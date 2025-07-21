from django.urls import path
from . import views

app_name = 'Admin'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('dynamic-datatables/', views.dynamic_dt_overview, name='dynamic_dt_overview'),
    
    path('create/<str:model_name>/', views.create_item, name='create'),
    path('update/<str:model_name>/<int:item_id>/', views.update_item, name='update'),
    path('delete/<str:model_name>/<int:item_id>/', views.delete_item, name='delete'),

    path('dynamic-api-overview/', views.dynamic_api_overview, name='dynamic_api_overview'),
    path('charts/', views.charts, name='charts'),
    path('billing/', views.billing, name='billing'),
    path('user-management/', views.user_management, name='user_management'),

    path('create-hide-show-items/<str:link>/', views.create_hide_show_items_view, name='create-hide-show-items'),
    path('create-page-items/<str:link>/', views.create_page_items_view, name='create-page-items'),
    path('create-filter/<str:link>/', views.create_filter_view, name='create_filter'),
    path('delete-filter/<str:link>/<int:filter_id>/', views.delete_filter_view, name='delete_filter'),
    path('export-csv/<str:link>/', views.export_csv_view, name='export_csv'),
    
    path('dynamic-api/<str:model_name>/', views.model_api, name='model_api'),
]