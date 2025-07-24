# myproject/blog/urls.py

from django.urls import path
from . import views # Import views from the current app
from django.shortcuts import render
from .views import FeedbackView # Import the FeedbackView class
app_name = 'PetStore' 

urlpatterns = [
    path('', views.HomeView, name='home'),
    path('category/', views.CategoryView, name='category'),
    path('history', views.HistoryView, name='history'),
    path('blog/<int:pk>/', views.PostDetailView, name='blog_detail'), # Updated to use PostDetailView
    path('blog/', views.PostView, name='blog'),

    path('product/<int:pk>/', views.single_product_view, name='single_product'),
    path('product-quick-view/<int:pk>/', views.product_quick_view, name='product_quick_view'), 
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('get-cart-details/', views.get_cart_details, name='get_cart_details'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order-confirmation/', views.order_confirmation_view, name='order_confirmation'), # <--- ADD THIS
    path('order-confirmation/<int:order_id>/', views.order_confirmation_view, name='order_confirmation_with_id'), 
    path('register/', render, {'template_name': 'register.html'}, name='register_html'),
    path('login/', render, {'template_name': 'login.html'}, name='login_html'),# Optional: for specific order
    path('feedback/',  views.FeedbackView, name='feedback'),
]