from functools import wraps
from django.http import HttpRequest
from django.utils import timezone
from Admin.models import APIList
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings

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


def staff_member_required(function=None, redirect_field_name='next', login_url=None):
    """
    Decorator for views that checks that the user is logged in and is a staff member,
    displaying the login page if necessary. It ensures the redirect goes to the
    configured LOGIN_URL in settings.
    """
    actual_login_url = login_url or settings.LOGIN_URL
    return user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url=actual_login_url,
        redirect_field_name=redirect_field_name
    )(function)