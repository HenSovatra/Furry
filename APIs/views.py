from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from PetStore.models import Product , Category, Cart, CartItem, Order, OrderItem,Feedback,FeedbackImage
from Admin.models import Customer, Billing
from .serializers import *
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework import viewsets, filters 
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
import stripe
from rest_framework import filters
import logging
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.decorators import action
from django.views import View
from .serializers import RegisteredCustomerSerializer
from rest_framework.permissions import AllowAny
from PetStore.forms import FeedbackForm,FeedbackImageFormSet
from django.db.models import Prefetch
from django.db.models import Sum, F
from django.http import JsonResponse
from .decorators import track_api_usage
from rest_framework.permissions import AllowAny
from .authentication import QueryParamAccessTokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.decorators import api_view, authentication_classes
import json
from rest_framework import permissions
from django.db.models import Q

logger = logging.getLogger(__name__) 

stripe.api_key = settings.STRIPE_SECRET_KEY

def get_or_create_cart(request):
    """
    Retrieves or creates a cart based on user authentication status or session key.
    """
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user, defaults={'session_key': None})
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
        if created or not cart.session_key: 
            cart.session_key = session_key
            cart.save()
    return cart


@api_view(['GET'])
@authentication_classes([QueryParamAccessTokenAuthentication]) 
@track_api_usage
def product_list(request):
    products = Product.objects.filter(is_active=True).annotate(
        total_sold=Sum('orderitem__quantity')
    ).order_by(F('total_sold').desc(nulls_last=True)) 

    serializer = ProductSerializer(products, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def products_by_createdate(request):
        products = Product.objects.filter(is_active=True).order_by('-created_at')
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


@api_view(['GET'])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True) 
    serializer = ProductSerializer(product)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny]) 
@csrf_exempt 
def add_to_cart_api(request):
    cart = get_or_create_cart(request) 
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity', 1))

    product = get_object_or_404(Product, pk=product_id, is_active=True)

    if product.stock < quantity:
        return Response({'error': 'Not enough stock.'}, status=status.HTTP_400_BAD_REQUEST)

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()
    request.session['cart_total_items'] = cart.total_items 

    return Response({'success': True, 'message': 'Added to cart.', 'cart_total_items': cart.total_items})

@api_view(['GET'])
@permission_classes([AllowAny]) 
def cart_details(request):
    cart = get_or_create_cart(request)
    items = cart.items.all()
    serializer = CartItemSerializer(items, many=True)
    cart.update_totals()

    return Response({
        'cart_items': serializer.data,
        'total': cart.total_price,
        'total_items': cart.total_items
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if not request.user.is_staff and order.user != request.user:
        return Response({'error': 'You do not have permission to view this order.'}, status=status.HTTP_403_FORBIDDEN)
    serializer = OrderSerializer(order)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny]) 
@csrf_exempt 
def update_cart_item_quantity_api(request):
    try:
        product_id = request.data.get('product_id')
        new_quantity = request.data.get('quantity')

        if not product_id or not isinstance(new_quantity, int) or new_quantity < 0:
            return Response({'success': False, 'error': 'Invalid product ID or quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(request) 

        try:
            cart_item = cart.items.get(product__id=product_id)
        except CartItem.DoesNotExist:
            return Response({'success': False, 'error': 'Item not found in cart.'}, status=status.HTTP_404_NOT_FOUND)

        product = cart_item.product

        if new_quantity == 0:
            cart_item.delete()
            message = 'Item removed from cart.'
        else:
            if product.stock < new_quantity:
                return Response({'success': False, 'error': f'Only {product.stock} left in stock. Cannot update to {new_quantity}.'}, status=status.HTTP_400_BAD_REQUEST)

            cart_item.quantity = new_quantity
            cart_item.save()
            message = 'Cart quantity updated.'

        request.session['cart_total_items'] = cart.total_items 
        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Error updating cart quantity:")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny]) 
@csrf_exempt 
def remove_from_cart_api(request):
    try:
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'success': False, 'error': 'Product ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(request) 

        try:
            cart_item = cart.items.get(product__id=product_id)
            cart_item.delete()
            message = 'Item successfully removed from cart.'
        except CartItem.DoesNotExist:
            message = 'Item was not in cart (already removed or never existed).'
            return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

        request.session['cart_total_items'] = cart.total_items 

        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Error removing from cart:")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny]) 
@csrf_protect 
def place_order_api(request):
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        return Response({'error': 'Your cart is empty. Please add items before placing an order.'},
                        status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    payment_method_id = data.get('payment_method_id') 
    payment_intent_id = data.get('payment_intent_id') 

    email = data.get('email')
    if not request.user.is_authenticated and not email: 
        return Response({'error': 'Email is required for guest checkout.'}, status=status.HTTP_400_BAD_REQUEST)
    elif request.user.is_authenticated:
        email = request.user.email 
    required_fields = ['first_name', 'last_name', 'email', 'address_line_1', 'city', 'state', 'zip_code', 'country']
    for field in required_fields:
        if not data.get(field):
            return Response({'error': f'{field.replace("_", " ").title()} is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        final_total_amount = Decimal('0.00')
        for item in cart.items.all():
            product = item.product 
            if product.discounted_price is not None:
                product_price = product.discounted_price
            else:
                product_price = product.original_price
            if not isinstance(product_price, Decimal):
                product_price = Decimal(str(product_price)) 
            final_total_amount += product_price * item.quantity

        shipping_cost = Decimal('5.00') 
        final_total_amount += shipping_cost

        total_amount_cents = int(final_total_amount * 100) 

        if total_amount_cents <= 0:
            return Response({'error': 'Cart total must be greater than zero after all calculations.'}, status=status.HTTP_400_BAD_REQUEST)

    except Product.DoesNotExist:
        return Response({'error': 'One or more products in your cart could not be found or have an invalid price.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error calculating total amount in place_order_api:")
        return Response({'error': f'Failed to calculate order total: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        with transaction.atomic(): 
            order = None 
            if payment_intent_id:
                try:
                    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                    existing_order = Order.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
                    if existing_order:
                        logger.info(f"Duplicate call for PI {payment_intent_id}. Order {existing_order.id} already exists.")
                        my_return_url = f'{settings.BASE_URL}/order-confirmation/{existing_order.id}'
                        print(f"DEBUG: Returning existing order with redirect_url: {my_return_url}")
                        return Response({
                            'success': True,
                            'message': 'Order already processed successfully!',
                            'redirect_url': my_return_url
                        }, status=status.HTTP_200_OK)
                    if payment_intent.amount != total_amount_cents:
                        logger.warning(f"Amount mismatch for PI {payment_intent_id}. Expected {total_amount_cents}, got {payment_intent.amount}.")
                        return Response({'error': 'Payment amount mismatch. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)


                    if payment_intent.status == 'succeeded':
                        order_data = {
                            'total_amount': final_total_amount, 
                            'status': 'Processing', 
                            'payment_status': 'Paid',
                            'first_name': data.get('first_name'),
                            'last_name': data.get('last_name'),
                            'shipping_cost': shipping_cost,
                            'email': email,
                            'phone': data.get('phone', ''), 
                            'address_line_1': data.get('address_line_1'),
                            'address_line_2': data.get('address_line_2', ''),
                            'city': data.get('city'),
                            'state': data.get('state'),
                            'zip_code': data.get('zip_code'),
                            'country': data.get('country'),
                            'billing_first_name': data.get('billing_first_name', data.get('first_name')),
                            'billing_last_name': data.get('billing_last_name', data.get('last_name')),
                            'billing_email': data.get('billing_email', email),
                            'billing_phone': data.get('billing_phone', data.get('phone', '')),
                            'billing_address_line_1': data.get('billing_address_line_1', data.get('address_line_1')),
                            'billing_address_line_2': data.get('billing_address_line_2', data.get('address_line_2', '')),
                            'billing_city': data.get('billing_city', data.get('city')),
                            'billing_state': data.get('billing_state', data.get('state')),
                            'billing_zip_code': data.get('billing_zip_code', data.get('zip_code')),
                            'billing_country': data.get('billing_country', data.get('country')),
                            'stripe_payment_intent_id': payment_intent.id, 
                            'payment_method': data.get('paymentMethod'), 
                        }
                        if request.user.is_authenticated:
                            order_data['user'] = request.user
                        else:
                            if request.session.session_key:
                                order_data['session_key'] = request.session.session_key
                            else:
                                request.session.save() 
                                order_data['session_key'] = request.session.session_key

                        order = Order.objects.create(**order_data)

                        for item in cart.items.all():
                            product = item.product 
                            
                            price_to_store = product.discounted_price if product.discounted_price is not None else product.original_price

                            OrderItem.objects.create(
                                order=order,
                                product=product,
                                quantity=item.quantity,
                                price=price_to_store, 
                                total_price=item.quantity * price_to_store
                            )

                            if product.stock >= item.quantity:
                                product.stock -= item.quantity
                                product.save()
                                logger.info(f"Deducted {item.quantity} from product {product.name}. New stock: {product.stock}")
                            else:
                                logger.error(f"Insufficient stock for product {product.name} (ID: {product.id}) during order {order.id} creation. Expected {item.quantity}, but only {product.stock} available.")



                        cart.items.all().delete() 
                        if not cart.items.exists() and not request.user.is_authenticated:
                            cart.delete()

                        subject = 'Your PetStore Order Confirmation'
                        recipient_email = order.email
                        html_message = render_to_string('email/order_confirmation_email.html', {'order': order, 'user': order.user if order.user else None})
                        plain_message = f'Thank you for your order, {order.first_name}! Your order ID is {order.id}.'
                        send_mail(subject, plain_message, settings.DEFAULT_FROM_EMAIL, [recipient_email], html_message=html_message)

                        my_return_url = f'{settings.BASE_URL}/order-confirmation/{order.id}'
                        print(f"DEBUG: Order {order.id} placed successfully. Redirect URL: {my_return_url}")

                        return Response({
                            'success': True,
                            'message': 'Order placed successfully!',
                            'order_id': order.id,
                            'redirect_url': my_return_url
                        }, status=status.HTTP_200_OK)
                    else:
                        return Response({
                            'error': f'Payment not successful. Status: {payment_intent.status}. Please try again or use another payment method.',
                            'payment_intent_status': payment_intent.status
                        }, status=status.HTTP_400_BAD_REQUEST)

                except stripe.error.StripeError as e:
                    logger.exception(f"Stripe Error retrieving/confirming PaymentIntent {payment_intent_id}:")
                    return Response({'error': f'Payment processing failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.exception("An error occurred during payment intent verification and order creation:")
                    return Response({'error': f'An unexpected error occurred during order finalization: {str(e)}'},
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            elif payment_method_id:
                try:
                    intent = stripe.PaymentIntent.create(
                        amount=total_amount_cents,
                        currency='usd',
                        payment_method=payment_method_id,
                        confirm=True, 
                        confirmation_method='automatic', 
                        return_url=f'{settings.BASE_URL}/order-confirmation/', 
                        metadata={
                            'cart_id': str(cart.id), 
                            'customer_email': email,
                            'is_guest_checkout': 'true' if not request.user.is_authenticated else 'false',
                            'user_id': str(request.user.id) if request.user.is_authenticated else 'guest'
                        },
                        shipping={
                            'name': f"{data.get('first_name')} {data.get('last_name')}",
                            'address': {
                                'line1': data.get('address_line_1'),
                                'line2': data.get('address_line_2', ''),
                                'city': data.get('city'),
                                'state': data.get('state'),
                                'postal_code': data.get('zip_code'),
                                'country': data.get('country'),
                            },
                        },
                        description=f"Order for {email} from PetStore",
                    )
                    return Response({
                        'success': True, 
                        'client_secret': intent.client_secret,
                        'payment_intent_id': intent.id, 
                        'message': 'Payment Intent created successfully, awaiting client confirmation.'
                    }, status=status.HTTP_200_OK)

                except stripe.error.CardError as e:
                    logger.warning(f"Stripe Card Error during PaymentIntent creation: {e.user_message}")
                    return Response({'error': e.user_message or str(e)}, status=status.HTTP_400_BAD_REQUEST)
                except stripe.error.StripeError as e:
                    logger.exception("Stripe API error during PaymentIntent creation:")
                    return Response({'error': f'Payment processing failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logger.exception("An unexpected error occurred during PaymentIntent creation:")
                    return Response({'error': f'An unexpected error occurred: {str(e)}'},
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({'error': 'Payment method or intent ID missing. Cannot process order.'}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e: 
        logger.exception("Unhandled error in place_order_api:")
        return Response({'error': f'An unexpected error occurred: {str(e)}'},
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def register_api(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'success': True,
            'message': 'User registered successfully.',
            'username': user.username,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_protect
def login_api(request):
    print("DEBUG: Login API called with data:", request.data)  
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        redirect_url = ''
        message = ''
        if user.is_staff:
            redirect_url = '/my-admin/' 
            message = 'Login successful. Welcome to the dashboard!'
        else:
            redirect_url = '/' 
            message = 'Login successful. Welcome back!'

        return Response({
            'success': True,
            'message': message,
            'username': user.username,
            'token': token.key,
            'is_staff': user.is_staff, 
            'redirect_url': redirect_url, 
        }, status=status.HTTP_200_OK)
    else:
        return Response({'success': False, 'error': 'Invalid username or password.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_api(request):
    try:
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        logout(request)
        return Response({'success': True, 'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Logout failed:")
        return Response({'success': False, 'error': f'Logout failed: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_history_api(request):
    user = request.user

    orders = Order.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')

    serializer = OrderHistorySerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

class ProductAdminViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductAdminSerializer
    filterset_fields = ['category'] 
    search_fields = ['name', 'description'] 

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class OrderAdminViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderAdminSerializer
    filterset_fields = ['status'] 
    search_fields = ['id', 'billing_first_name', 'billing_email'] 

class BillingViewSet(viewsets.ModelViewSet):
    queryset = Billing.objects.all()
    serializer_class = BillingSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all().prefetch_related('order_items')


class RegisteredCustomerAPIView(generics.ListCreateAPIView):
    """
    API View to list all registered customers (GET) and register new ones (POST).
    """
    queryset = User.objects.filter(is_staff=False) 

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RegisterSerializer 
        return RegisteredCustomerSerializer 

    permission_classes = [AllowAny]


@api_view(['GET'])
def products_by_category_api(request, category_id):
    """
    API endpoint to get products by category ID.
    Handles both direct category products and products in its subcategories.
    """
    try:
        category = get_object_or_404(Category, id=category_id)
        products = Product.objects.filter(category=category, is_active=True)
        if category.subcategories.exists():
            for subcat in category.subcategories.filter(is_active=True):
                products = products | Product.objects.filter(category=subcat, is_active=True)

        product_data = []
        for product in products.distinct(): 
            price = 0
            image_url = request.build_absolute_uri(product.image.url) if product.image else ''
            if product.discounted_price is not None:
                price = product.discounted_price
            else:
                price = product.original_price
            product_data.append({
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': float(price), 
                'image': image_url, 
            })

        return Response(product_data)
    except Exception as e:
        print(f"Error fetching products by category {category_id}: {e}")
        return Response({'error': str(e)}, status=500)
    


class FeedbackAPIView(View):
    def post(self, request, *args, **kwargs):

        form = FeedbackForm(request.POST)
        formset = FeedbackImageFormSet(request.POST, request.FILES, prefix='images')

        if form.is_valid() and formset.is_valid():
            feedback = form.save(commit=False)
            if request.user.is_authenticated:
                feedback.user = request.user 
            feedback.save() 

            for form_in_formset in formset:
                if form_in_formset.cleaned_data.get('image'): 
                    image_instance = form_in_formset.save(commit=False)
                    image_instance.feedback = feedback 
                    image_instance.save()

            return JsonResponse({'message': 'Feedback submitted successfully!', 'status': 'success'}, status=200)
        else:
            errors = {}
            if form.errors:
                errors.update(form.errors.as_json()) 
            if formset.errors:
                formset_errors_list = []
                for i, fs_form in enumerate(formset):
                    if fs_form.errors:
                        formset_errors_list.append(f"Image {i+1}: {fs_form.errors.as_json()}")
                errors['images'] = formset_errors_list 

            return JsonResponse({'message': 'Validation failed', 'status': 'error', 'errors': errors}, status=400)

@api_view(['GET'])
def get_feedback_api(request):
    """
    API endpoint to retrieve all submitted feedback for display.
    Includes associated images and user/email information.
    """
    feedback_queryset = Feedback.objects.all().order_by('-submitted_at').prefetch_related(
        Prefetch('images', queryset=FeedbackImage.objects.all())
    )
    serializer = FeedbackSerializer(feedback_queryset, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


class PostViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Post.objects.filter(is_published=True).order_by('-published_date')
    serializer_class = PostSerializer
    lookup_field = 'pk'

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Returns ALL published blog posts, ordered by recent date.
        This action will no longer limit to 3 posts.
        """
        all_recent_posts = self.get_queryset()
        serializer = self.get_serializer(all_recent_posts, many=True)
        return Response(serializer.data)
    


def update_order_status(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)
        data = json.loads(request.body)
        new_status = data.get('status')

        if new_status and new_status in [choice[0] for choice in order.STATUS_CHOICES]:
            order.status = new_status
            order.save()
            return JsonResponse({'message': 'Order status updated successfully', 'new_status': new_status})
        else:
            return JsonResponse({'error': 'Invalid status provided'}, status=400)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()  
    serializer_class = PostSerializer
    image = serializers.ImageField(required=False) 
    
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.method == 'GET':
            return Post.objects.filter(is_published=True).order_by('-published_date')
        return Post.objects.all()

    lookup_field = 'pk'

    @action(detail=False, methods=['get'])
    def recent(self, request):
        all_recent_posts = self.get_queryset()
        serializer = self.get_serializer(all_recent_posts, many=True)
        return Response(serializer.data)
        
@csrf_exempt
def dispatch(self, *args, **kwargs):
    return super().dispatch(*args, **kwargs)




def search_products(request):
    query = request.GET.get('q', '')
    products = []
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:10] # Limit to 10 results for performance
    
    # Format the products into a list of dictionaries for JSON
    results = [
        {
            'name': product.name,
            'price': product.original_price,
            'url': product.image.url # Assuming you have this method on your model
        }
        for product in products
    ]

    return JsonResponse(results, safe=False)