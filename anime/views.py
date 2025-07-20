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
    template_name = 'anime/my_list.html'
    context_object_name = 'anime_list'
    
    def get_queryset(self):
        status = self.request.GET.get('status', 'all')
        queryset = UserAnimeList.objects.filter(user=self.request.user)
        
        if status != 'all':
            queryset = queryset.filter(status=status)
            
        return queryset.select_related('anime')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get('status', 'all')
        
        # Get counts for each status
        counts = UserAnimeList.objects.filter(
            user=self.request.user
        ).values('status').annotate(
            count=Count('status')
        )
        
        # Initialize all counts to 0
        status_counts = {
            'watching': 0,
            'completed': 0,
            'plan_to_watch': 0,
            'on_hold': 0,
            'dropped': 0
        }
        
        # Update with actual counts
        for item in counts:
            status_counts[item['status']] = item['count']
        
        context.update({
            'status': status,
            'status_counts': status_counts,
            'total_anime': sum(status_counts.values())
        })
        
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
    if not request.user.is_authenticated or not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=403)
    
    # Validate status
    valid_statuses = [choice[0] for choice in UserAnimeList.LIST_CHOICES] + ['all']
    if status not in valid_statuses:
        return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
    
    # Get anime list for the status
    user_anime = UserAnimeList.objects.filter(user=request.user)
    
    if status != 'all':
        user_anime = user_anime.filter(status=status)
    
    # Order by most recently updated
    user_anime = user_anime.select_related('anime').order_by('-updated_at')
    
    # Render the anime cards
    html = render_to_string('anime/partials/anime_grid.html', {
        'animes': [item.anime for item in user_anime],
        'user_anime': {item.anime_id: item.status for item in user_anime}
    })
    
    # Get counts for all statuses
    status_counts = UserAnimeList.objects.filter(
        user=request.user
    ).values('status').annotate(
        count=Count('status')
    )
    
    # Format counts as a dictionary
    counts = {item['status']: item['count'] for item in status_counts}
    
    return JsonResponse({
        'status': 'success',
        'html': html,
        'count': user_anime.count(),
        'status_counts': counts
    })
