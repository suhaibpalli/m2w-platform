from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Template filter to lookup dictionary value by key"""
    try:
        return dictionary.get(key, [])
    except AttributeError:
        return []
