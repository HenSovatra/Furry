# Furry/Admin/urls.py

from django.urls import path
from . import views

app_name = 'Admin'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    path('dynamic-tables/', views.dyn_dt_index, name='dynamic_dt_overview'),
    path('dynamic-tables/<str:model_name>/', views.model_dt_view, name='model_dt'),
    path('dynamic-tables/<str:link>/create/', views.create_view, name='create'),
    path('dynamic-tables/<str:link>/<int:item_id>/update/', views.update_view, name='update'),
    path('dynamic-tables/<str:link>/<int:item_id>/delete/', views.delete_view, name='delete'),
    path('create-hide-show-items/<str:link>/', views.create_hide_show_items_view, name='create-hide-show-items'),
    path('create-page-items/<str:link>/', views.create_page_items_view, name='create-page-items'),
    path('create-filter/<str:link>/', views.create_filter_view, name='create_filter'),
    path('delete-filter/<str:link>/<int:filter_id>/', views.delete_filter_view, name='delete_filter'),
    path('export-csv/<str:link>/', views.export_csv_view, name='export_csv'),

    path('dynamic-api/', views.dyn_api_index, name='dynamic_api_overview'),
    path('dynamic-api/<str:model_name>/', views.model_api_view, name='model_api'),

    path('charts/', views.charts_index, name='charts'),

    path('billing/', views.billing_view, name='billing'),

    path('user-management/', views.user_management_view, name='user_management'),

]