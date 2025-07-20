from django import template
from ..models import UserAnimeList

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Custom template filter to get a dictionary value by key.
    Returns None if the key doesn't exist instead of raising an error.
    """
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def filter_by_status(queryset, status):
    """
    Filter a queryset of UserAnimeList items by status.
    """
    if not queryset:
        return queryset.none()
    return queryset.filter(status=status)

@register.filter
def filter_favorites(queryset, is_favorite=True):
    """
    Filter a queryset of UserAnimeList items by favorite status.
    """
    if not queryset:
        return queryset.none()
    return queryset.filter(is_favorite=is_favorite)

# You can add more custom filters here if needed
