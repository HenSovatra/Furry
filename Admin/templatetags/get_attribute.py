# Example: Inside the same file that contains your get_attribute filter
from django import template

register = template.Library()

@register.filter
def get_attribute(value, arg):
    """Gets an attribute of an object or an item of a dictionary."""
    if hasattr(value, arg):
        return getattr(value, arg)
    if isinstance(value, dict):
        return value.get(arg)
    return None

@register.filter
def replace(value, arg):
    """
    Replaces all occurrences of a substring with another in a string.
    Usage: {{ my_string|replace:"old_substring,new_substring" }}
    Example: {{ "Hello World"|replace:"World,Django" }} outputs "Hello Django"
    """
    if isinstance(value, str) and isinstance(arg, str):
        parts = arg.split(',')
        if len(parts) == 2:
            old_str = parts[0]
            new_str = parts[1]
            return value.replace(old_str, new_str)
    return value # Return original value if not a string or arg is malformed