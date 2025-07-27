from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
import json

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
    episode_count = models.PositiveIntegerField('Número de episodios', default=0)  
    duration = models.PositiveIntegerField('Duración por episodio (minutos)', default=24)
    rating = models.DecimalField('Puntuación', max_digits=3, decimal_places=1, default=0.0)
    average_rating = models.DecimalField('Puntuación media', max_digits=3, decimal_places=1, default=0.0)
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
    
    def get_average_rating(self):
        """Calculate average rating from user scores"""
        from django.db.models import Avg
        return self.user_lists.aggregate(avg_rating=Avg('score'))['avg_rating'] or 0.0
    
    def update_average_rating(self):
        ratings = self.ratings.all()
        if ratings:
            self.average_rating = sum(r.score for r in ratings) / len(ratings)
            self.save(update_fields=['average_rating'])
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Anime'
        verbose_name_plural = 'Animes'

class UserProfile(models.Model):
    """Extended user profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField('Biografía', blank=True, null=True)
    avatar = models.ImageField('Avatar', upload_to='avatars/', blank=True, null=True)
    banner = models.ImageField('Banner', upload_to='banners/', blank=True, null=True)
    birth_date = models.DateField('Fecha de nacimiento', blank=True, null=True)
    location = models.CharField('Ubicación', max_length=100, blank=True, null=True)
    website = models.URLField('Sitio web', blank=True, null=True)
    social_media = models.JSONField('Redes sociales', default=dict, blank=True)
    email_verified = models.BooleanField('Correo verificado', default=False)
    preferences = models.JSONField('Preferencias', default=dict, blank=True)
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.social_media:
            self.social_media = {}
        super().save(*args, **kwargs)

class UserAnimeList(models.Model):
    """Model to track user's anime lists"""
    LIST_CHOICES = [
        ('por_ver', 'Por ver'),
        ('viendo', 'Viendo'),
        ('finalizado', 'Finalizado'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anime_lists', verbose_name='Usuario')
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='user_lists', verbose_name='Anime')
    status = models.CharField('Estado', max_length=15, choices=LIST_CHOICES, default='por_ver')
    score = models.PositiveIntegerField('Puntuación (0-10)', blank=True, null=True)
    progress = models.PositiveIntegerField('Episodios vistos', default=0)
    notes = models.TextField('Notas', blank=True, null=True)
    is_favorite = models.BooleanField('Favorito', default=False)
    start_date = models.DateField('Fecha de inicio', blank=True, null=True)
    finish_date = models.DateField('Fecha de finalización', blank=True, null=True)
    rewatch_count = models.PositiveIntegerField('Veces visto', default=0)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'anime')
        ordering = ['-updated_at']
        verbose_name = 'Lista de anime'
        verbose_name_plural = 'Listas de anime'
    
    def __str__(self):
        return f"{self.user.username} - {self.anime.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        # Update finish date when status changes to completed
        if self.status == 'finalizado' and not self.finish_date:
            self.finish_date = timezone.now().date()
        super().save(*args, **kwargs)

class Episode(models.Model):
    """Model for anime episodes"""
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='episode_list')
    number = models.PositiveIntegerField('Número de episodio')
    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descripción', blank=True, null=True)
    duration = models.PositiveIntegerField('Duración (minutos)', default=24)
    air_date = models.DateField('Fecha de emisión', blank=True, null=True)
    video_url = models.URLField('URL del vídeo', blank=True, null=True)
    thumbnail = models.ImageField('Miniatura', upload_to='episode_thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    
    class Meta:
        ordering = ['number']
        unique_together = ('anime', 'number')
        verbose_name = 'Episodio'
        verbose_name_plural = 'Episodios'
    
    def __str__(self):
        return f"{self.anime.title} - Episodio {self.number}: {self.title}"

class Comment(models.Model):
    """Model for user comments on anime"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anime_comments')
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField('Contenido')
    is_spoiler = models.BooleanField('Contiene spoilers', default=False)
    is_edited = models.BooleanField('Editado', default=False)
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    dislikes = models.ManyToManyField(User, related_name='disliked_comments', blank=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
    
    def __str__(self):
        return f"Comentario de {self.user.username} en {self.anime.title}"
    
    def save(self, *args, **kwargs):
        if self.pk:  # If the comment already exists
            self.is_edited = True
        super().save(*args, **kwargs)
    
    def get_like_count(self):
        return self.likes.count()
    
    def get_dislike_count(self):
        return self.dislikes.count()

class WatchHistory(models.Model):
    """Model to track user's watched episodes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='watch_history')
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='watch_history')
    watched_at = models.DateTimeField('Visto el', auto_now_add=True)
    progress = models.PositiveIntegerField('Progreso (segundos)', default=0)
    is_completed = models.BooleanField('Completado', default=False)
    
    class Meta:
        ordering = ['-watched_at']
        verbose_name = 'Historial de visualización'
        verbose_name_plural = 'Historial de visualizaciones'
        unique_together = ('user', 'episode')
    
    def __str__(self):
        return f"{self.user.username} - {self.episode.anime.title} Ep. {self.episode.number}"

class Notification(models.Model):
    """Model for user notifications"""
    NOTIFICATION_TYPES = [
        ('comment', 'Nuevo comentario'),
        ('reply', 'Respuesta a tu comentario'),
        ('like', 'Me gusta en tu comentario'),
        ('follow', 'Nuevo seguidor'),
        ('system', 'Notificación del sistema'),
        ('anime_update', 'Actualización de anime'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField('Tipo', max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField('Mensaje')
    is_read = models.BooleanField('Leído', default=False)
    related_id = models.PositiveIntegerField('ID relacionado', blank=True, null=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.user.username}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    @classmethod
    def create_notification(cls, user, notification_type, message, related_id=None):
        """Helper method to create notifications"""
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            message=message,
            related_id=related_id
        )

class Rating(models.Model):
    """Model for user ratings of anime"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anime_ratings')
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='ratings')
    score = models.PositiveSmallIntegerField('Puntuación', choices=[(i, str(i)) for i in range(1, 11)])  # 1-10 scale
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        unique_together = ('user', 'anime')
        verbose_name = 'Valoración'
        verbose_name_plural = 'Valoraciones'
    
    def __str__(self):
        return f"{self.user.username} - {self.anime.title}: {self.score}/10"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the anime's average rating
        self.anime.update_average_rating()

class News(models.Model):
    """Model for news and announcements"""
    title = models.CharField('Título', max_length=200)
    slug = models.SlugField('Slug', max_length=200, unique=True)
    content = models.TextField('Contenido')
    image = models.ImageField('Imagen', upload_to='news/', blank=True, null=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='news_posts')
    is_published = models.BooleanField('Publicado', default=False)
    publication_date = models.DateTimeField('Fecha de publicación', default=timezone.now)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        ordering = ['-publication_date']
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class ForumThread(models.Model):
    """Model for forum discussion threads"""
    title = models.CharField('Título', max_length=200)
    slug = models.SlugField('Slug', max_length=200, unique=True)
    content = models.TextField('Contenido')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_threads')
    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='forum_threads', null=True, blank=True)
    is_pinned = models.BooleanField('Fijado', default=False)
    is_closed = models.BooleanField('Cerrado', default=False)
    view_count = models.PositiveIntegerField('Vistas', default=0)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = 'Tema del foro'
        verbose_name_plural = 'Temas del foro'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('forum:thread_detail', kwargs={'slug': self.slug})

class ForumPost(models.Model):
    """Model for forum posts (replies in threads)"""
    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    content = models.TextField('Contenido')
    is_edited = models.BooleanField('Editado', default=False)
    likes = models.ManyToManyField(User, related_name='liked_forum_posts', blank=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Mensaje del foro'
        verbose_name_plural = 'Mensajes del foro'
    
    def __str__(self):
        return f"Respuesta de {self.author.username} en '{self.thread.title}'"
    
    def save(self, *args, **kwargs):
        if self.pk:  # If the post already exists
            self.is_edited = True
        super().save(*args, **kwargs)
        # Update the thread's updated_at timestamp
        ForumThread.objects.filter(pk=self.thread_id).update(updated_at=timezone.now())

# Signals to create/update user profile when User is created/updated
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
