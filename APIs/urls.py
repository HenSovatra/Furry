from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter
from .views import RegisteredCustomerAPIView, get_feedback_api, FeedbackAPIView
from .views import PostViewSet
app_name = 'APIs' 

urlpatterns = [
    path('products/', views.product_list, name='api-product-list'),
    path('products/filter/', views.products_by_createdate, name='api-product-list-date'),
    path('products/<int:pk>/', views.product_detail, name='api-product-detail'),
    path('cart/add/', views.add_to_cart_api, name='api-add-to-cart'),
    path('cart/', views.cart_details, name='api-cart-details'),
    path('order/<int:order_id>/', views.order_detail, name='api-order-detail'),
    path('cart/update-quantity/', views.update_cart_item_quantity_api, name='api-update-cart-quantity'),
    path('cart/remove/', views.remove_from_cart_api, name='api-remove-from-cart'),
    path('placeorder/', views.place_order_api, name='api-place-order'),    
    path('register/', views.register_api, name='api-register'),
    path('login/', views.login_api, name='api-login'),
    path('logout/', views.logout_api, name='api-logout'),
    path('order-history/', views.order_history_api, name='order_history_api'),
    path('register-customers/', RegisteredCustomerAPIView.as_view(), name='register-customers'),
    path('products-category/<int:category_id>/', views.products_by_category_api, name='api_products_by_category'),
    path('feedback/submit/', FeedbackAPIView.as_view(), name='feedback_submit_api'), # For POST
    path('feedback/', get_feedback_api, name='api_get_feedback'), # For GET (to retrieve all feedback)

]


# New Admin API Router and URLs
router = DefaultRouter()
router.register(r'admin/products', views.ProductAdminViewSet)
router.register(r'admin/customers', views.CustomerViewSet)
router.register(r'admin/orders', views.OrderAdminViewSet)
router.register(r'admin/billings', views.BillingViewSet)
router.register(r'admin/categories', views.CategoryViewSet)
router.register(r'posts', PostViewSet)
# Append the Admin API URLs to the existing urlpatterns
urlpatterns += router.urls