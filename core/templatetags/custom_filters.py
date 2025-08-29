from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Template filter to lookup dictionary value by key, supports dot notation"""
    try:
        if '.' in str(key):
            # Handle nested dictionary access like 'industry.slug.total_products'
            keys = str(key).split('.')
            value = dictionary
            for k in keys:
                value = value.get(k, {})
            return value
        else:
            return dictionary.get(key, [])
    except (AttributeError, TypeError):
        return []
