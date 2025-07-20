from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse

class Genre(models.Model):
    """Model for anime genres"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']
        verbose_name = 'Género'
        verbose_name_plural = 'Géneros'

class Anime(models.Model):
    """Model for anime series/movies"""
    STATUS_CHOICES = [
        ('airing', 'En emisión'),
        ('completed', 'Finalizado'),
        ('upcoming', 'Próximamente'),
    ]
    
    TYPE_CHOICES = [
        ('tv', 'Serie TV'),
        ('movie', 'Película'),
        ('ova', 'OVA'),
        ('ona', 'ONA'),
        ('special', 'Especial'),
    ]
    
    title = models.CharField('Título', max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField('Descripción', blank=True, null=True)
    image = models.ImageField('Imagen miniatura', upload_to='anime_covers/', blank=True, null=True)
    cover_image = models.ImageField('Imagen de portada', upload_to='anime_covers/full/', blank=True, null=True)
    trailer_url = models.URLField('URL del tráiler', blank=True, null=True)
    status = models.CharField('Estado', max_length=10, choices=STATUS_CHOICES, default='upcoming')
    anime_type = models.CharField('Tipo', max_length=10, choices=TYPE_CHOICES, default='tv')
    episodes = models.PositiveIntegerField('Número de episodios', default=0)
    duration = models.PositiveIntegerField('Duración por episodio (minutos)', default=24)
    rating = models.FloatField('Puntuación', default=0.0)
    genres = models.ManyToManyField(Genre, related_name='animes', verbose_name='Géneros')
    year = models.PositiveIntegerField('Año de estreno', null=True, blank=True)
    season = models.CharField('Temporada', max_length=20, blank=True, null=True)
    studio = models.CharField('Estudio', max_length=100, blank=True, null=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('anime:anime_detail', kwargs={'slug': self.slug})
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Anime'
        verbose_name_plural = 'Animes'

class UserAnimeList(models.Model):
    """Model to track user's anime lists"""
    LIST_CHOICES = [
        ('watching', 'Viendo'),
        ('completed', 'Completado'),
        ('plan_to_watch', 'Planeo ver'),
        ('on_hold', 'En pausa'),
        ('dropped', 'Abandonado'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anime_lists', verbose_name='Usuario')
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='user_lists', verbose_name='Anime')
    status = models.CharField('Estado', max_length=15, choices=LIST_CHOICES)
    score = models.PositiveIntegerField('Puntuación (0-10)', default=0, blank=True, null=True)
    progress = models.PositiveIntegerField('Episodios vistos', default=0)
    notes = models.TextField('Notas', blank=True, null=True)
    is_favorite = models.BooleanField('Favorito', default=False)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'anime')
        ordering = ['-updated_at']
        verbose_name = 'Lista de anime'
        verbose_name_plural = 'Listas de anime'
    
    def __str__(self):
        return f"{self.user.username} - {self.anime.title} ({self.get_status_display()})"
