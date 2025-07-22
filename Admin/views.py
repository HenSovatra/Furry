import requests # Added this import
import json
import datetime 
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.apps import apps
from django.db.models import ForeignKey, ManyToManyField, DateTimeField, IntegerField, EmailField, CharField, TextField, DecimalField, BooleanField, ImageField
from django.urls import reverse
import csv
from django.db import models
from io import StringIO
from .models import Product, Customer, Order, Billing
from PetStore.models import Product as PetStoreProduct, Category
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from urllib.parse import urlparse, parse_qs, quote 
# Define the base URL for your API
# IMPORTANT: In a real application, this should be configured in settings.py
# and retrieved using django.conf.settings (e.g., from django.conf import settings; BASE_API_URL = settings.API_BASE_URL)
BASE_API_URL = "http://127.0.0.1:8000/api/"

# Mapping for model names to API endpoints
API_ENDPOINTS = {
    'product': 'admin/products/',
    'customer': 'admin/customers/',
    'order': 'admin/orders/',
    'orderitem': 'admin/orderitems/', # Assuming an OrderItemViewSet is exposed
    'billing': 'admin/billings/',
    'category': 'admin/categories/', # Added category for completeness
}

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
                # For FK fields, we'll try to get their related model data for display
                # Note: This still fetches from DB, as API might return just IDs.
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
                read_only_fields.append(field_name) # Images are handled separately

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
    context['model_map'] = model_map_for_context # Pass model_map to context for template use
    return context

def dashboard(request):
    context = get_base_context(request)
    context['segment'] = 'dashboard'
    context['page_title'] = "Admin Dashboard"

    # For dashboard, you might want to call specific API endpoints for summary data
    # For now, keeping direct DB queries for simplicity as they are summaries
    total_products = PetStoreProduct.objects.count()
    total_customers = Customer.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(status='delivered').aggregate(models.Sum('total_amount'))['total_amount__sum'] or 0.00

    context.update({
        'total_products': total_products,
        'total_customers': total_customers,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
    })
    return render(request, 'admin_app/index.html', context)

def dynamic_api_overview(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_api'
    context['page_title'] = "Dynamic API Endpoints Overview"

    managed_models = {
        'product': PetStoreProduct,
        'customer': Customer,
        'order': Order,
        'orderitem': apps.get_model('Admin', 'OrderItem') if apps.is_installed('Admin') and 'OrderItem' in [m._meta.model_name for m in apps.get_app_config('Admin').get_models()] else None,
        'billing': Billing,
    }

    available_routes = [name for name, model_cls in managed_models.items() if model_cls is not None]

    context['routes'] = available_routes
    return render(request, 'admin_app/dyn_dt/index.html', context)

def dynamic_dt_overview(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_dt'
    set_main_item = request.GET.get('main_item', 'product')

    main_item = request.GET.get('main_item', 'product').lower()
    category = request.GET.get('category', 'All') # For product filtering
    search_query = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    page_items_count = request.session.get(f'page_items_{main_item}', 10)

    api_path = API_ENDPOINTS.get(main_item)

    if not api_path:
        return HttpResponse("API endpoint not found for selected item.", status=404)

    # Construct query parameters for the API call
    params = {'page': page, 'page_size': page_items_count}
    if search_query:
        params['search'] = search_query # Assuming API supports a 'search' parameter

    # Add category filter for products if applicable
    if main_item == 'product' and category != 'All':
        try:
            # Get the category ID to pass to the API
            category_obj = Category.objects.get(name__iexact=category)
            params['category'] = category_obj.id # Assuming API filters by category ID
        except Category.DoesNotExist:
            pass # No category filter if not found

    # For other specific filters from session, convert them to API query params
    filter_data = request.session.get(f'filters_{main_item}', [])
    for f_data in filter_data:
        key = f_data.get('key')
        value = f_data.get('value')
        if key and value:
            params[key] = value # Assuming API can handle direct key-value filters

    api_url = f"{BASE_API_URL}{api_path}"

    items = []
    total_count = 0
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        api_data = response.json()

        # Check if api_data is a list (direct return) or a dictionary (paginated DRF response)
        if isinstance(api_data, list):
            items = api_data
            total_count = len(api_data)
        else: # Assume it's a dictionary with 'results' and 'count' for paginated data
            items = api_data.get('results', [])
            total_count = api_data.get('count', 0)

    except requests.exceptions.RequestException as e:
        print(f"API Error fetching {main_item} data: {e}")
        return HttpResponse(f"Error fetching data from API: {e}", status=500)

    # Mimic Django Paginator page object for template compatibility
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
            return (self.number - 1) * self.paginator.num_pages + 1

        def end_index(self):
            return min(self.number * page_items_count, self.paginator.count)

    paginated_items = ApiPaginatorPage(items, total_count, page, page_items_count)

    page_title = f"{main_item.capitalize()} Management"
    if main_item == 'product' and category != 'All':
        category_name = Category.objects.filter(id=params.get('category')).first().name if 'category' in params else 'All'
        page_title = f"{category_name} Products Management"
    context['page_title'] = page_title

    context['set_main_item'] = main_item
    context['set_category'] = category

    # Model info for fields for rendering forms etc. still comes from local model definition
    # Ensure correct model is selected for retrieving field info
    model = apps.get_model('Admin', main_item.capitalize()) if main_item.lower() not in ['product', 'category'] else (PetStoreProduct if main_item.lower() == 'product' else Category)
    if main_item.lower() == 'orderitem' and not model: # special handling for OrderItem if not in Admin models
        model = apps.get_model('PetStore', 'OrderItem') # Assuming OrderItem is in PetStore

    if not model:
        # Fallback if model could not be determined, should not happen with proper mappings
        return HttpResponse("Could not determine model for field info.", status=500)

    model_info = get_model_fields(model)
    context.update(model_info)

    context['items'] = paginated_items
    context['db_filters'] = model_info['db_field_names']
    context['filter_instance'] = filter_data # Pass filters back to template
    context['page_items'] = page_items_count # Ensure this is passed correctly
    context['model_name'] = set_main_item
    return render(request, 'admin_app/dyn_dt/model.html', context)


def get_base_context(request):
    return {
        'segment': 'dynamic-datatables',
        'parent': 'tables',
        'set_main_item': request.GET.get('main_item', 'product'),
        'model_map': API_ENDPOINTS, # Used to show available models
    }

# Your existing dynamic_dt_overview function...

def create_item(request, model_name):
    """
    Handles creation of a new item by making a POST request to the external API.
    """
    if request.method == 'POST':
        api_path = API_ENDPOINTS.get(model_name)
        if not api_path:
            return HttpResponse("Invalid model name.", status=400)

        api_url = f"{BASE_API_URL}{api_path}" # POST to the list endpoint for creation

        # Initialize 'data' as an EMPTY dictionary for explicit population.
        # This prevents accidental inclusion of unexpected fields from request.POST.
        data = {}
        files = {} # This will hold the new image file if uploaded

        if model_name == 'product':
            # --- Populate 'data' with specific fields explicitly from request.POST ---
            # Basic Text/Number fields (assuming these are always present in the form)
            if 'name' in request.POST:
                data['name'] = request.POST['name']
            if 'description' in request.POST:
                data['description'] = request.POST['description']
            if 'original_price' in request.POST:
                data['original_price'] = request.POST['original_price']
            if 'discounted_price' in request.POST:
                data['discounted_price'] = request.POST['discounted_price']

            # Stock handling (convert to int)
            if 'stock' in request.POST:
                try:
                    data['stock'] = int(request.POST['stock'])
                except (ValueError, TypeError):
                    # Handle validation error for stock if needed, or let API handle it
                    pass

            # --- FIX FOR CATEGORY_ID IS HERE: Send as 'category_id' integer directly ---
            if 'category' in request.POST and request.POST['category']:
                try:
                    # The API expects 'category_id' as an integer, not a nested dictionary.
                    data['category_id'] = int(request.POST['category'])
                except (ValueError, TypeError):
                    # If category is not a valid integer, return an error
                    return HttpResponse("Invalid category ID provided. Must be a number.", status=400)
            else:
                # If category is required but not provided in the form, return an error.
                # This directly addresses the "This field is required." for category_id.
                return HttpResponse("Category is required for new products. Please select one.", status=400)

            # Is Active (boolean from checkbox)
            # Checkbox value is 'on' if checked, otherwise not in request.POST
            data['is_active'] = 'is_active' in request.POST

            # created_at: Typically handled by API with auto_now_add.
            # Remove `data['created_at'] = datetime.datetime.now().isoformat()` unless your API explicitly requires it for creation.
            # Your serializer has `read_only=True` for `created_at`, so the API should set it.

            # --- Image Handling for NEW items ---
            if 'image' in request.FILES:
                files['image'] = request.FILES['image']
                # The 'image' field is NOT added to 'data' when a file is in 'files'.
                # For new items, if no image is uploaded, the API will typically set it to null/default
                # because `ImageField(required=False, allow_null=True)` is defined in the serializer.
                # So, no 'image: ""' is needed here.

        # --- Diagnostic Prints (Check these carefully after running!) ---
        print(f"Data being sent to API for {model_name} (Create): {data}")
        print(f"Files being sent to API for {model_name} (Create): {files}")

        try:
            # Send the POST request to your API for creation
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
        # This handles the initial GET request to display the add item form
        return redirect(reverse('Admin:dynamic_dt_overview') + f"?main_item={model_name}")


def update_item(request, model_name, item_id):
    """
    Handles updating an existing item by making a POST/PATCH request to the external API.
    """
    if request.method == 'POST':
        # --- DIAGNOSTIC PRINT: See raw request.POST content (Keep this for now!) ---
        print(f"RAW request.POST at start of update_item: {request.POST}")

        api_path = API_ENDPOINTS.get(model_name)
        if not api_path:
            return HttpResponse("Invalid model name.", status=400)

        api_url = f"{BASE_API_URL}{api_path}{item_id}/"

        # Initialize 'data' as an EMPTY dictionary for explicit population.
        data = {}
        files = {} # This will hold the NEW image file if uploaded

        if model_name == 'product':
            # --- Populate 'data' with specific fields explicitly from request.POST ---
            if 'name' in request.POST:
                data['name'] = request.POST['name']
            if 'description' in request.POST:
                data['description'] = request.POST['description']
            if 'original_price' in request.POST:
                data['original_price'] = request.POST['original_price']
            if 'discounted_price' in request.POST: # This line was fixed previously for syntax
                data['discounted_price'] = request.POST['discounted_price']

            if 'stock' in request.POST:
                try:
                    data['stock'] = int(request.POST['stock'])
                except (ValueError, TypeError):
                    pass # Or handle this error gracefully

            if 'category' in request.POST and request.POST['category']:
                try:
                    data['category_id'] = int(request.POST['category'])
                except (ValueError, TypeError):
                    pass # Or handle this error

            data['is_active'] = 'is_active' in request.POST # Checkbox value

            if 'created_at' in request.POST:
                data['created_at'] = request.POST['created_at']


            # --- SIMPLIFIED AND CORRECTED IMAGE HANDLING LOGIC FOR PRESERVATION ---
            # This is the most direct and reliable way to handle image preservation
            # when no new file is uploaded and there's no explicit "clear image" checkbox.
            if 'image' in request.FILES:
                # Case 1: A new image file was uploaded by the user.
                files['image'] = request.FILES['image']
                # The 'image' field is NOT added to 'data' in this case, as it's handled via 'files'.
            else:
                # Case 2: No new image was uploaded.
                # In this scenario, we assume the user intends to PRESERVE the existing image.
                # To achieve preservation with DRF's PATCH, we *must not* include the 'image' field
                # in the 'data' payload at all.
                # The `request.POST['image'] = ''` coming from the browser for an empty file input
                # is effectively ignored by this logic, preventing it from being passed to the API as a clear instruction.
                pass # By doing nothing here, the 'image' field is omitted, which preserves it.


        # --- Final Diagnostic Prints for the payload being sent (IMPORTANT to check this!) ---
        print(f"Data being sent to API for {model_name}: {data}")
        print(f"Files being sent to API for {model_name}: {files}")

        try:
            response = requests.patch(api_url, data=data, files=files if files else None)

            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
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


def delete_item(request, model_name, item_id):
    """
    Handles deletion of an item by making a DELETE request to the external API.
    """
    api_path = API_ENDPOINTS.get(model_name)
    if not api_path:
        return HttpResponse("Invalid model name.", status=400)

    # Construct the API URL for the specific item
    api_url = f"{BASE_API_URL}{api_path}{item_id}/"

    # --- Crucial Change: Handle DELETE request ---
    if request.method == 'DELETE':
        try:
            # Forward the DELETE request to your API
            response = requests.delete(api_url)
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

            # If the API returns a success status (e.g., 200 OK, 204 No Content)
            # Send a successful JSON response back to the frontend JavaScript
            return JsonResponse({'message': f'{model_name.title()} (ID: {item_id}) deleted successfully.'}, status=204) # 204 No Content is typical for successful DELETE

        except requests.exceptions.RequestException as e:
            # Log the error and the API's response content for debugging
            print(f"API Error deleting {model_name} (ID: {item_id}): {e}")
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                print(f"API Response Content: {e.response.text}") # This is vital for debugging API's 400s
                try:
                    # Try to parse API's error response as JSON if possible
                    api_error_details = e.response.json()
                    error_message = api_error_details # Use the detailed API error
                except json.JSONDecodeError:
                    error_message = e.response.text # Fallback to plain text if not JSON

            # Return a JSON error response with the appropriate status code
            return JsonResponse({'error': error_message}, status=e.response.status_code if hasattr(e, 'response') and e.response is not None else 500)
    else:
        # If any method other than DELETE is used, return 405 Method Not Allowed
        # This prevents accidental deletions via GET or other methods.
        return HttpResponse("Invalid request method.", status=405)


def export_csv_view(request, link):
    model_name = link.lower() # Use lower for API lookup

    api_path = API_ENDPOINTS.get(model_name)
    if not api_path:
        return HttpResponse("API endpoint not found for export operation.", status=404)

    api_url = f"{BASE_API_URL}{api_path}"

    # Get search query from request
    search_query = request.GET.get('search', '')
    params = {}
    if search_query:
        params['search'] = search_query

    # For export, fetch ALL items (or handle pagination appropriately if dataset is huge)
    # For simplicity, we'll try to fetch all items for CSV. DRF usually has a 'limit' parameter or paginator disabled.
    # We might need to adjust the API to allow fetching all items without pagination for export.
    # For now, let's assume the API returns all matching results with search.
    # If the API is paginated by default, you would need to iterate through pages.
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()
        api_data = response.json()

        # Check if api_data is a list or a paginated response
        items_data = api_data.get('results', api_data) # Adjust based on actual API response format

    except requests.exceptions.RequestException as e:
        print(f"API Error fetching {model_name} data for CSV export: {e}")
        return HttpResponse(f"Error fetching data for export: {e}", status=500)

    # Determine the local model class for field names
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
            # If FKs are returned as IDs, you might want to fetch their names for the CSV
            # This would require additional API calls or a more complex serializer in DRF.
            # For simplicity, just use the value as is.
            row.append(str(value))
        writer.writerow(row)
    return response


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

def model_api(request, model_name):
    # This function is now redundant as we are using DRF ViewSets
    # and the Admin views are clients of those ViewSets.
    # You can remove this function if it's not explicitly used elsewhere.
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

def charts(request):
    context = get_base_context(request)
    context['segment'] = 'charts'
    context['page_title'] = "Sales & Product Charts"

    # For charts, consider fetching data from specific API endpoints tailored for analytics
    products_for_chart = PetStoreProduct.objects.all().values('name', 'original_price')
    products_data = list(products_for_chart)
    products_json_string = json.dumps(products_data)
    context['products_for_chart'] = products_json_string

    sales_data = [
        {'date': '2024-01-01', 'amount': 1500},
        {'date': '2024-02-01', 'amount': 2200},
        {'date': '2024-03-01', 'amount': 1800},
        {'date': '2024-04-01', 'amount': 2500},
    ]
    context['sales_data_json'] = json.dumps(sales_data)

    return render(request, 'admin_app/charts/index.html', context)

def billing(request):
    context = get_base_context(request)
    context['segment'] = 'billing'
    context['page_title'] = "Billing Management"

    invoices = Billing.objects.all().select_related('customer').order_by('-issue_date')
    context['invoices'] = invoices
    return render(request, 'admin_app/billing/index.html', context)

def user_management(request):
    context = get_base_context(request)
    context['segment'] = 'user_management'
    context['page_title'] = "User Account Management"

    User = get_user_model()
    users = User.objects.all().order_by('date_joined')
    context['users'] = users
    return render(request, 'admin_app/users/index.html', context)