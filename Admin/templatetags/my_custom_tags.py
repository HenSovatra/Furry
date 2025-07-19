from django import template

register = template.Library()

@register.filter
def getattribute(value, arg):
    """Gets an attribute of an object dynamically."""
    if hasattr(value, str(arg)):
        return getattr(value, str(arg))
    elif isinstance(value, dict) and str(arg) in value:
        return value[str(arg)]
    return None