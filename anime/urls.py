from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from . import views
from .views import rate_anime

app_name = 'anime'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('catalog/', views.AnimeCatalogView.as_view(), name='catalog'),
    path('anime/<slug:slug>/', views.AnimeDetailView.as_view(), name='anime_detail'),
    path('anime/<int:anime_id>/update_status/', views.update_anime_status, name='update_anime_status'),
    path('anime/<int:anime_id>/toggle_favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('toggle-favorite/', views.toggle_favorite, name='toggle_favorite_legacy'),  # For backward compatibility
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # User anime list management
    path('my-list/', views.UserAnimeListView.as_view(), name='user_anime_list'),
    path('favorites/', views.FavoritesView.as_view(), name='favorites'),
    path('api/list/<str:status>/', views.get_anime_list_by_status, name='get_anime_list_by_status'),
    path('remove-from-list/', views.remove_from_list, name='remove_from_list'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page=reverse_lazy('anime:home'),
        template_name='registration/logged_out.html'
    ), name='logout'),
    
    # Comments
    path('anime/<slug:anime_slug>/comment/', views.submit_comment, name='submit_comment'),
    path('comments/', views.AnimeCommentsView.as_view(), name='comments'),
    
    # Forums
    path('foros/', TemplateView.as_view(template_name='anime/foros.html'), name='foros'),
    
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change.html',
        success_url=reverse_lazy('anime:password_change_done')
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url='anime:password_reset_done'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url='anime:password_reset_complete'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('anime/<int:pk>/rate/', rate_anime, name='rate_anime'),
]
