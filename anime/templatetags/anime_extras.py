from django import template
from django.utils.safestring import mark_safe
from ..models import UserAnimeList

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Template filter to get dictionary item by key"""
    return dictionary.get(key)

@register.filter(name='get_status_class')
def get_status_class(status):
    """Returns the appropriate CSS class for a status"""
    status_classes = {
        'watching': 'btn-watching',
        'completed': 'btn-completed',
        'on_hold': 'btn-on_hold',
        'dropped': 'btn-dropped',
        'plan_to_watch': 'btn-plan_to_watch',
    }
    return status_classes.get(status, 'btn-outline-primary')

@register.filter(name='get_status_display')
def get_status_display(status):
    """Returns the display text for a status"""
    status_choices = dict(UserAnimeList.LIST_CHOICES)
    return status_choices.get(status, 'Añadir a mi lista')

@register.filter(name='get_status_badge')
def get_status_badge(status):
    """Returns a badge for the status"""
    status_choices = dict(UserAnimeList.LIST_CHOICES)
    status_classes = {
        'watching': 'bg-primary',
        'completed': 'bg-success',
        'on_hold': 'bg-warning text-dark',
        'dropped': 'bg-danger',
        'plan_to_watch': 'bg-secondary',
    }
    
    if status in status_choices:
        return mark_safe(
            f'<span class="badge {status_classes.get(status, "bg-secondary")} ' 
            f'text-uppercase">{status_choices[status]}</span>'
        )
    return ''
