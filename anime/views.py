from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q, Count, Case, When, IntegerField
from .models import Anime, Genre, UserAnimeList
from .forms import AnimeFilterForm
import json
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from functools import wraps

def require_ajax(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper

class HomeView(TemplateView):
    template_name = 'anime/index.html'

class AnimeCatalogView(ListView):
    model = Anime
    template_name = 'anime/catalog.html'
    context_object_name = 'animes'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Anime.objects.all()
        
        # Get search query
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(genres__name__icontains=search_query)
            ).distinct()
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['title', '-title', 'year', '-year', '-rating', '-created_at']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current view mode (grid or list)
        view_mode = self.request.GET.get('view', 'grid')
        context['view_mode'] = view_mode if view_mode in ['grid', 'list'] else 'grid'
        
        # Add search query to context
        context['search_query'] = self.request.GET.get('q', '')
        
        # Add current sorting to context
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        # Add user's anime status if authenticated
        if self.request.user.is_authenticated:
            user_anime = UserAnimeList.objects.filter(
                user=self.request.user,
                anime_id__in=[anime.id for anime in context['animes']]
            )
            context['user_anime_dict'] = {ua.anime_id: ua.status for ua in user_anime}
        
        return context

class AnimeDetailView(DetailView):
    model = Anime
    template_name = 'anime/anime_detail.html'
    context_object_name = 'anime'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Import UserAnimeList to access LIST_CHOICES
        from .models import UserAnimeList
        
        # Add LIST_CHOICES to context
        context['list_choices'] = UserAnimeList.LIST_CHOICES
        
        # Add user's anime status if authenticated
        if self.request.user.is_authenticated:
            try:
                user_anime = UserAnimeList.objects.get(
                    user=self.request.user,
                    anime=self.object
                )
                context['user_status'] = user_anime.status
            except UserAnimeList.DoesNotExist:
                context['user_status'] = None
        
        return context

class UserAnimeListView(LoginRequiredMixin, ListView):
    model = UserAnimeList
    template_name = 'anime/user_anime_list.html'
    context_object_name = 'user_anime_list'
    
    def get_queryset(self):
        # Get the status filter from URL parameters
        status_filter = self.request.GET.get('status')
        
        # Base queryset - only get the user's anime with valid slugs
        queryset = UserAnimeList.objects.filter(
            user=self.request.user,
            anime__slug__isnull=False
        ).exclude(anime__slug='')
        
        # Apply status filter if provided
        if status_filter and status_filter in dict(UserAnimeList.LIST_CHOICES):
            queryset = queryset.filter(status=status_filter)
        
        return queryset.select_related('anime')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add LIST_CHOICES to context
        context['list_choices'] = UserAnimeList.LIST_CHOICES
        
        # Filter out any entries with empty or None slugs just to be safe
        valid_entries = [
            ua for ua in self.object_list 
            if ua.anime and ua.anime.slug
        ]
        
        # Create a dictionary of anime IDs to their status for the template
        context['user_anime'] = {
            ua.anime_id: ua.status 
            for ua in valid_entries
        }
        
        # Get a list of anime objects for the template (for the anime cards)
        context['animes'] = [ua.anime for ua in valid_entries]
        
        # Add favorites for the template
        context['favorites'] = set(
            ua.anime_id for ua in valid_entries
            if ua.is_favorite
        )
        
        # Get status counts for the filter tabs, excluding entries with invalid slugs
        status_counts = UserAnimeList.objects.filter(
            user=self.request.user,
            anime__slug__isnull=False
        ).exclude(anime__slug='').values('status').annotate(
            count=Count('status')
        )
        
        # Convert to a dictionary for easier access in the template
        context['status_counts'] = {
            item['status']: item['count'] 
            for item in status_counts
        }
        
        # Add total count
        context['total_count'] = sum(context['status_counts'].values())
        
        # Add current status filter
        context['current_status'] = self.request.GET.get('status', 'all')
        
        return context

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's anime list stats
        anime_stats = UserAnimeList.objects.filter(user=user).aggregate(
            total_anime=Count('id', distinct=True),
            completed=Count(Case(When(status='completed', then=1), output_field=IntegerField())),
            watching=Count(Case(When(status='watching', then=1), output_field=IntegerField())),
            plan_to_watch=Count(Case(When(status='plan_to_watch', then=1), output_field=IntegerField())),
            on_hold=Count(Case(When(status='on_hold', then=1), output_field=IntegerField())),
            dropped=Count(Case(When(status='dropped', then=1), output_field=IntegerField()))
        )
        
        context.update({
            'user': user,
            'anime_stats': anime_stats,
            'recent_anime': UserAnimeList.objects.filter(user=user).select_related('anime').order_by('-updated_at')[:5]
        })
        
        return context

class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('anime:home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)  # Log the user in after registration
        return response

@require_http_methods(["POST"])
@login_required
@require_ajax
def update_anime_list(request):
    """
    Handle AJAX requests to update an anime's status in the user's list or toggle favorite status.
    
    Expected POST parameters:
    - anime_id: ID of the anime to update
    - action: 'update_status' or 'toggle_favorite'
    - status: Required if action is 'update_status', the new status (watching, completed, etc.)
    
    Returns JSON response with status and message.
    """
    try:
        data = json.loads(request.body)
        anime_id = data.get('anime_id')
        action = data.get('action')
        
        if not anime_id or not action:
            return JsonResponse({'status': 'error', 'message': 'Missing required parameters'}, status=400)
        
        anime = get_object_or_404(Anime, id=anime_id)
        
        if action == 'update_status':
            status = data.get('status')
            if not status:
                return JsonResponse({'status': 'error', 'message': 'Status is required'}, status=400)
                
            # If status is 'none', remove from list
            if status == 'none':
                UserAnimeList.objects.filter(user=request.user, anime=anime).delete()
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Anime removed from your list',
                    'new_status': None,
                    'is_favorite': False
                })
            
            # Otherwise, update or create the entry
            user_anime, created = UserAnimeList.objects.get_or_create(
                user=request.user,
                anime=anime,
                defaults={'status': status}
            )
            
            if not created and user_anime.status != status:
                user_anime.status = status
                user_anime.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Status updated to {user_anime.get_status_display()}',
                'new_status': user_anime.status,
                'is_favorite': user_anime.is_favorite
            })
            
        elif action == 'toggle_favorite':
            user_anime, created = UserAnimeList.objects.get_or_create(
                user=request.user,
                anime=anime,
                defaults={'status': 'plan_to_watch', 'is_favorite': True}
            )
            
            # Toggle favorite status
            user_anime.is_favorite = not user_anime.is_favorite
            user_anime.save()
            
            return JsonResponse({
                'status': 'success', 
                'message': f'Anime {"added to" if user_anime.is_favorite else "removed from"} favorites',
                'is_favorite': user_anime.is_favorite,
                'current_status': user_anime.status if not created else None
            })
            
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def update_anime_status(request):
    """
    Handle AJAX requests to update an anime's status in the user's list.
    
    Expected POST parameters:
    - anime_id: ID of the anime to update
    - status: New status (watching, completed, on_hold, dropped, plan_to_watch, or 'none' to remove)
    
    Returns JSON response with status and message.
    """
    if not request.user.is_authenticated or not request.method == 'POST':
        return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=403)
    
    anime_id = request.POST.get('anime_id')
    status = request.POST.get('status')
    
    if not anime_id or not status:
        return JsonResponse({'status': 'error', 'message': 'Missing parameters'}, status=400)
    
    try:
        anime = Anime.objects.get(id=anime_id)
    except Anime.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Anime not found'}, status=404)
    
    # If status is 'none', remove the anime from the user's list
    if status == 'none':
        try:
            user_anime = UserAnimeList.objects.get(user=request.user, anime=anime)
            user_anime.delete()
            return JsonResponse({
                'status': 'success',
                'message': f'Anime {anime.title} eliminado de tu lista',
                'status_display': 'none'
            })
        except UserAnimeList.DoesNotExist:
            return JsonResponse({
                'status': 'success',
                'message': 'El anime no estaba en tu lista',
                'status_display': 'none'
            })
    
    # Validate status
    valid_statuses = [choice[0] for choice in UserAnimeList.LIST_CHOICES]
    if status not in valid_statuses:
        return JsonResponse({'status': 'error', 'message': 'Estado no válido'}, status=400)
    
    # Get or create the user's anime list entry
    user_anime, created = UserAnimeList.objects.get_or_create(
        user=request.user,
        anime=anime,
        defaults={'status': status}
    )
    
    # If the entry already exists, update the status
    if not created:
        user_anime.status = status
        user_anime.save(update_fields=['status', 'updated_at'])
    
    # Get the display name for the status
    status_display = dict(UserAnimeList.LIST_CHOICES).get(status, status)
    
    return JsonResponse({
        'status': 'success',
        'message': f'Anime {anime.title} actualizado a {status_display}',
        'status_display': status_display,
        'status_value': status
    })

def get_anime_list_by_status(request, status):
    """
    AJAX endpoint to get anime list filtered by status.
    Returns rendered HTML of anime cards for the given status.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=403)
    
    # Validate status
    valid_statuses = [choice[0] for choice in UserAnimeList.LIST_CHOICES] + ['all']
    if status not in valid_statuses:
        return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
    
    # Get user's anime list filtered by status and exclude entries with empty or None slugs
    user_anime_list = UserAnimeList.objects.filter(
        user=request.user,
        anime__slug__isnull=False,
    ).exclude(anime__slug='')
    
    if status != 'all':
        user_anime_list = user_anime_list.filter(status=status)
    
    # Get the anime objects with valid slugs
    animes = []
    valid_entries = []
    for item in user_anime_list.select_related('anime'):
        if item.anime.slug:  # Double-check that slug is not empty
            animes.append(item.anime)
            valid_entries.append(item)
    
    # Create a dictionary of anime statuses for the template
    user_anime_dict = {}
    for entry in valid_entries:
        user_anime_dict[entry.anime_id] = entry
    
    # Get favorite anime IDs
    favorites = set(entry.anime_id for entry in valid_entries if entry.is_favorite)
    
    # Render the anime cards
    html = render_to_string('anime/partials/anime_grid.html', {
        'animes': animes,
        'user_anime_list': user_anime_dict,
        'favorites': favorites
    })
    
    return JsonResponse({'status': 'success', 'html': html})

@require_http_methods(["POST"])
@login_required
@require_ajax
def toggle_favorite(request):
    """
    Handle AJAX requests to toggle an anime's favorite status.
    
    Expected POST parameters:
    - anime_id: ID of the anime to toggle favorite status for
    
    Returns JSON response with status and updated favorite status.
    """
    try:
        data = json.loads(request.body)
        anime_id = data.get('anime_id')
        
        if not anime_id:
            return JsonResponse({'status': 'error', 'message': 'Missing anime_id parameter'}, status=400)
        
        anime = get_object_or_404(Anime, id=anime_id)
        
        # Get or create the user's anime list entry
        user_anime, created = UserAnimeList.objects.get_or_create(
            user=request.user,
            anime=anime,
            defaults={'status': 'plan_to_watch', 'is_favorite': True}
        )
        
        # Toggle favorite status if not just created
        if not created:
            user_anime.is_favorite = not user_anime.is_favorite
            user_anime.save(update_fields=['is_favorite', 'updated_at'])
        
        # Get updated favorites count
        favorites_count = UserAnimeList.objects.filter(user=request.user, is_favorite=True).count()
        
        return JsonResponse({
            'status': 'success',
            'is_favorite': user_anime.is_favorite,
            'favorites_count': favorites_count,
            'message': f'Anime {anime.title} {"añadido a" if user_anime.is_favorite else "eliminado de"} favoritos'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_http_methods(["POST"])
@login_required
@require_ajax
def remove_from_list(request):
    """
    Handle AJAX requests to remove an anime from the user's list.
    
    Expected POST parameters:
    - anime_id: ID of the anime to remove
    
    Returns JSON response with status and message.
    """
    try:
        data = json.loads(request.body)
        anime_id = data.get('anime_id')
        
        if not anime_id:
            return JsonResponse({'status': 'error', 'message': 'Missing anime_id parameter'}, status=400)
        
        anime = get_object_or_404(Anime, id=anime_id)
        
        # Delete the anime from user's list if it exists
        deleted, _ = UserAnimeList.objects.filter(
            user=request.user,
            anime=anime
        ).delete()
        
        if deleted:
            return JsonResponse({
                'status': 'success',
                'message': f'Anime {anime.title} eliminado de tu lista'
            })
        else:
            return JsonResponse({
                'status': 'success',
                'message': 'El anime no estaba en tu lista'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
