import requests
from django.db.models import Sum, F
import json
import datetime
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.apps import apps
from django.db.models import ForeignKey, ManyToManyField, DateTimeField, IntegerField, EmailField, CharField, TextField, DecimalField, BooleanField, ImageField
from django.urls import reverse
import csv
from Admin.models import Customer, Order
from django.db import models
from io import StringIO
from .models import *
from PetStore.models import Product as PetStoreProduct, Category
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from urllib.parse import urlparse, parse_qs, quote

from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from django.db.models import Count
from decimal import Decimal
from datetime import datetime, timedelta
from APIs.decorators import staff_member_required
import calendar # Import the calendar module to get days in a month
import logging
import stripe
logger = logging.getLogger(__name__)


BASE_API_URL = "http://127.0.0.1:8000/api/"

API_ENDPOINTS = {
    'product': 'admin/products/',
    'customer': 'register-customers/',
    'order': 'admin/orders/',
    'orderitem': 'admin/orderitems/',
    'billing': 'admin/billings/',
    'category': 'admin/categories/',
}

def get_monthly_stripe_revenue(target_date: datetime) -> float:
    """
    Calculates the total *Stripe* revenue for a specific month.
    Converts the target_date to UTC for Stripe API filtering.

    Args:
        target_date: A timezone-aware datetime object representing any day within
                     the month for which to calculate revenue (e.g., datetime.now()
                     for the current month, or a specific date for a past month).

    Returns:
        The total revenue in the primary currency unit (e.g., dollars, not cents).
        Returns 0.0 if no successful payments are found or on error.
    """
    if not stripe.api_key:
        logger.error("Error: STRIPE_SECRET_KEY not set. Please set your Stripe secret key in settings.py.")
        return 0.0

    # Calculate the first day of the target month in the project's timezone
    start_of_month_local = timezone.make_aware(
        datetime(target_date.year, target_date.month, 1),
        timezone.get_current_timezone()
    )

    # Calculate the last day of the target month
    # Get the number of days in the target month
    _, num_days_in_month = calendar.monthrange(target_date.year, target_date.month)
    end_of_month_local = timezone.make_aware(
        datetime(target_date.year, target_date.month, num_days_in_month),
        timezone.get_current_timezone()
    )
    # Set time to the very end of the last day
    end_of_month_local = end_of_month_local.replace(hour=23, minute=59, second=59, microsecond=999999)


    # Convert local timezone datetimes to UTC timestamps for Stripe API
    start_timestamp_utc = int(start_of_month_local.timestamp())
    end_timestamp_utc = int(end_of_month_local.timestamp())

    total_amount_cents = 0
    has_more = True
    starting_after = None

    try:
        while has_more:
            payments = stripe.PaymentIntent.list(
                created={
                    'gte': start_timestamp_utc,
                    'lte': end_timestamp_utc
                },
                limit=100, # Max limit per request
                starting_after=starting_after
            )

            for payment in payments.data:
                # Filter by status AFTER receiving the data from Stripe
                if payment.status == 'succeeded':
                    total_amount_cents += payment.amount
                    # logger.info(f"  - PI: {payment.id}, Status: {payment.status}, Amount: {payment.amount / 100:.2f} {payment.currency.upper()}")

            has_more = payments.has_more
            if has_more:
                starting_after = payments.data[-1].id

        return total_amount_cents / 100.0

    except stripe.error.StripeError as e:
        logger.error(f"Stripe API Error fetching payments for {target_date.strftime('%Y-%m')}: {e}")
        return 0.0
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching Stripe data for {target_date.strftime('%Y-%m')}: {e}")
        return 0.0

def get_model_fields(model):
    fields = []
    fk_fields = {}
    read_only_fields = ['id', 'created_at', 'updated_at']
    fk_fields_keys = []
    choices_dict = {}
    integer_fields = []
    date_time_fields = []
    email_fields = []
    text_fields = []

    for field in model._meta.get_fields():
        if field.concrete and not field.auto_created:
            field_name = field.name
            fields.append(field_name)

            if isinstance(field, ForeignKey):
                fk_fields[field_name] = field.related_model.objects.all()
                fk_fields_keys.append(field_name)
            elif isinstance(field, ManyToManyField):
                read_only_fields.append(field_name)
            elif field.choices:
                choices_dict[field_name] = field.choices
            elif isinstance(field, IntegerField):
                integer_fields.append(field_name)
            elif isinstance(field, DateTimeField):
                date_time_fields.append(field_name)
            elif isinstance(field, EmailField):
                email_fields.append(field_name)
            elif isinstance(field, CharField) or isinstance(field, TextField):
                text_fields.append(field_name)
            elif isinstance(field, DecimalField):
                text_fields.append(field_name)
            elif isinstance(field, BooleanField):
                read_only_fields.append(field_name)
            elif isinstance(field, ImageField):
                read_only_fields.append(field_name)

    return {
        'db_field_names': fields,
        'fk_fields': fk_fields,
        'read_only_fields': read_only_fields,
        'fk_fields_keys': fk_fields_keys,
        'choices_dict': choices_dict,
        'integer_fields': integer_fields,
        'date_time_fields': date_time_fields,
        'email_fields': email_fields,
        'text_fields': text_fields,
    }
@staff_member_required
def get_base_context(request, model_name=None):
    context = {}
    path_segments = request.path.strip('/').split('/')
    if len(path_segments) > 1 and path_segments[1] == 'my-admin':
        if len(path_segments) > 2:
            context['segment'] = path_segments[2].replace('-', '_')
        else:
            context['segment'] = 'dashboard'

    if model_name:
        context['link'] = model_name

    model_map_for_context = {
        'product': PetStoreProduct,
        'customer': Customer,
        'order': Order,
        'orderitem': apps.get_model('Admin', 'OrderItem') if apps.is_installed('Admin') and 'OrderItem' in [m._meta.model_name for m in apps.get_app_config('Admin').get_models()] else None,
        'billing': Billing,
    }
    context['model_map'] = model_map_for_context
    return context

@staff_member_required
def dashboard(request):
    context = get_base_context(request)
    context['segment'] = 'dashboard'
    context['page_title'] = "Admin Dashboard"

    # Products
    context['total_products'] = PetStoreProduct.objects.count()

    # --- AGGREGATED PRODUCT DATA FOR CHART (Daily, Weekly, Monthly, Yearly) ---
    daily_products_counts_queryset = PetStoreProduct.objects \
        .annotate(period=TruncDay('created_at')) \
        .values('period') \
        .annotate(count=Count('id')) \
        .order_by('period')

    daily_product_data = []
    for entry in daily_products_counts_queryset:
        daily_product_data.append({
            'label': entry['period'].strftime('%b %d'),
            'value': entry['count']
        })
    context['daily_product_data'] = daily_product_data

    weekly_products_counts_queryset = PetStoreProduct.objects \
        .annotate(period=TruncWeek('created_at')) \
        .values('period') \
        .annotate(count=Count('id')) \
        .order_by('period')

    weekly_product_data = []
    for entry in weekly_products_counts_queryset:
        weekly_product_data.append({
            'label': entry['period'].strftime('Wk %W, %Y'),
            'value': entry['count']
        })
    context['weekly_product_data'] = weekly_product_data

    monthly_products_counts_queryset = PetStoreProduct.objects \
        .annotate(period=TruncMonth('created_at')) \
        .values('period') \
        .annotate(count=Count('id')) \
        .order_by('period')

    monthly_product_data = []
    for entry in monthly_products_counts_queryset:
        monthly_product_data.append({
            'label': entry['period'].strftime('%B %Y'),
            'value': entry['count']
        })
    context['monthly_product_data'] = monthly_product_data

    yearly_products_counts_queryset = PetStoreProduct.objects \
        .annotate(period=TruncYear('created_at')) \
        .values('period') \
        .annotate(count=Count('id')) \
        .order_by('period')

    yearly_product_data = []
    for entry in yearly_products_counts_queryset:
        yearly_product_data.append({
            'label': entry['period'].strftime('%Y'),
            'value': entry['count']
        })
    context['yearly_product_data'] = yearly_product_data
    # --- END AGGREGATED PRODUCT DATA ---

    # Optional: Calculate product growth based on actual daily data
    context['product_growth'] = 0
    if len(daily_product_data) >= 2:
        latest_count = daily_product_data[-1]['value']
        previous_count = daily_product_data[-2]['value']
        if previous_count > 0:
            context['product_growth'] = round(((latest_count - previous_count) / previous_count) * 100)
        else:
            context['product_growth'] = 100 if latest_count > 0 else 0


    # Get registered customers (not admin ones) - Assumes an external API call
    try:
        customer_response = requests.get("http://127.0.0.1:8000/api/register-customers/")
        if customer_response.status_code == 200:
            context['total_customers'] = len(customer_response.json())
        else:
            context['total_customers'] = 0
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching total customers: {e}")
        context['total_customers'] = 0

    # Orders (still from your API/DB if you want total order count separate from Stripe revenue)
    # Assumes an external API call for order count
    try:
        order_response = requests.get("http://127.0.0.1:8000/api/admin/orders/")
        if order_response.status_code == 200:
            orders = order_response.json()
            context['total_orders'] = len(orders)
            # Removed raw_total and total_revenue calculation from internal API here
            # as it's now handled by Stripe below
        else:
            context['total_orders'] = 0
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching total orders: {e}")
        context['total_orders'] = 0

    # --- STRIPE REVENUE CALCULATIONS FOR THIS MONTH AND LAST MONTH ---
    current_date = timezone.now()

    # This Month's Revenue
    context['stripe_revenue_this_month'] = get_monthly_stripe_revenue(current_date)

    # Last Month's Revenue
    # Calculate a date in the previous month (e.g., Dec 31st if current month is Jan)
    first_day_of_this_month = timezone.make_aware(
        datetime(current_date.year, current_date.month, 1),
        timezone.get_current_timezone()
    )
    last_month_date = first_day_of_this_month - timedelta(days=1)
    context['stripe_revenue_last_month'] = get_monthly_stripe_revenue(last_month_date)


    # Calculate percentage change for revenue (This Month vs Last Month)
    revenue_percentage_change = 0.0
    is_revenue_increase = False
    is_revenue_infinite_increase = False # Flag for +Infinite%

    if context['stripe_revenue_last_month'] > 0:
        revenue_percentage_change = (
            (context['stripe_revenue_this_month'] - context['stripe_revenue_last_month']) / context['stripe_revenue_last_month']
        ) * 100
        is_revenue_increase = revenue_percentage_change >= 0
        revenue_percentage_change = abs(revenue_percentage_change)
    elif context['stripe_revenue_this_month'] > 0 and context['stripe_revenue_last_month'] == 0:
        # If this month's revenue is positive and last month's was zero, it's an "infinite" increase
        is_revenue_infinite_increase = True
        is_revenue_increase = True # It is definitely an increase
    else: # Both this month and last month are 0, or revenue_percentage_change is exactly 0
        revenue_percentage_change = 0.0
        is_revenue_increase = False # Consider it no change

    context['revenue_percentage_change'] = revenue_percentage_change
    context['is_revenue_increase'] = is_revenue_increase
    context['is_revenue_infinite_increase'] = is_revenue_infinite_increase
    # ------------------------------------------------------------------

    # Feedback - Assumes an external API call
    try:
        feedback_response = requests.get("http://127.0.0.1:8000/api/feedback/")
        if feedback_response.status_code == 200:
            context['feedback_list'] = feedback_response.json()
        else:
            context['feedback_list'] = []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching feedback: {e}")
        context['feedback_list'] = []

    return render(request, 'admin_app/index.html', context)


@staff_member_required
def dynamic_api_overview(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_api'
    context['page_title'] = "Dynamic API Endpoints Overview"

    managed_models = {
        'product': PetStoreProduct,
        'customer': Customer,
        'order': Order,
        'orderitem': apps.get_model('Admin', 'OrderItem') if apps.is_installed('APIs') and 'OrderItem' in [m._meta.model_name for m in apps.get_app_config('APIs').get_models()] else None,
        'billing': Billing,
    }

    # Model-based routes
    available_routes = [
        {
            "name": name,
            "url": f"/admin/dynamic-api/{name}/"
        }
        for name, model_cls in managed_models.items() if model_cls is not None
    ]

    custom_apis = [
        {"name": "categories", "url": "/api/admin/categories/"},
        {"name": "orders", "url": "/api/admin/orders/"},
        {"name": "customers", "url": "/api/register-customers/"},
        {"name": "products", "url": "/api/admin/products/"},
        {"name": "register-customers", "url": "/api/register-customers/"},
        {"name": "feedback", "url": "/api/feedback/"},
        {"name": "posts", "url": "/api/posts/"},
        {"name": "admin-orders", "url": "/api/admin/orders/"},
    ]

    context['routes'] = available_routes + custom_apis
    return render(request, 'admin_app/dyn_api/index.html', context)

@staff_member_required
def dynamic_dt_overview(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_dt' # For active menu highlighting

    # Determine the main item type (product, order, orderitem, etc.)
    main_item = request.GET.get('main_item', 'product').lower()
    print("Main item is:", main_item) # For debugging

    # Get filtering and pagination parameters from request
    category = request.GET.get('category', 'All') # For products
    search_query = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    # Get items per page from session, default to 10
    page_items_count = request.session.get(f'page_items_{main_item}', 10)

    # Get the API path for the selected main item
    api_path = API_ENDPOINTS.get(main_item)
    if not api_path:
        return HttpResponse("API endpoint not found for selected item.", status=404)

    # Prepare parameters for the API request
    params = {'page': page, 'page_size': page_items_count}
    if search_query:
        params['search'] = search_query

    # Special filtering for 'product' by category
    if main_item == 'product' and category != 'All':
        try:
            category_obj = Category.objects.get(name__iexact=category)
            params['category'] = category_obj.id
        except Category.DoesNotExist:
            # If category not found, no category filter is applied
            pass

    # Special filtering for 'order' by status
    if main_item == 'order':
        status_filter = request.GET.get('status', 'All')
        context['set_status'] = status_filter # Pass status to context for template
        if status_filter != 'All':
            params['status'] = status_filter

    # Apply any saved filters from session (e.g., from a filter form)
    filter_data = request.session.get(f'filters_{main_item}', [])
    for f_data in filter_data:
        key = f_data.get('key')
        value = f_data.get('value')
        if key and value:
            params[key] = value

    # Construct the full API URL
    api_url = f"{BASE_API_URL}{api_path}"

    items = []
    total_count = 0
    try:
        # Make the API request
        response = requests.get(api_url, params=params)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        api_data = response.json()

        # Handle paginated (DRF's default) or unpaginated list responses
        if isinstance(api_data, list):
            items = api_data
            total_count = len(api_data)
        else:
            items = api_data.get('results', [])
            total_count = api_data.get('count', 0)

    except requests.exceptions.RequestException as e:
        # Log the error and return an HTTP error response
        print(f"API Error fetching {main_item} data: {e}")
        return HttpResponse(f"Error fetching data from API: {e}", status=500)

    # Custom Paginator Class to wrap API results in a Django-like Paginator Page object
    class ApiPaginatorPage:
        def __init__(self, data, count, page_num, page_size):
            self.object_list = data # The items for the current page
            self.number = int(page_num) # Current page number
            # Create a dummy paginator object with num_pages and count
            self.paginator = type('Paginator', (object,), {
                'num_pages': (count + page_size - 1) // page_size if page_size > 0 else 1,
                'count': count
            })()

        def has_next(self):
            return self.number < self.paginator.num_pages

        def has_previous(self):
            return self.number > 1

        def next_page_number(self):
            return self.number + 1

        def previous_page_number(self):
            return self.number - 1

        # These methods are often used by Django's pagination templates
        def start_index(self):
            # Calculate the starting index of items on the current page
            if self.paginator.count == 0:
                return 0
            return (self.number - 1) * page_items_count + 1

        def end_index(self):
            # Calculate the ending index of items on the current page
            return min(self.number * page_items_count, self.paginator.count)

        def __iter__(self):
            return iter(self.object_list) # Make it iterable like a QuerySet

    paginated_items = ApiPaginatorPage(items, total_count, page, page_items_count)

    # Set page title based on the selected item and category
    page_title = f"{main_item.replace('_', ' ').capitalize()} Management"
    if main_item == 'product' and category != 'All':
        try:
            # Try to get the category name for the title
            category_name = Category.objects.filter(id=params.get('category')).first().name
            page_title = f"{category_name} Products Management"
        except AttributeError:
            # Handle case where category_name might be None if category not found
            pass
    context['page_title'] = page_title

    # Add relevant parameters to context for template use (e.g., dropdown selection)
    context['set_main_item'] = main_item
    context['set_category'] = category
    context['search_query'] = search_query # Pass search query back to template for input field

    # Determine the actual Django model based on main_item
    model = None
    if main_item.lower() == 'product':
        model = PetStoreProduct
    elif main_item.lower() == 'category':
        model = Category
    elif main_item.lower() == 'order':
        model = Order
    elif main_item.lower() == 'orderitem':
        model = OrderItem
    else:
        # Fallback for other potential models in the 'Admin' app
        try:
            model = apps.get_model('Admin', main_item.capitalize())
        except LookupError:
            return HttpResponse(f"Model '{main_item.capitalize()}' not found.", status=404)


    if not model:
        return HttpResponse("Could not determine model for field information.", status=500)

    # Get model field information for dynamic table headers and filters
    model_info = get_model_fields(model)
    context.update(model_info) # Adds 'field_headers' and 'db_field_names' to context

    # Add items and pagination object to context
    context['items'] = paginated_items
    context['db_filters'] = model_info['db_field_names'] # For dynamic filtering options
    context['filter_instance'] = filter_data # Existing filters from session
    context['page_items'] = page_items_count # Items per page for UI control
    context['model_name'] = main_item # The lowercase name of the current model
    context['set_page'] = int(page) # Current page number for pagination UI

    print(f"Items for {main_item}:", [item.get('id') for item in paginated_items.object_list]) # Print IDs for debugging
    return render(request, 'admin_app/dyn_dt/model.html', context)

@staff_member_required
def create_item(request, model_name):
    if request.method == 'POST':
        api_path = API_ENDPOINTS.get(model_name)
        if not api_path:
            return HttpResponse("Invalid model name.", status=400)

        api_url = f"{BASE_API_URL}{api_path}"

        data = {}
        files = {}

        if model_name == 'product':
            if 'name' in request.POST:
                data['name'] = request.POST['name']
            if 'description' in request.POST:
                data['description'] = request.POST['description']
            if 'original_price' in request.POST:
                data['original_price'] = request.POST['original_price']
            if 'discounted_price' in request.POST:
                data['discounted_price'] = request.POST['discounted_price']

            if 'stock' in request.POST:
                try:
                    data['stock'] = int(request.POST['stock'])
                except (ValueError, TypeError):
                    pass # Handle error or set a default

            if 'category' in request.POST and request.POST['category']:
                try:
                    data['category_id'] = int(request.POST['category'])
                except (ValueError, TypeError):
                    return HttpResponse("Invalid category ID provided. Must be a number.", status=400)
            else:
                return HttpResponse("Category is required for new products. Please select one.", status=400)

            data['is_active'] = 'is_active' in request.POST

            if 'image' in request.FILES:
                files['image'] = request.FILES['image']

        # --- NEW LOGIC FOR 'customer' (Add new user/customer) ---
        elif model_name == 'customer':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password') # This is what HTML sends

            # Basic Validation (already there)
            if not username or not email or not password or not confirm_password: # Add confirm_password to validation
                encoded_error = quote("Username, Email, Password, and Confirm Password are required.")
                return redirect(reverse('Admin:dynamic_dt_overview') +
                                f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")

            if password != confirm_password:
                encoded_error = quote("Passwords do not match.")
                return redirect(reverse('Admin:dynamic_dt_overview') +
                                f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")

            # Prepare data for API call
            data['username'] = username
            data['email'] = email
            data['password'] = password
            data['password2'] = confirm_password # <-- ADD THIS LINE to map confirm_password to password2
            data['first_name'] = request.POST.get('first_name', '')
            data['last_name'] = request.POST.get('last_name', '')
            data['phone_number'] = request.POST.get('phone_number', '')
            data['address'] = request.POST.get('address', '')
            # The 'register-customers/' API is expected to handle creating both User and Customer profile

        # --- END NEW LOGIC FOR 'customer' ---

        print(f"Data being sent to API for {model_name} (Create): {data}")
        print(f"Files being sent to API for {model_name} (Create): {files}")

        try:
            response = requests.post(api_url, data=data, files=files if files else None)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}&create_success=true")

        except requests.exceptions.RequestException as e:
            print(f"Error creating item: {e}")
            error_message_from_api = "An unknown error occurred during item addition."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    json_content = e.response.json()
                    if isinstance(json_content, dict):
                        if 'detail' in json_content:
                            error_message_from_api = json_content['detail']
                        else:
                            error_messages = []
                            for field, errors in json_content.items():
                                if isinstance(errors, list):
                                    error_messages.append(f"{field.replace('_', ' ').title()}: {', '.join(errors)}")
                                elif isinstance(errors, dict):
                                    for sub_field, sub_errors in errors.items():
                                        if isinstance(sub_errors, list):
                                            error_messages.append(f"{field.replace('_', ' ').title()} - {sub_field.replace('_', ' ').title()}: {', '.join(sub_errors)}")
                                        else:
                                            error_messages.append(f"{field.replace('_', ' ').title()} - {sub_field.replace('_', ' ').title()}: {sub_errors}")
                                else:
                                    error_messages.append(f"{field.replace('_', ' ').title()}: {errors}")
                            error_message_from_api = "; ".join(error_messages)
                    else:
                        error_message_from_api = str(json_content)
                except json.JSONDecodeError:
                    error_message_from_api = e.response.text
                except Exception as ex:
                    print(f"Error processing API JSON response: {ex}")
                    error_message_from_api = f"API responded with an unreadable error: {e.response.text}"
            else:
                error_message_from_api = f"Request failed before API could respond: {str(e)}"

            encoded_error = quote(error_message_from_api)
            return redirect(reverse('Admin:dynamic_dt_overview') +
                            f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")
    else:
        return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}")

@staff_member_required
def update_item(request, model_name, item_id):
    if request.method == 'POST':
        print(f"RAW request.POST at start of update_item: {request.POST}")

        api_path = API_ENDPOINTS.get(model_name)
        if not api_path:
            return HttpResponse("Invalid model name.", status=400)

        api_url = f"{BASE_API_URL}{api_path}{item_id}/"

        data = {}
        files = {}

        if model_name == 'product':
            if 'name' in request.POST:
                data['name'] = request.POST['name']
            if 'description' in request.POST:
                data['description'] = request.POST['description']
            if 'original_price' in request.POST:
                data['original_price'] = request.POST['original_price']
            if 'discounted_price' in request.POST:
                data['discounted_price'] = request.POST['discounted_price']

            if 'stock' in request.POST:
                try:
                    data['stock'] = int(request.POST['stock'])
                except (ValueError, TypeError):
                    pass

            if 'category' in request.POST and request.POST['category']:
                try:
                    data['category_id'] = int(request.POST['category'])
                except (ValueError, TypeError):
                    pass

            data['is_active'] = 'is_active' in request.POST

            if 'created_at' in request.POST:
                data['created_at'] = request.POST['created_at']

            if 'image' in request.FILES:
                files['image'] = request.FILES['image']
            else:
                pass
        elif model_name == 'order':
            data['total_amount'] = request.POST.get('total_amount')
            data['status'] = request.POST.get('status')
            data['payment_status'] = request.POST.get('payment_status')
            data['payment_method'] = request.POST.get('payment_method')
            data['shipping_cost'] = request.POST.get('shipping_cost')
            
            data['billing_first_name'] = request.POST.get('billing_first_name')
            data['billing_last_name'] = request.POST.get('billing_last_name')
            data['billing_email'] = request.POST.get('billing_email')
            data['billing_phone'] = request.POST.get('billing_phone')
            data['billing_address_line_1'] = request.POST.get('billing_address_line_1')
            data['billing_address_line_2'] = request.POST.get('billing_address_line_2')
            data['billing_city'] = request.POST.get('billing_city')
            data['billing_state'] = request.POST.get('billing_state')
            data['billing_zip_code'] = request.POST.get('billing_zip_code')
            data['billing_country'] = request.POST.get('billing_country')

            data['first_name'] = request.POST.get('first_name')
            data['last_name'] = request.POST.get('last_name')
            data['email'] = request.POST.get('email')
            data['phone'] = request.POST.get('phone')
            data['address_line_1'] = request.POST.get('address_line_1')
            data['address_line_2'] = request.POST.get('address_line_2')
            data['city'] = request.POST.get('city')
            data['state'] = request.POST.get('state')
            data['zip_code'] = request.POST.get('zip_code')
            data['country'] = request.POST.get('country')

            for key, value in list(data.items()):
                if value == '':
                    data[key] = None

            if data.get('total_amount'):
                try:
                    data['total_amount'] = float(data['total_amount'])
                except (ValueError, TypeError):
                    del data['total_amount']
            if data.get('shipping_cost'):
                try:
                    data['shipping_cost'] = float(data['shipping_cost'])
                except (ValueError, TypeError):
                    del data['shipping_cost']

        print(f"Data being sent to API for {model_name}: {data}")
        print(f"Files being sent to API for {model_name}: {files}")

        try:
            response = requests.patch(api_url, data=data, files=files if files else None)

            response.raise_for_status()
            return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}&update_success=true")

        except requests.exceptions.RequestException as e:
            print(f"Error updating item: {e}")
            error_message_from_api = "An unknown error occurred during item update."
            if hasattr(e, 'response') and e.response is not None:
                try:
                    json_content = e.response.json()
                    if isinstance(json_content, dict):
                        if 'detail' in json_content:
                            error_message_from_api = json_content['detail']
                        else:
                            error_messages = []
                            for field, errors in json_content.items():
                                if isinstance(errors, list):
                                    error_messages.append(f"{field.replace('_', ' ').title()}: {', '.join(errors)}")
                                elif isinstance(errors, dict):
                                    for sub_field, sub_errors in errors.items():
                                        if isinstance(sub_errors, list):
                                            error_messages.append(f"{field.replace('_', ' ').title()} - {sub_field.replace('_', ' ').title()}: {', '.join(sub_errors)}")
                                        else:
                                            error_messages.append(f"{field.replace('_', ' ').title()} - {sub_field.replace('_', ' ').title()}: {sub_errors}")
                                else:
                                    error_messages.append(f"{field.replace('_', ' ').title()}: {errors}")
                            error_message_from_api = "; ".join(error_messages)
                    else:
                        error_message_from_api = str(json_content)
                except json.JSONDecodeError:
                    error_message_from_api = e.response.text
                except Exception as ex:
                    print(f"Error processing API JSON response: {ex}")
                    error_message_from_api = f"API responded with an unreadable error: {e.response.text}"
            else:
                error_message_from_api = f"Request failed before API could respond: {str(e)}"
            print(f"--- Diagnostic Info End ---")

            encoded_error = quote(error_message_from_api)
            return redirect(reverse('Admin:dynamic_dt_overview') +
                            f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")

    else:
        return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}")

@staff_member_required
def delete_item(request, model_name, item_id):
    api_path = API_ENDPOINTS.get(model_name)
    if not api_path:
        return HttpResponse("Invalid model name.", status=400)

    api_url = f"{BASE_API_URL}{api_path}{item_id}/"

    if request.method == 'DELETE':
        try:
            response = requests.delete(api_url)
            response.raise_for_status()

            return JsonResponse({'message': f'{model_name.title()} (ID: {item_id}) deleted successfully.'}, status=204)

        except requests.exceptions.RequestException as e:
            print(f"API Error deleting {model_name} (ID: {item_id}): {e}")
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                print(f"API Response Content: {e.response.text}")
                try:
                    api_error_details = e.response.json()
                    error_message = api_error_details
                except json.JSONDecodeError:
                    error_message = e.response.text

            return JsonResponse({'error': error_message}, status=e.response.status_code if hasattr(e, 'response') and e.response is not None else 500)
    else:
        return HttpResponse("Invalid request method.", status=405)

@staff_member_required
def export_csv_view(request, link):
    model_name = link.lower()

    api_path = API_ENDPOINTS.get(model_name)
    if not api_path:
        return HttpResponse("API endpoint not found for export operation.", status=404)

    api_url = f"{BASE_API_URL}{api_path}"

    search_query = request.GET.get('search', '')
    params = {}
    if search_query:
        params['search'] = search_query

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        api_data = response.json()

        items_data = api_data.get('results', api_data)

    except requests.exceptions.RequestException as e:
        print(f"API Error fetching {model_name} data for CSV export: {e}")
        return HttpResponse(f"Error fetching data for export: {e}", status=500)

    model = apps.get_model('Admin', model_name.capitalize()) if model_name not in ['product', 'category'] else (PetStoreProduct if model_name == 'product' else Category)
    if model_name == 'orderitem' and not model:
        model = apps.get_model('PetStore', 'OrderItem')
    if not model:
        return HttpResponse("Model not found for CSV field names.", status=500)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{model_name}_data.csv"'

    writer = csv.writer(response)
    field_names = [field.name for field in model._meta.fields if not field.auto_created]
    writer.writerow(field_names)

    for item_dict in items_data:
        row = []
        for field_name in field_names:
            value = item_dict.get(field_name, '')
            row.append(str(value))
        writer.writerow(row)
    return response

@staff_member_required
def create_hide_show_items_view(request, link):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            key = data.get('key')
            value = data.get('value')

            session_key = f'hidden_columns_{link}'
            hidden_columns = request.session.get(session_key, [])

            if value:
                if key not in hidden_columns:
                    hidden_columns.append(key)
            else:
                if key in hidden_columns:
                    hidden_columns.remove(key)

            request.session[session_key] = hidden_columns
            request.session.modified = True
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
@staff_member_required
def create_page_items_view(request, link):
    if request.method == 'POST':
        items_per_page = request.POST.get('items')
        try:
            items_per_page = int(items_per_page)
            request.session[f'page_items_{link}'] = items_per_page
            request.session.modified = True
            return JsonResponse({'status': 'success'})
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid items per page value'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
@staff_member_required
def create_filter_view(request, link):
    if request.method == 'POST':
        filter_data = []
        keys = request.POST.getlist('key')
        values = request.POST.getlist('value')

        for i in range(len(keys)):
            if keys[i] and values[i]:
                filter_data.append({'key': keys[i], 'value': values[i], 'id': i + 1})

        request.session[f'filters_{link}'] = filter_data
        request.session.modified = True
        referer_path = request.META.get('HTTP_REFERER', '/')
        main_item = link
        category = 'All'
        if 'main_item=' in referer_path:
            parsed_url = urlparse(referer_path)
            query_params = parse_qs(parsed_url.query)
            main_item = query_params.get('main_item', [link])[0]
            category = query_params.get('category', ['All'])[0]

        return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={main_item}&category={category}")
    return HttpResponse("Invalid request method for create filter.", status=405)
@staff_member_required
def delete_filter_view(request, link, filter_id):
    filter_id = int(filter_id)
    session_key = f'filters_{link}'
    filter_data = request.session.get(session_key, [])

    request.session[session_key] = [f for f in filter_data if f.get('id') != filter_id]
    request.session.modified = True
    referer_path = request.META.get('HTTP_REFERER', '/')
    main_item = link
    category = 'All'
    if 'main_item=' in referer_path:
        parsed_url = urlparse(referer_path)
        query_params = parse_qs(parsed_url.query)
        main_item = query_params.get('main_item', [link])[0]
        category = query_params.get('category', ['All'])[0]
    return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={main_item}&category={category}")
@staff_member_required
def model_api(request, model_name):
    try:
        model = apps.get_model('Admin', model_name.capitalize())
        if model_name.lower() == 'product':
            model = PetStoreProduct
    except LookupError:
        return JsonResponse({'error': 'Model not found.'}, status=404)

    if request.method == 'GET':
        items = list(model.objects.all().values())
        return JsonResponse(items, safe=False)
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            instance = model.objects.create(**data)
            return JsonResponse({'status': 'success', 'id': instance.id}, status=201)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
@staff_member_required
def charts(request):
    context = get_base_context(request)
    context['segment'] = 'charts'
    context['page_title'] = "Sales & Product Charts"

    
    # Annotate products by how many times they were bought
    product_sales = (
        PetStoreProduct.objects
        .annotate(total_quantity=Sum('orderitem__quantity'))
        .values('name', 'original_price', 'total_quantity')
        .order_by('-total_quantity')  # Sort by most bought
    )

    products_data = []
    for product in product_sales:
        products_data.append({
            'name': product['name'],
            'original_price': float(product['original_price']),
            'total_quantity': product['total_quantity'] or 0
        })

    context['products_for_chart'] = json.dumps(products_data)

    # Static dummy sales data
    sales_data = [
        {'date': '2024-01-01', 'amount': 1500},
        {'date': '2024-02-01', 'amount': 2200},
        {'date': '2024-03-01', 'amount': 1800},
        {'date': '2024-04-01', 'amount': 2500},
    ]
    context['sales_data_json'] = json.dumps(sales_data)

    daily_product_data = []
    for i in range(7):
        date = datetime.now() - timedelta(days=6-i)
        daily_product_data.append({
            'label': date.strftime('%b %d'),
            'value': 50 + i * 5 + (i % 2) * 10 # Dummy values
        })

    # Example: Weekly data for the last 4 weeks
    weekly_product_data = []
    for i in range(4):
        date = datetime.now() - timedelta(weeks=3-i)
        weekly_product_data.append({
            'label': f'Week {i+1}', # You might want to format this as "Jan 1 - Jan 7" etc.
            'value': 200 + i * 20 + (i % 2) * 30 # Dummy values
        })

    # Example: Monthly data for the last 6 months
    monthly_product_data = []
    for i in range(6):
        date = datetime.now().replace(day=1) - timedelta(days=30 * (5-i))
        monthly_product_data.append({
            'label': date.strftime('%b'),
            'value': 800 + i * 50 + (i % 2) * 100 # Dummy values
        })

    # Example: Yearly data for the last 3 years
    yearly_product_data = []
    for i in range(3):
        year = datetime.now().year - (2-i)
        yearly_product_data.append({
            'label': str(year),
            'value': 5000 + i * 500 + (i % 2) * 1000 # Dummy values
        })

    context['daily_product_data'] = json.dumps(daily_product_data)
    context['weekly_product_data'] = json.dumps(weekly_product_data)
    context['monthly_product_data'] = json.dumps(monthly_product_data)
    context['yearly_product_data'] = json.dumps(yearly_product_data)



    return render(request, 'admin_app/charts/index.html', context)
@staff_member_required
def billing(request):
    context = get_base_context(request)
    context['segment'] = 'billing'
    context['page_title'] = "Billing Management"

    invoices = Billing.objects.all().select_related('customer').order_by('-issue_date')
    context['invoices'] = invoices
    return render(request, 'admin_app/billing/index.html', context)

@staff_member_required
def user_management(request):
    context = get_base_context(request)
    context['segment'] = 'user_management'
    context['page_title'] = "User Account Management"

    User = get_user_model()
    users = User.objects.all().order_by('date_joined')
    context['users'] = users
    return render(request, 'admin_app/users/index.html', context)