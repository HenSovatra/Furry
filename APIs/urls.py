from django.urls import path
from . import views

app_name = 'APIs' 

urlpatterns = [
    path('products/', views.product_list, name='api-product-list'),
    path('products/<int:pk>/', views.product_detail, name='api-product-detail'),
    path('cart/add/', views.add_to_cart_api, name='api-add-to-cart'),
    path('cart/', views.cart_details, name='api-cart-details'),
    path('order/<int:order_id>/', views.order_detail, name='api-order-detail'),
    path('cart/update-quantity/', views.update_cart_item_quantity_api, name='api-update-cart-quantity'),
    path('cart/remove/', views.remove_from_cart_api, name='api-remove-from-cart'),
    path('placeorder/', views.place_order_api, name='api-place-order'),
]
