from django.contrib import admin, messages
from django.db import models, transaction
from django.utils.html import format_html
from django.utils.translation import ngettext
from django.shortcuts import render
from .models import Anime, Genre, UserAnimeList

class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'anime_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _anime_count=models.Count('animes')
        )
    
    def anime_count(self, obj):
        return obj._anime_count
    anime_count.admin_order_field = '_anime_count'
    anime_count.short_description = 'Número de animes'

class AnimeAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_image', 'anime_type', 'status', 'year', 'rating', 'created_at')
    list_filter = ('status', 'anime_type', 'genres', 'year')
    search_fields = ('title', 'description', 'studio')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('genres',)
    readonly_fields = ('created_at', 'updated_at')
    actions = ['delete_selected_with_related']
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'slug', 'description', 'anime_type', 'status')
        }),
        ('Detalles', {
            'fields': ('episode_count', 'duration', 'rating', 'year', 'season', 'studio', 'genres')
        }),
        ('Multimedia', {
            'fields': ('image', 'cover_image', 'trailer_url')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.image.url)
        return "Sin imagen"
    display_image.short_description = 'Miniatura'
    display_image.allow_tags = True

    def delete_selected_with_related(self, request, queryset):
        """
        Custom action to delete selected animes and all their related data.
        """
        if request.POST.get('post'):
            # This is the confirmation step
            deleted_count = 0
            for anime in queryset:
                # Delete all related data before deleting the anime
                self._delete_related_objects(anime)
                anime.delete()
                deleted_count += 1
            
            self.message_user(
                request,
                ngettext(
                    '%d anime was successfully deleted with all its related data.',
                    '%d animes were successfully deleted with all their related data.',
                    deleted_count
                ) % deleted_count,
                messages.SUCCESS
            )
            return None
            
        # Show confirmation page
        related_objects = []
        for anime in queryset:
            related = self._get_related_objects(anime)
            if related:
                related_objects.append((anime, related))
        
        return render(
            request,
            'admin/anime/anime/delete_selected_confirmation.html',
            context={
                'animes': queryset,
                'related_objects': related_objects,
                'opts': self.model._meta,
                'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )
    delete_selected_with_related.short_description = "Eliminar seleccionados (incluyendo datos relacionados)"
    
    def _get_related_objects(self, anime):
        """Get a list of related objects that will be deleted."""
        related = []
        
        # Episodes
        episodes_count = anime.episode_list.count()
        if episodes_count > 0:
            related.append((f"Episodios ({episodes_count})", anime.episode_list.all()[:10]))
            
        # Comments
        comments_count = anime.comments.count()
        if comments_count > 0:
            related.append((f"Comentarios ({comments_count})", anime.comments.all()[:10]))
            
        # User lists
        user_lists_count = anime.user_lists.count()
        if user_lists_count > 0:
            related.append((f"Listas de usuarios ({user_lists_count})", anime.user_lists.all()[:10]))
            
        # Ratings
        ratings_count = anime.ratings.count()
        if ratings_count > 0:
            related.append((f"Puntuaciones ({ratings_count})", anime.ratings.all()[:10]))
            
        # Forum threads
        forum_threads_count = anime.forum_threads.count()
        if forum_threads_count > 0:
            related.append((f"Hilos del foro ({forum_threads_count})", anime.forum_threads.all()[:10]))
            
        return related
    
    def _delete_related_objects(self, anime):
        """Delete all related objects for the given anime."""
        # Delete all related objects
        anime.episode_list.all().delete()
        anime.comments.all().delete()
        anime.user_lists.all().delete()
        anime.ratings.all().delete()
        
        # Delete forum threads and their posts
        for thread in anime.forum_threads.all():
            thread.posts.all().delete()
        anime.forum_threads.all().delete()
        
        # Delete any notifications related to this anime
        from .models import Notification
        Notification.objects.filter(
            notification_type__in=['comment', 'anime_update'],
            related_id=anime.id
        ).delete()

class UserAnimeListAdmin(admin.ModelAdmin):
    list_display = ('user', 'anime', 'status', 'score', 'progress', 'is_favorite', 'updated_at')
    list_filter = ('status', 'is_favorite')
    search_fields = ('user__username', 'anime__title', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('user', 'anime')

# Register models
admin.site.register(Genre, GenreAdmin)
admin.site.register(Anime, AnimeAdmin)
admin.site.register(UserAnimeList, UserAnimeListAdmin)
