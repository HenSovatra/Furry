from functools import wraps
from django.http import HttpRequest
from django.utils import timezone
from Admin.models import APIList

def track_api_usage(view_func):
    """
    Decorator to track the usage of an API endpoint.
    Assumes the view_func receives a request object as its first argument.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        # Construct the endpoint string.
        # request.path gives you the full path including the leading slash.
        endpoint_path = request.path

        try:
            api_entry, created = APIList.objects.get_or_create(endpoint=endpoint_path)
            api_entry.increment_usage() # This also saves the object
            if created:
                print(f"New API endpoint '{endpoint_path}' tracked.")
        except Exception as e:
            # Log the error, but don't prevent the API call from proceeding
            print(f"Error tracking API usage for {endpoint_path}: {e}")

        return view_func(request, *args, **kwargs)
    return wrapper
