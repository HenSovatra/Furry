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
import calendar 
import logging
import stripe
logger = logging.getLogger(__name__)
from django.contrib.auth.models import User

from django.conf import settings

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

    start_of_month_local = timezone.make_aware(
        datetime(target_date.year, target_date.month, 1),
        timezone.get_current_timezone()
    )

    _, num_days_in_month = calendar.monthrange(target_date.year, target_date.month)
    end_of_month_local = timezone.make_aware(
        datetime(target_date.year, target_date.month, num_days_in_month),
        timezone.get_current_timezone()
    )
    end_of_month_local = end_of_month_local.replace(hour=23, minute=59, second=59, microsecond=999999)


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


    base_domain_host = f"{settings.BASE_URL}"
    api_root = 'api/' 

    try:
        customer_url = f"{base_domain_host}/{api_root}register-customers/"
        customer_response = requests.get(customer_url)
        if customer_response.status_code == 200:
            context['total_customers'] = len(customer_response.json())
        else:
            logger.error(f"Failed to fetch customers from {customer_url}: Status {customer_response.status_code}")
            context['total_customers'] = 0
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching total customers from {customer_url}: {e}")
        context['total_customers'] = 0

    try:
        order_url = f"{base_domain_host}/{api_root}admin/orders/"
        order_response = requests.get(order_url)
        if order_response.status_code == 200:
            orders = order_response.json()
            context['total_orders'] = len(orders)
        else:
            logger.error(f"Failed to fetch orders from {order_url}: Status {order_response.status_code}")
            context['total_orders'] = 0
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching total orders from {order_url}: {e}")
        context['total_orders'] = 0

    current_date = timezone.now()

    context['stripe_revenue_this_month'] = get_monthly_stripe_revenue(current_date)

    first_day_of_this_month = timezone.make_aware(
        datetime(current_date.year, current_date.month, 1),
        timezone.get_current_timezone()
    )
    last_month_date = first_day_of_this_month - timedelta(days=1)
    context['stripe_revenue_last_month'] = get_monthly_stripe_revenue(last_month_date)

    revenue_percentage_change = 0.0
    is_revenue_increase = False
    is_revenue_infinite_increase = False

    if context['stripe_revenue_last_month'] > 0:
        revenue_percentage_change = (
            (context['stripe_revenue_this_month'] - context['stripe_revenue_last_month']) / context['stripe_revenue_last_month']
        ) * 100
        is_revenue_increase = revenue_percentage_change >= 0
        revenue_percentage_change = abs(revenue_percentage_change)
    elif context['stripe_revenue_this_month'] > 0 and context['stripe_revenue_last_month'] == 0:
        is_revenue_infinite_increase = True
        is_revenue_increase = True
    else:
        revenue_percentage_change = 0.0
        is_revenue_increase = False

    context['revenue_percentage_change'] = revenue_percentage_change
    context['is_revenue_increase'] = is_revenue_increase
    context['is_revenue_infinite_increase'] = is_revenue_infinite_increase

    try:
        feedback_url = f"{base_domain_host}/{api_root}feedback/"
        feedback_response = requests.get(feedback_url)
        if feedback_response.status_code == 200:
            context['feedback_list'] = feedback_response.json()
        else:
            logger.error(f"Failed to fetch feedback from {feedback_url}: Status {feedback_response.status_code}")
            context['feedback_list'] = []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching feedback from {feedback_url}: {e}")
        context['feedback_list'] = []

    return render(request, 'admin_app/index.html', context)

@staff_member_required
def dynamic_api_overview(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_api'
    context['page_title'] = "Dynamic API Endpoints Overview"

    base_domain_host = f"{request.scheme}://{request.get_host()}"
    api_root_path = '/api/'
    admin_dynamic_api_root_path = '/admin/dynamic-api/' 

    managed_models = {
        'product': PetStoreProduct,
        'customer': Customer,
        'order': Order,
        'billing': Billing,
    }

    try:
        if apps.is_installed('APIs'): 
            if 'orderitem' in [m._meta.model_name for m in apps.get_app_config('APIs').get_models()]:
                 managed_models['orderitem'] = apps.get_model('APIs', 'OrderItem')
            else:
                 logger.warning("OrderItem model not found in 'APIs' app.")
        else:
            logger.warning("APIs app is not installed, skipping OrderItem model.")
    except LookupError as e:
        logger.error(f"Error looking up OrderItem model: {e}")
    available_routes = [
        {
            "name": name,
            "url": f"{base_domain_host}{admin_dynamic_api_root_path}{name}/"
        }
        for name, model_cls in managed_models.items() if model_cls is not None
    ]

    custom_apis = [
        {"name": "categories", "url": f"{base_domain_host}{api_root_path}admin/categories/"},
        {"name": "orders", "url": f"{base_domain_host}{api_root_path}admin/orders/"},
        {"name": "customers", "url": f"{base_domain_host}{api_root_path}register-customers/"},
        {"name": "products", "url": f"{base_domain_host}{api_root_path}admin/products/"},
        {"name": "register-customers", "url": f"{base_domain_host}{api_root_path}register-customers/"}, 
        {"name": "feedback", "url": f"{base_domain_host}{api_root_path}feedback/"},
        {"name": "posts", "url": f"{base_domain_host}{api_root_path}posts/"},
        {"name": "admin-orders", "url": f"{base_domain_host}{api_root_path}admin/orders/"}, 
    ]

    context['routes'] = available_routes + custom_apis
    return render(request, 'admin_app/dyn_api/index.html', context)

@staff_member_required
def dynamic_dt_overview(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_dt' 

    main_item = request.GET.get('main_item', 'product').lower()
    print("Main item is:", main_item) 

    category = request.GET.get('category', 'All') 
    search_query = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    page_items_count = request.session.get(f'page_items_{main_item}', 10)

    api_path = API_ENDPOINTS.get(main_item)
    if not api_path:
        return HttpResponse("API endpoint not found for selected item.", status=404)

    params = {'page': page, 'page_size': page_items_count}
    if search_query:
        params['search'] = search_query

    if main_item == 'product' and category != 'All':
        try:
            category_obj = Category.objects.get(name__iexact=category)
            params['category'] = category_obj.id
        except Category.DoesNotExist:
            pass

    if main_item == 'order':
        status_filter = request.GET.get('status', 'All')
        context['set_status'] = status_filter 
        if status_filter != 'All':
            params['status'] = status_filter

    filter_data = request.session.get(f'filters_{main_item}', [])
    for f_data in filter_data:
        key = f_data.get('key')
        value = f_data.get('value')
        if key and value:
            params[key] = value
    base_domain_host = f"{request.scheme}://{request.get_host()}"
    api_root = 'api/'

    api_url = f"{base_domain_host}/{api_root}{api_path}"
    print("Full API URL constructed:", api_url) 

    items = []
    total_count = 0
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status() 
        api_data = response.json()
        if isinstance(api_data, list):
            items = api_data
            total_count = len(api_data)
        else:
            items = api_data.get('results', [])
            total_count = api_data.get('count', 0)

    except requests.exceptions.RequestException as e:
        logger.error(f"API Error fetching {main_item} data from {api_url} with params {params}: {e}")
        return HttpResponse(f"Error fetching data from API: {e}", status=500)
    class ApiPaginatorPage:
        def __init__(self, data, count, page_num, page_size):
            self.object_list = data 
            self.number = int(page_num)
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

        def start_index(self):
            if self.paginator.count == 0:
                return 0
            return (self.number - 1) * page_items_count + 1

        def end_index(self):
            return min(self.number * page_items_count, self.paginator.count)

        def __iter__(self):
            return iter(self.object_list)

    paginated_items = ApiPaginatorPage(items, total_count, page, page_items_count)
    page_title = f"{main_item.replace('_', ' ').capitalize()} Management"
    if main_item == 'product' and category != 'All':
        try:
            category_name = Category.objects.filter(id=params.get('category')).first()
            if category_name: 
                page_title = f"{category_name.name} Products Management"
        except Exception as e: 
            logger.error(f"Error getting category name for title: {e}")
            pass
    context['page_title'] = page_title

    context['set_main_item'] = main_item
    context['set_category'] = category
    context['search_query'] = search_query 

    model = None
    if main_item.lower() == 'product':
        model = PetStoreProduct
    elif main_item.lower() == 'category':
        model = Category
    elif main_item.lower() == 'order':
        model = Order
    elif main_item.lower() == 'orderitem':
        try:
            model = OrderItem 
        except NameError: 
            try:
                model = apps.get_model('APIs', 'OrderItem')
            except LookupError:
                logger.error(f"OrderItem model not found for app 'APIs'.")
                return HttpResponse(f"Model 'OrderItem' not found.", status=404)
    elif main_item.lower() == 'customer':
        model = Customer
    elif main_item.lower() == 'billing': 
        model = Billing
    else:
        try:
            model = apps.get_model('Admin', main_item.capitalize())
        except LookupError:
            try: 
                model = apps.get_model('PetStore', main_item.capitalize())
            except LookupError:
                logger.error(f"Model '{main_item.capitalize()}' not found in 'Admin' or 'PetStore' apps.")
                return HttpResponse(f"Model '{main_item.capitalize()}' not found.", status=404)

    if not model:
        return HttpResponse("Could not determine model for field information.", status=500)
    model_info = get_model_fields(model)
    context.update(model_info) 

    context['items'] = paginated_items
    context['db_filters'] = model_info['db_field_names'] 
    context['filter_instance'] = filter_data 
    context['page_items'] = page_items_count 
    context['model_name'] = main_item 
    context['set_page'] = int(page) 

    print(f"Items for {main_item}:", [item.get('id') for item in paginated_items.object_list]) 
    return render(request, 'admin_app/dyn_dt/model.html', context)

@staff_member_required
def create_item(request, model_name):
    if request.method == 'POST':
        api_path = API_ENDPOINTS.get(model_name)
        if not api_path:
            return HttpResponse("Invalid model name.", status=400)
        base_domain_host = f"{request.scheme}://{request.get_host()}"
        api_root = 'api/'
        api_url = f"{base_domain_host}/{api_root}{api_path}"

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
                    return HttpResponse("Invalid category ID provided. Must be a number.", status=400)
            else:
                return HttpResponse("Category is required for new products. Please select one.", status=400)

            data['is_active'] = 'is_active' in request.POST

            if 'image' in request.FILES:
                files['image'] = request.FILES['image']

        elif model_name == 'customer':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            if not username or not email or not password or not confirm_password:
                encoded_error = quote("Username, Email, Password, and Confirm Password are required.")
                return redirect(reverse('Admin:dynamic_dt_overview') +
                                f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")

            if password != confirm_password:
                encoded_error = quote("Passwords do not match.")
                return redirect(reverse('Admin:dynamic_dt_overview') +
                                f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")

            data['username'] = username
            data['email'] = email
            data['password'] = password
            data['password2'] = confirm_password
            data['first_name'] = request.POST.get('first_name', '')
            data['last_name'] = request.POST.get('last_name', '')
            data['phone_number'] = request.POST.get('phone_number', '')
            data['address'] = request.POST.get('address', '')

        logger.info(f"Data being sent to API for {model_name} (Create): {data}")
        logger.info(f"Files being sent to API for {model_name} (Create): {files}")

        try:
            response = requests.post(api_url, data=data, files=files if files else None)
            response.raise_for_status()

            return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}&create_success=true")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating item: {e}")
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
                    logger.error(f"Error processing API JSON response: {ex}")
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
        api_path = API_ENDPOINTS.get(model_name)
        if not api_path:
            return HttpResponse("Invalid model name.", status=400)

        base_domain_host = f"{request.scheme}://{request.get_host()}"
        api_root = 'api/'
        api_url = f"{base_domain_host}/{api_root}{api_path}{item_id}/"

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

        logger.info(f"Data being sent to API for {model_name} (Update): {data}")
        logger.info(f"Files being sent to API for {model_name} (Update): {files}")

        try:
            response = requests.patch(api_url, data=data, files=files if files else None)

            response.raise_for_status()
            return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}&update_success=true")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating item: {e}")
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
                    logger.error(f"Error processing API JSON response: {ex}")
                    error_message_from_api = f"API responded with an unreadable error: {e.response.text}"
            else:
                error_message_from_api = f"Request failed before API could respond: {str(e)}"
            
            encoded_error = quote(error_message_from_api)
            return redirect(reverse('Admin:dynamic_dt_overview') +
                            f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")

    else:
        return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}")
    

def delete_item(request, model_name, item_id):
    api_path = API_ENDPOINTS.get(model_name)
    if not api_path:
        return HttpResponse("Invalid model name.", status=400)

    base_domain_host = f"{request.scheme}://{request.get_host()}"
    api_root = 'api/'
    api_url = f"{base_domain_host}/{api_root}{api_path}{item_id}/"

    if request.method == 'POST':
        try:
            response = requests.delete(api_url)
            response.raise_for_status() 
            return redirect(reverse('Admin:dynamic_dt_overview') +
                            f"?main_item={model_name}&delete_success=true")

        except requests.exceptions.RequestException as e:
            logger.error(f"API Error deleting {model_name} (ID: {item_id}) from {api_url}: {e}")
            error_message_from_api = "An unknown error occurred during item deletion."

            if hasattr(e, 'response') and e.response is not None:
                try:
                    api_error_details = e.response.json()
                    if isinstance(api_error_details, dict) and 'detail' in api_error_details:
                        error_message_from_api = api_error_details['detail']
                    else:
                        error_message_from_api = str(api_error_details)
                except json.JSONDecodeError:
                    error_message_from_api = e.response.text
                except Exception as ex:
                    logger.error(f"Error processing API JSON response for deletion: {ex}")
                    error_message_from_api = f"API responded with an unreadable error: {e.response.text}"
            else:
                error_message_from_api = f"Request failed before API could respond: {str(e)}"

            encoded_error = quote(error_message_from_api)
            return redirect(reverse('Admin:dynamic_dt_overview') +
                            f"?main_item={model_name}&action_error=true&error_msg={encoded_error}")
    else:
        return HttpResponse("Invalid request method. Only POST is allowed for deletion.", status=405)


@staff_member_required
def export_csv_view(request, link):
    model_name = link.lower()

    api_path = API_ENDPOINTS.get(model_name)
    if not api_path:
        return HttpResponse("API endpoint not found for export operation.", status=404)

    base_domain_host = f"{request.scheme}://{request.get_host()}"
    api_root = 'api/'
    api_url = f"{base_domain_host}/{api_root}{api_path}"

    search_query = request.GET.get('search', '')
    params = {}
    if search_query:
        params['search'] = search_query

    items_data = []
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        api_data = response.json()

        if isinstance(api_data, list):
            items_data = api_data
        elif isinstance(api_data, dict) and 'results' in api_data:
            items_data = api_data['results']
        else:
            if isinstance(api_data, dict):
                items_data = [api_data]
            else:
                logger.warning(f"Unexpected API response type for {model_name}: {type(api_data)}. Expected list or dict.")
                items_data = []

    except requests.exceptions.RequestException as e:
        logger.error(f"API Error fetching {model_name} data for CSV export from {api_url}: {e}")
        return HttpResponse(f"Error fetching data for export: {e}", status=500)

    model = None
    if model_name == 'product':
        model = PetStoreProduct
    elif model_name == 'category':
        model = Category
    elif model_name == 'orderitem':
        try:
            model = apps.get_model('PetStore', 'OrderItem')
        except LookupError:
            try:
                model = apps.get_model('APIs', 'OrderItem')
            except LookupError:
                logger.error(f"OrderItem model not found in PetStore or APIs app.")
                return HttpResponse("Model 'OrderItem' not found for CSV field names.", status=500)
    else:
        try:
            model = apps.get_model('Admin', model_name.capitalize())
        except LookupError:
            try:
                model = apps.get_model('PetStore', model_name.capitalize()) 
            except LookupError:
                logger.error(f"Model '{model_name.capitalize()}' not found in 'Admin' or 'PetStore' apps for CSV export.")
                return HttpResponse("Model not found for CSV field names.", status=500)

    if not model:
        return HttpResponse("Could not determine model for CSV field names.", status=500)

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

    product_sales = (
        PetStoreProduct.objects
        .annotate(total_quantity=Sum('orderitem__quantity'))
        .values('name', 'original_price', 'total_quantity')
        .order_by('-total_quantity')  
    )

    products_data = []
    for product in product_sales:
        products_data.append({
            'name': product['name'],
            'original_price': float(product['original_price']),
            'total_quantity': product['total_quantity'] or 0
        })

    context['products_for_chart'] = json.dumps(products_data)

    sales_data = [
        {'date': '2024-01-01', 'amount': 1500},
        {'date': '2024-02-01', 'amount': 2200},
        {'date': '2024-03-01', 'amount': 1800},
        {'date': '2024-04-01', 'amount': 2500},
    ]
    context['sales_data_json'] = json.dumps(sales_data)

    now = timezone.now() # Get the current timezone-aware datetime

    # --- Daily Product Data (Last 7 days, including today) ---
    # Filter products created within the last 7 days (inclusive of today)
    daily_product_data_raw = PetStoreProduct.objects.filter(
        created_at__date__gte=(now - timedelta(days=6)).date() # Compare dates only
    ).annotate(
        # Truncate created_at to the start of the day
        day=TruncDay('created_at')
    ).values('day').annotate(
        # Count products for each day
        value=Count('id')
    ).order_by('day') # Order by day for correct sequence

    # Convert raw query results into a dictionary for easy lookup
    daily_data_map = {item['day'].date(): item['value'] for item in daily_product_data_raw}

    daily_product_data = []
    # Loop through the last 7 days to ensure all days are represented, even if no data
    for i in range(7):
        date_to_check = (now - timedelta(days=6 - i)).date() # Calculate date for current iteration
        daily_product_data.append({
            'label': date_to_check.strftime('%b %d'), # e.g., 'Jul 20'
            'value': daily_data_map.get(date_to_check, 0) # Get actual count or 0 if no products on that day
        })


    # --- Weekly Product Data (Last 4 weeks, including current partial week) ---
    # Determine the start of the current week (Monday by default for TruncWeek)
    # Go back 3 full weeks from the start of the current week
    start_of_period_week = now - timedelta(weeks=3)

    weekly_product_data_raw = PetStoreProduct.objects.filter(
        created_at__gte=start_of_period_week
    ).annotate(
        # Truncate created_at to the start of the week (Monday)
        week=TruncWeek('created_at')
    ).values('week').annotate(
        value=Count('id')
    ).order_by('week')

    # Map week start dates to their values
    weekly_data_map = {item['week'].date(): item['value'] for item in weekly_product_data_raw}

    weekly_product_data = []
    for i in range(4):
        # Calculate the start date of each of the last 4 weeks (Mon, Tue, etc.)
        # Ensure consistency with TruncWeek (which starts on Monday by default in Django)
        # Find the Monday of the current week
        monday_of_this_week = now.date() - timedelta(days=now.weekday())
        week_start_date = monday_of_this_week - timedelta(weeks=(3 - i))
        
        weekly_product_data.append({
            'label': f'Week {i+1}', # Or more descriptive: f'{week_start_date.strftime("%b %d")}'
            'value': weekly_data_map.get(week_start_date, 0)
        })


    # --- Monthly Product Data (Last 6 months, including current partial month) ---
    # Go back 5 full months from the 1st day of the current month
    start_of_period_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30 * 5) # Approximate
    
    monthly_product_data_raw = PetStoreProduct.objects.filter(
        created_at__gte=start_of_period_month
    ).annotate(
        # Truncate created_at to the start of the month
        month=TruncMonth('created_at')
    ).values('month').annotate(
        value=Count('id')
    ).order_by('month')

    # Map month start dates to their values
    monthly_data_map = {item['month'].date(): item['value'] for item in monthly_product_data_raw}

    monthly_product_data = []
    for i in range(6):
        # Calculate the first day of each of the last 6 months
        date = now.replace(day=1) # Start with first day of current month
        # Subtract months by going to the last day of the previous month, then the first day of that month
        for _ in range(5 - i): # For the previous 5 months (0-indexed loop covers 6 months total)
            date = (date - timedelta(days=1)).replace(day=1) 

        monthly_product_data.append({
            'label': date.strftime('%b'), # e.g., 'Jul'
            'value': monthly_data_map.get(date.date(), 0)
        })


    # --- Yearly Product Data (Last 3 years, including current partial year) ---
    # Filter products from the beginning of 2 years ago up to now
    start_of_period_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=365 * 2)

    yearly_product_data_raw = PetStoreProduct.objects.filter(
        created_at__gte=start_of_period_year
    ).annotate(
        # Truncate created_at to the start of the year
        year=TruncYear('created_at')
    ).values('year').annotate(
        value=Count('id')
    ).order_by('year')

    # Map year start dates to their values
    yearly_data_map = {item['year'].date().year: item['value'] for item in yearly_product_data_raw}

    yearly_product_data = []
    for i in range(3):
        year_to_check = now.year - (2 - i) # Current year, last year, two years ago
        yearly_product_data.append({
            'label': str(year_to_check),
            'value': yearly_data_map.get(year_to_check, 0)
        })


    # Dump the data to JSON strings for use in JavaScript in the template
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
    users = User.objects.filter(is_staff=False).order_by('date_joined')
    context['users'] = users
    return render(request, 'admin_app/users/index.html', context)

@staff_member_required
def user_create_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        is_staff = request.POST.get('is_staff') == 'True' # Checkbox value is 'True' if checked

        if not username or not password:
            encoded_error = quote("Username and Password are required.")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")

        if User.objects.filter(username=username).exists():
            encoded_error = quote("Username already exists.")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")

        if email and User.objects.filter(email=email).exists():
            encoded_error = quote("Email already exists.")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")

        try:
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=is_staff,
                is_active=True # New users are active by default
            )
            return redirect(reverse('Admin:user_management') + "?create_success=true")
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            encoded_error = quote(f"Failed to create user: {e}")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")
    else:
        # If accessed via GET, redirect to the user list page
        return redirect(reverse('Admin:user_management'))


@staff_member_required
def user_update_view(request, pk):
    user_instance = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        is_staff = request.POST.get('is_staff') == 'True'
        new_password = request.POST.get('password') # Optional password change

        # Basic validation for username and email uniqueness (excluding current user)
        if User.objects.filter(username=username).exclude(pk=pk).exists():
            encoded_error = quote("Username already exists.")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")
        if email and User.objects.filter(email=email).exclude(pk=pk).exists():
            encoded_error = quote("Email already exists.")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")

        try:
            user_instance.username = username
            user_instance.email = email
            user_instance.is_staff = is_staff
            # Only update password if a new one is provided
            if new_password:
                user_instance.set_password(new_password) # Use set_password to hash
            user_instance.save()
            return redirect(reverse('Admin:user_management') + "?update_success=true")
        except Exception as e:
            logger.error(f"Error updating user {pk}: {e}")
            encoded_error = quote(f"Failed to update user: {e}")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")
    else:
        # For GET requests, you might want to render a specific edit form
        # For simplicity, we redirect to the list page, which will not show the modal directly
        # A more complex solution would involve passing user_instance data to the context
        # and using JS to open the modal on page load if 'edit_user_id' is in GET params.
        return redirect(reverse('Admin:user_management'))


@staff_member_required
def user_delete_view(request, pk):
    if request.method == 'POST': # HTML forms send POST for delete actions
        user_instance = get_object_or_404(User, pk=pk)

        # Prevent deleting the superuser or currently logged-in user (optional safety)
        if user_instance.is_superuser and not request.user.is_superuser:
            encoded_error = quote("Only a superuser can delete another superuser.")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")
        if user_instance == request.user:
            encoded_error = quote("You cannot delete your own account.")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")

        try:
            user_instance.delete()
            return redirect(reverse('Admin:user_management') + "?delete_success=true")
        except Exception as e:
            logger.error(f"Error deleting user {pk}: {e}")
            encoded_error = quote(f"Failed to delete user: {e}")
            return redirect(reverse('Admin:user_management') + f"?action_error=true&error_msg={encoded_error}")
    else:
        return HttpResponse("Invalid request method. Only POST is allowed for deletion.", status=405)