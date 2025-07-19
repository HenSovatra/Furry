from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.apps import apps
from django.db.models import ForeignKey, ManyToManyField, DateTimeField, IntegerField, EmailField, CharField, TextField, DecimalField, BooleanField
from django.urls import reverse
import json
import csv
from django.db import models
from io import StringIO
from .models import Product, Customer, Order, Billing
from django.http import JsonResponse
from django.contrib.auth import get_user_model

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
    return context

def dashboard_view(request):
    context = get_base_context(request)
    context['segment'] = 'dashboard'
    context['page_title'] = "Admin Dashboard"

    total_products = Product.objects.count()
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

def dyn_dt_index(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_dt'
    context['page_title'] = "Dynamic DataTables Overview"

    managed_models = ['Product', 'Customer', 'Order', 'OrderItem', 'Billing']
    routes = []
    for model_name in managed_models:
        try:
            apps.get_model('Admin', model_name)
            routes.append(model_name.lower())
        except LookupError:
            print(f"Model {model_name} not found in Admin app.")
            pass

    context['routes'] = routes
    return render(request, 'admin_app/dyn_dt/index.html', context) # Adjusted this path

def model_dt_view(request, model_name):
    context = get_base_context(request, model_name)
    context['segment'] = 'dynamic_dt'

    try:
        model = apps.get_model('Admin', model_name.capitalize())
    except LookupError:
        return HttpResponse("Model not found.", status=404)

    model_info = get_model_fields(model)
    context.update(model_info)
    context['page_title'] = f'{model_name.capitalize()} Management'

    items = model.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        q_objects = models.Q()
        for field in model_info['db_field_names']:
            if field in model_info['text_fields'] or field in model_info['email_fields']:
                q_objects |= models.Q(**{f"{field}__icontains": search_query})
        if q_objects:
            items = items.filter(q_objects)

    filter_data = request.session.get(f'filters_{model_name}', [])
    context['filter_instance'] = filter_data
    
    for f_data in filter_data:
        key = f_data.get('key')
        value = f_data.get('value')
        if key and value:
            try:
                items = items.filter(**{f"{key}__icontains": value})
            except Exception as e:
                print(f"Filter error: {e}")

    page = request.GET.get('page', 1)
    page_items_count = request.session.get(f'page_items_{model_name}', 10)
    context['page_items'] = page_items_count

    paginator = Paginator(items, page_items_count)
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)
    
    context['items'] = items
    
    context['db_filters'] = model_info['db_field_names']

    return render(request, 'admin_app/dyn_dt/model.html', context)

def create_view(request, link):
    model_name = link.capitalize()
    model = apps.get_model('Admin', model_name)

    if request.method == 'POST':
        data = request.POST.copy()
        
        for fk_key, fk_queryset in get_model_fields(model)['fk_fields'].items():
            if fk_key in data:
                try:
                    fk_id = data.pop(fk_key)[0]
                    fk_model = fk_queryset.model
                    data[fk_key] = fk_model.objects.get(id=fk_id)
                except (IndexError, fk_model.DoesNotExist) as e:
                    print(f"FK error for {fk_key}: {e}")
                    return HttpResponse(f"Error creating item: Invalid FK for {fk_key}", status=400)

        if 'csrfmiddlewaretoken' in data:
            del data['csrfmiddlewaretoken']

        try:
            cleaned_data = {}
            for field_name, value in data.items():
                field = model._meta.get_field(field_name)
                if isinstance(field, IntegerField):
                    cleaned_data[field_name] = int(value) if value else None
                elif isinstance(field, DecimalField):
                    cleaned_data[field_name] = float(value) if value else None
                elif isinstance(field, DateTimeField):
                    cleaned_data[field_name] = value
                elif isinstance(field, BooleanField):
                    cleaned_data[field_name] = (value.lower() == 'on' or value.lower() == 'true')
                else:
                    cleaned_data[field_name] = value

            model.objects.create(**cleaned_data)
            return redirect(reverse('Admin:model_dt', kwargs={'model_name': link}))
        except Exception as e:
            print(f"Error creating {model_name}: {e}")
            return HttpResponse(f"Error creating item: {e}", status=400)
    return HttpResponse("Invalid request method for create.", status=405)


def update_view(request, link, item_id):
    model_name = link.capitalize()
    model = apps.get_model('Admin', model_name)
    item = get_object_or_404(model, id=item_id)

    if request.method == 'POST':
        data = request.POST.copy()

        for fk_key, fk_queryset in get_model_fields(model)['fk_fields'].items():
            if fk_key in data:
                try:
                    fk_id = data.pop(fk_key)[0]
                    fk_model = fk_queryset.model
                    setattr(item, fk_key, fk_model.objects.get(id=fk_id))
                except (IndexError, fk_model.DoesNotExist) as e:
                    print(f"FK error for {fk_key} during update: {e}")
                    return HttpResponse(f"Error updating item: Invalid FK for {fk_key}", status=400)

        if 'csrfmiddlewaretoken' in data:
            del data['csrfmiddlewaretoken']

        try:
            for field_name, value in data.items():
                field = model._meta.get_field(field_name)
                if isinstance(field, IntegerField):
                    setattr(item, field_name, int(value) if value else None)
                elif isinstance(field, DecimalField):
                    setattr(item, field_name, float(value) if value else None)
                elif isinstance(field, DateTimeField):
                    setattr(item, field_name, value)
                elif isinstance(field, BooleanField):
                    setattr(item, field_name, (value.lower() == 'on' or value.lower() == 'true'))
                else:
                    setattr(item, field_name, value)
            item.save()
            return redirect(reverse('Admin:model_dt', kwargs={'model_name': link}))
        except Exception as e:
            print(f"Error updating {model_name}: {e}")
            return HttpResponse(f"Error updating item: {e}", status=400)
    return HttpResponse("Invalid request method for update.", status=405)


def delete_view(request, link, item_id):
    model_name = link.capitalize()
    model = apps.get_model('Admin', model_name)
    item = get_object_or_404(model, id=item_id)
    if request.method == 'GET':
        item.delete()
        return redirect(reverse('Admin:model_dt', kwargs={'model_name': link}))
    return HttpResponse("Invalid request method for delete.", status=405)

def export_csv_view(request, link):
    model_name = link.capitalize()
    try:
        model = apps.get_model('Admin', model_name)
    except LookupError:
        return HttpResponse("Model not found.", status=404)

    items = model.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        model_info = get_model_fields(model)
        q_objects = models.Q()
        for field in model_info['db_field_names']:
            if field in model_info['text_fields'] or field in model_info['email_fields']:
                q_objects |= models.Q(**{f"{field}__icontains": search_query})
        if q_objects:
            items = items.filter(q_objects)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{model_name}_data.csv"'

    writer = csv.writer(response)
    field_names = [field.name for field in model._meta.fields if not field.auto_created]
    writer.writerow(field_names)

    for obj in items:
        row = []
        for field_name in field_names:
            value = getattr(obj, field_name)
            if isinstance(value, models.Model):
                row.append(str(value))
            else:
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
        return redirect(reverse('Admin:model_dt', kwargs={'model_name': link}))
    return HttpResponse("Invalid request method for create filter.", status=405)

def delete_filter_view(request, link, filter_id):
    filter_id = int(filter_id)
    session_key = f'filters_{link}'
    filter_data = request.session.get(session_key, [])
    
    request.session[session_key] = [f for f in filter_data if f.get('id') != filter_id]
    request.session.modified = True
    return redirect(reverse('Admin:model_dt', kwargs={'model_name': link}))

def dyn_api_index(request):
    context = get_base_context(request)
    context['segment'] = 'dynamic_api'
    context['page_title'] = "Dynamic API Endpoints"

    managed_models = ['Product', 'Customer', 'Order']
    routes = [model.lower() for model in managed_models]
    context['routes'] = routes
    return render(request, 'admin_app/dyn_api/index.html', context)

def model_api_view(request, model_name):
    try:
        model = apps.get_model('Admin', model_name.capitalize())
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

def charts_index(request):
    context = get_base_context(request)
    context['segment'] = 'charts'
    context['page_title'] = "Sales & Product Charts"

    products_for_chart = Product.objects.all().values('name', 'price')
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

def billing_view(request):
    context = get_base_context(request)
    context['segment'] = 'billing'
    context['page_title'] = "Billing Management"

    invoices = Billing.objects.all().select_related('customer').order_by('-issue_date')
    context['invoices'] = invoices
    return render(request, 'admin_app/billing/index.html', context)

def user_management_view(request):
    context = get_base_context(request)
    context['segment'] = 'user_management'
    context['page_title'] = "User Account Management"

    User = get_user_model()
    users = User.objects.all().order_by('date_joined')
    context['users'] = users
    return render(request, 'admin_app/users/index.html', context)
