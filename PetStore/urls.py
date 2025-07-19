# myproject/blog/urls.py

from django.urls import path
from . import views # Import views from the current app

app_name = 'PetStore' 

urlpatterns = [
    path('', views.HomeView, name='home'),
    path('category/', views.CategoryView, name='category'),
    path('product/<int:pk>/', views.single_product_view, name='single_product'),
    path('product-quick-view/<int:pk>/', views.product_quick_view, name='product_quick_view'), 
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('get-cart-details/', views.get_cart_details, name='get_cart_details'),
]