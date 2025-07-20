from django.contrib import admin
from django.db import models
from django.utils.html import format_html
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
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'slug', 'description', 'anime_type', 'status')
        }),
        ('Detalles', {
            'fields': ('episodes', 'duration', 'rating', 'year', 'season', 'studio', 'genres')
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
