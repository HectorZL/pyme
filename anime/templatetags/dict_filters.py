from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get a dictionary value by key.
    Usage: {{ my_dict|get_item:key_var }}
    """
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
