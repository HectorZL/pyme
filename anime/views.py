from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db import models
from django.db.models import Q, Count, Case, When, IntegerField
from .models import Anime, Genre, UserAnimeList, UserProfile, Comment, Rating
from .forms import AnimeFilterForm
import json
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from functools import wraps
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.csrf import ensure_csrf_cookie

def require_ajax(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Allow the request if either the header is set or it's a POST request
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
            # Log the issue but don't block the request
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f'Missing X-Requested-With header in request: {request.path}')
        return view_func(request, *args, **kwargs)
    return wrapper

class HomeView(TemplateView):
    template_name = 'anime/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get latest animes (most recently added to the database)
        context['latest_animes'] = Anime.objects.filter(
            year__isnull=False
        ).order_by('-created_at')[:12]
        
        # Get top rated animes (with rating >= 6.0, ordered by rating)
        context['top_rated'] = Anime.objects.filter(
            rating__gte=6.0
        ).order_by('-rating', '-year')[:12]
        
        # If we don't have enough top rated animes, fill with highest rated
        if len(context['top_rated']) < 12:
            top_rated_ids = [anime.id for anime in context['top_rated']]
            additional = Anime.objects.exclude(id__in=top_rated_ids)\
                                   .order_by('-rating', '-year')\
                                   [:12 - len(context['top_rated'])]
            context['top_rated'] = list(context['top_rated']) + list(additional)
            
        return context

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
        
        # Apply filters
        genre_filter = self.request.GET.get('genre')
        if genre_filter:
            queryset = queryset.filter(genres__slug=genre_filter)
            
        year_filter = self.request.GET.get('year')
        if year_filter and year_filter.isdigit():
            queryset = queryset.filter(year=year_filter)
        
        status_filter = self.request.GET.get('status')
        if status_filter in dict(Anime.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter)
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['title', '-title', 'year', '-year', '-rating', '-created_at']:
            queryset = queryset.order_by(sort_by)
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current view mode (grid or list)
        view_mode = self.request.GET.get('view', 'grid')
        context['view_mode'] = view_mode if view_mode in ['grid', 'list'] else 'grid'
        
        # Add search query to context
        context['search_query'] = self.request.GET.get('q', '')
        
        # Add current sorting to context
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        # Add filter parameters to context
        context['current_genre'] = self.request.GET.get('genre', '')
        context['current_year'] = self.request.GET.get('year', '')
        context['current_status'] = self.request.GET.get('status', '')
        
        # Get all genres for the filter
        context['all_genres'] = Genre.objects.all().order_by('name')
        
        # Get distinct years for the filter
        context['all_years'] = Anime.objects.exclude(year__isnull=True).values_list('year', flat=True).distinct().order_by('-year')
        
        # Add status choices
        context['status_choices'] = Anime.STATUS_CHOICES
        
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
        anime = self.object
        
        # Add LIST_CHOICES to context
        context['list_choices'] = UserAnimeList.LIST_CHOICES
        
        # Add related anime (same studio or same genres)
        related_anime = Anime.objects.filter(
            Q(genres__in=anime.genres.all()) | Q(studio=anime.studio)
        ).exclude(id=anime.id).distinct()[:5]
        context['related_anime'] = related_anime
        
        # Add episodes if available
        context['episodes'] = anime.episode_list.all().order_by('number')
        
        # Get rating statistics
        rating_data = anime.ratings.aggregate(
            avg_rating=models.Avg('score'),
            rating_count=models.Count('id')
        )
        
        # Add rating data to context
        context['avg_rating'] = round(float(rating_data['avg_rating'] or 0), 1)
        context['rating_count'] = rating_data['rating_count'] or 0
        
        # Add user's rating if authenticated
        if self.request.user.is_authenticated:
            try:
                user_rating = Rating.objects.get(user=self.request.user, anime=anime)
                context['user_rating'] = user_rating.score
            except Rating.DoesNotExist:
                context['user_rating'] = 0
        else:
            context['user_rating'] = 0
            
        # Add user's anime status and other data if authenticated
        if self.request.user.is_authenticated:
            try:
                user_anime = UserAnimeList.objects.get(
                    user=self.request.user,
                    anime=anime
                )
                context['user_status'] = user_anime.status
                context['user_score'] = user_anime.score
                context['user_progress'] = user_anime.progress
                context['user_notes'] = user_anime.notes
                context['is_favorite'] = user_anime.is_favorite
            except UserAnimeList.DoesNotExist:
                context['user_status'] = None
                context['user_score'] = None
                context['user_progress'] = 0
                context['user_notes'] = ''
                context['is_favorite'] = False
        
        # Add comments
        context['comments'] = anime.comments.filter(parent__isnull=True).order_by('-created_at')
        
        return context

class UserAnimeListView(LoginRequiredMixin, ListView):
    model = UserAnimeList
    template_name = 'anime/my_list.html'
    context_object_name = 'user_anime_list'
    paginate_by = 24
    
    def get_queryset(self):
        # Get the status filter from URL parameters, default to 'por_ver'
        self.status_filter = self.request.GET.get('status', 'por_ver')
        
        # Base queryset - get the user's anime with valid slugs
        queryset = UserAnimeList.objects.filter(
            user=self.request.user,
            anime__slug__isnull=False
        ).exclude(anime__slug='').select_related('anime')
        
        # Apply status filter if provided and valid
        if self.status_filter and self.status_filter in dict(UserAnimeList.LIST_CHOICES):
            queryset = queryset.filter(status=self.status_filter)
        
        # Order by most recently updated
        return queryset.order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add list choices to context
        context['list_choices'] = UserAnimeList.LIST_CHOICES
        
        # Get status counts for all statuses
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
        
        # Ensure all statuses are in the dictionary with count 0
        for status_choice in UserAnimeList.LIST_CHOICES:
            if status_choice[0] not in context['status_counts']:
                context['status_counts'][status_choice[0]] = 0
        
        # Add current status filter to context
        context['current_status'] = self.status_filter
        
        # Add user's anime status for the template
        user_anime = UserAnimeList.objects.filter(
            user=self.request.user,
            anime_id__in=[ua.anime_id for ua in self.object_list]
        )
        
        context['user_anime_dict'] = {ua.anime_id: ua for ua in user_anime}
        
        # Add favorites for the template
        context['favorites'] = set(
            ua.anime_id for ua in user_anime
            if ua.is_favorite
        )
        
        return context

class FavoritesView(LoginRequiredMixin, ListView):
    """View for displaying user's favorite anime"""
    model = UserAnimeList
    template_name = 'anime/favorites.html'
    context_object_name = 'favorites'
    paginate_by = 12
    
    def get_queryset(self):
        # Clean up any favorites with no associated anime first
        invalid_favorites = UserAnimeList.objects.filter(
            user=self.request.user,
            is_favorite=True,
            anime__isnull=True
        )
        invalid_favorites.delete()
        
        # Get valid favorites
        return UserAnimeList.objects.filter(
            user=self.request.user,
            is_favorite=True,
            anime__isnull=False,
            anime__slug__isnull=False  # Only include favorites with valid slugs
        ).select_related('anime').order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filter out any favorites with invalid slugs from the template context
        valid_favorites = [
            fav for fav in context['favorites'] 
            if hasattr(fav, 'anime') and fav.anime and fav.anime.slug
        ]
        context['favorites'] = valid_favorites
        
        # Add user's anime status for the template
        if valid_favorites:
            user_anime = UserAnimeList.objects.filter(
                user=self.request.user,
                anime_id__in=[fav.anime_id for fav in valid_favorites if hasattr(fav, 'anime_id')]
            )
            context['user_anime_dict'] = {ua.anime_id: ua.status for ua in user_anime}
            
            # Add favorites for the template
            context['favorites_set'] = set(
                ua.anime_id for ua in user_anime
                if ua.is_favorite
            )
        else:
            context['user_anime_dict'] = {}
            context['favorites_set'] = set()
        
        # Add list choices for status dropdown
        context['list_choices'] = UserAnimeList.LIST_CHOICES
        
        return context

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'
    
    def get_profile(self, user):
        """Get or create user profile"""
        profile, created = UserProfile.objects.get_or_create(user=user)
        return profile
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = self.get_profile(user)
        
        # Get user's anime list stats
        anime_stats = UserAnimeList.objects.filter(user=user).aggregate(
            total_anime=Count('id', distinct=True),
            completed=Count(Case(When(status='finalizado', then=1), output_field=IntegerField())),
            watching=Count(Case(When(status='viendo', then=1), output_field=IntegerField())),
            on_hold=Count(Case(When(status='en_pausa', then=1), output_field=IntegerField())),
            dropped=Count(Case(When(status='abandonado', then=1), output_field=IntegerField())),
            plan_to_watch=Count(Case(When(status='por_ver', then=1), output_field=IntegerField()))
        )
        
        context.update({
            'user': user,
            'profile': profile,
            'anime_stats': anime_stats,
            'recent_anime': UserAnimeList.objects.filter(user=user).select_related('anime').order_by('-updated_at')[:6]
        })
        return context
    
    def post(self, request, *args, **kwargs):
        user = request.user
        profile = self.get_profile(user)
        
        # Update user email if provided
        new_email = request.POST.get('email')
        if new_email and new_email != user.email:
            user.email = new_email
            user.save()
        
        # Update profile bio if provided
        new_bio = request.POST.get('bio', '').strip()
        if new_bio != profile.bio:
            profile.bio = new_bio
        
        # Handle avatar upload
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        
        profile.save()
        
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('anime:profile')

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
                defaults={'status': 'por_ver', 'is_favorite': True}
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

@require_http_methods(["POST"])
def update_anime_status(request, anime_id):
    """
    Handle AJAX requests to update an anime's status in the user's list.
    
    Args:
        request: The HTTP request object
        anime_id: ID of the anime to update (from URL)
    
    Expected POST parameters:
    - status: New status ('por_ver', 'viendo', 'finalizado', etc. or 'remove' to delete)
    - score: Optional score (0-10)
    - progress: Optional episode progress
    - notes: Optional user notes
    - is_favorite: Optional boolean for favorite status
    
    Returns JSON response with status and message.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Debes iniciar sesión para realizar esta acción'}, status=401)
    
    try:
        anime = get_object_or_404(Anime, id=anime_id)
        
        # Handle removal from list
        if request.POST.get('status') == 'remove':
            UserAnimeList.objects.filter(user=request.user, anime=anime).delete()
            return JsonResponse({
                'status': 'success', 
                'message': f'Se ha eliminado {anime.title} de tu lista',
                'action': 'removed'
            })
        
        # Validate status
        valid_statuses = dict(UserAnimeList.LIST_CHOICES).keys()
        if request.POST.get('status') not in valid_statuses:
            return JsonResponse({'status': 'error', 'message': 'Estado no válido'}, status=400)
        
        # Get or create user anime list entry
        user_anime, created = UserAnimeList.objects.get_or_create(
            user=request.user,
            anime=anime,
            defaults={'status': request.POST.get('status')}
        )
        
        # Update fields if they were provided
        if not created:
            user_anime.status = request.POST.get('status')
        
        # Update score if provided (0-10)
        if 'score' in request.POST:
            try:
                score = int(request.POST.get('score'))
                if 0 <= score <= 10:
                    user_anime.score = score
            except (ValueError, TypeError):
                pass
        
        # Update progress if provided
        if 'progress' in request.POST:
            try:
                progress = int(request.POST.get('progress'))
                if progress >= 0:
                    user_anime.progress = progress
            except (ValueError, TypeError):
                pass
        
        # Update notes if provided
        if 'notes' in request.POST:
            user_anime.notes = request.POST.get('notes', '')[:1000]  # Limit notes length
        
        # Update favorite status if provided
        if 'is_favorite' in request.POST:
            user_anime.is_favorite = request.POST.get('is_favorite') == 'true'
        
        # Set start date if this is the first time adding to list
        if created and not user_anime.start_date:
            user_anime.start_date = timezone.now().date()
        
        # Set finish date if marked as completed
        if request.POST.get('status') == 'finalizado' and not user_anime.finish_date:
            user_anime.finish_date = timezone.now().date()
        
        user_anime.save()
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Se ha actualizado el estado de {anime.title} a {user_anime.get_status_display()}',
            'action': 'updated' if not created else 'added',
            'user_status': user_anime.status,
            'user_score': user_anime.score,
            'user_progress': user_anime.progress,
            'is_favorite': user_anime.is_favorite
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_http_methods(["POST"])
@login_required
@require_ajax
def toggle_favorite(request, anime_id=None):
    """
    Handle AJAX requests to toggle an anime's favorite status.
    
    Can be called with anime_id in URL or in POST data for backward compatibility.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Debes iniciar sesión para realizar esta acción'}, status=401)
    
    # Get anime_id from URL parameter or POST data (for backward compatibility)
    anime_id = anime_id or request.POST.get('anime_id')
    
    if not anime_id:
        return JsonResponse({'status': 'error', 'message': 'Se requiere el ID del anime'}, status=400)
    
    try:
        anime = get_object_or_404(Anime, id=anime_id)
        
        # Get or create the user's anime list entry
        user_anime, created = UserAnimeList.objects.get_or_create(
            user=request.user,
            anime=anime,
            defaults={'status': 'por_ver'}
        )
        
        # Toggle favorite status
        user_anime.is_favorite = not user_anime.is_favorite
        user_anime.updated_at = timezone.now()
        user_anime.save(update_fields=['is_favorite', 'updated_at'])
        
        # Get updated favorite count for this anime
        favorite_count = UserAnimeList.objects.filter(anime=anime, is_favorite=True).count()
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Anime {"añadido a" if user_anime.is_favorite else "eliminado de"} favoritos',
            'is_favorite': user_anime.is_favorite,
            'favorite_count': favorite_count
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@require_http_methods(["POST"])
@login_required
@require_ajax
def update_anime_status(request, anime_id):
    """
    Handle AJAX requests to update an anime's status in the user's list.
    
    Args:
        request: The HTTP request object
        anime_id: ID of the anime to update (from URL)
    
    Expected POST parameters:
    - status: New status ('por_ver', 'viendo', 'finalizado', etc. or 'remove' to delete)
    - score: Optional score (0-10)
    - progress: Optional episode progress
    - notes: Optional user notes
    - is_favorite: Optional boolean for favorite status
    
    Returns JSON response with status and message.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Debes iniciar sesión para realizar esta acción'}, status=401)
    
    try:
        anime = get_object_or_404(Anime, id=anime_id)
        status = request.POST.get('status')
        
        if not status:
            return JsonResponse({'status': 'error', 'message': 'Se requiere un estado'}, status=400)
        
        # Handle removing from list
        if status == 'remove':
            UserAnimeList.objects.filter(user=request.user, anime=anime).delete()
            return JsonResponse({
                'status': 'success',
                'message': 'Anime eliminado de tu lista',
                'action': 'removed'
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
        
        # Update status and other fields
        user_anime.status = status
        user_anime.updated_at = timezone.now()
        
        # Update optional fields if provided
        if 'score' in request.POST:
            user_anime.score = request.POST.get('score')
        if 'progress' in request.POST:
            user_anime.progress = request.POST.get('progress')
        if 'notes' in request.POST:
            user_anime.notes = request.POST.get('notes')
        if 'is_favorite' in request.POST:
            user_anime.is_favorite = request.POST.get('is_favorite').lower() == 'true'
        
        user_anime.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Estado actualizado a {dict(UserAnimeList.LIST_CHOICES).get(status, status)}',
            'user_status': user_anime.status,
            'is_favorite': user_anime.is_favorite
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

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
        anime_id = request.POST.get('anime_id')
        
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
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

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
def submit_comment(request, anime_slug):
    """
    Handle comment submission via AJAX.
    """
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        is_spoiler = data.get('is_spoiler', False)
        parent_id = data.get('parent_id')
        
        if not content:
            return JsonResponse({'status': 'error', 'message': 'El comentario no puede estar vacío'}, status=400)
            
        try:
            anime = Anime.objects.get(slug=anime_slug)
        except Anime.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Anime no encontrado'}, status=404)
        
        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id, anime=anime)
            except Comment.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Comentario padre no válido'}, status=400)
        
        comment = Comment.objects.create(
            user=request.user,
            anime=anime,
            parent=parent,
            content=content,
            is_spoiler=is_spoiler
        )
        
        # Render the comment to HTML
        comment_html = render_to_string('anime/partials/comment.html', {
            'comment': comment,
            'user': request.user
        })
        
        return JsonResponse({
            'status': 'success',
            'message': 'Comentario publicado',
            'comment_html': comment_html,
            'comment_id': comment.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@require_http_methods(["POST"])
@login_required
@require_ajax
def rate_anime(request, pk):
    """
    Handle anime rating submission via AJAX.
    
    Expected POST data:
    - score: Integer between 1 and 10
    
    Returns JSON response with status and updated rating info.
    """
    try:
        data = json.loads(request.body)
        score = int(data.get('score'))
        
        # Validate score is between 1 and 10
        if not (1 <= score <= 10):
            return JsonResponse({
                'status': 'error',
                'message': 'La puntuación debe estar entre 1 y 10.'
            }, status=400)
            
        anime = get_object_or_404(Anime, pk=pk)
        
        # Get or create the rating
        from .models import Rating
        rating, created = Rating.objects.update_or_create(
            user=request.user,
            anime=anime,
            defaults={'score': score}
        )
        
        # Update anime's average rating
        anime.update_average_rating()
        
        # Get updated rating data
        rating_data = anime.ratings.aggregate(
            avg_rating=models.Avg('score'),
            rating_count=Count('id')
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Valoración guardada correctamente',
            'avg_rating': round(float(rating_data['avg_rating'] or 0), 1),
            'rating_count': rating_data['rating_count'] or 0
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Error en el formato de los datos.'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
