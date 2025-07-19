# Admin/templatetags/get_attribute.py
from django import template

register = template.Library()

@register.filter
def getattribute(value, arg):
    """Gets an attribute of an object dynamically."""
    if hasattr(value, str(arg)):
        return getattr(value, str(arg))
    elif isinstance(value, dict) and arg in value:
        return value[arg]
    return None # Or raise an exception, or return an empty string