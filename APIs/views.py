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
from rest_framework import viewsets, filters # Import filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
import stripe
from rest_framework import filters
import logging
from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework import generics

from django.views import View
from .serializers import RegisteredCustomerSerializer
from rest_framework.permissions import AllowAny
from PetStore.forms import FeedbackForm,FeedbackImageFormSet
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch

from django.http import JsonResponse

logger = logging.getLogger(__name__) # Initialize logger for this module

stripe.api_key = settings.STRIPE_SECRET_KEY

# --- Centralized Cart Helper Function ---
def get_or_create_cart(request):
    """
    Retrieves or creates a cart based on user authentication status or session key.
    """
    if request.user.is_authenticated:
        # For authenticated users, find or create a cart linked to their user account.
        # Ensure session_key is None for authenticated users' carts to avoid confusion.
        cart, created = Cart.objects.get_or_create(user=request.user, defaults={'session_key': None})
        # TODO: Implement cart merging logic here if an anonymous cart exists for the session
        # and the user just logged in. This is a more advanced feature.
    else:
        # For anonymous users, use the session key to identify/create the cart.
        session_key = request.session.session_key
        if not session_key:
            # If session is new, save it to generate a session_key
            request.session.save()
            session_key = request.session.session_key
        # Get or create a cart linked to the session key and explicitly no user.
        cart, created = Cart.objects.get_or_create(session_key=session_key, user=None)
        # Ensure the session_key is correctly set on the cart in case it was just created
        if created or not cart.session_key: # Ensure it's set if new or was somehow missing
            cart.session_key = session_key
            cart.save()
    return cart

# --- Product Views ---

# --- Teammate's Existing API Views (UPDATED to use PetStoreProduct) ---
@api_view(['GET'])
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('-created_at') # Changed to PetStoreProduct
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True) # Changed to PetStoreProduct
    serializer = ProductSerializer(product)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny]) # Allow anyone to add to cart
@csrf_exempt # Use @csrf_protect if you rely on Django's session-based CSRF for this API.
def add_to_cart_api(request):
    cart = get_or_create_cart(request) # <--- Use the helper here
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
    # price_at_addition is set in CartItem's save method, no need to set here explicitly unless you want to override
    cart_item.save()

    # Update cart totals after item change (CartItem's save/delete triggers cart.update_totals)
    # cart.update_totals() # This call is handled by CartItem's save/delete methods
    request.session['cart_total_items'] = cart.total_items # Update session for frontend display

    return Response({'success': True, 'message': 'Added to cart.', 'cart_total_items': cart.total_items})

@api_view(['GET'])
@permission_classes([AllowAny]) # Allow anyone to view cart details
def cart_details(request):
    cart = get_or_create_cart(request) # <--- Use the helper here

    # CORRECTED LINE: Use 'items.all()' because of related_name='items' in CartItem model
    items = cart.items.all()
    serializer = CartItemSerializer(items, many=True)

    # Ensure cart.total_price and cart.total_items are correctly calculated and updated
    cart.update_totals() # Call this before returning if totals are not always fresh

    return Response({
        'cart_items': serializer.data,
        'total': cart.total_price,
        'total_items': cart.total_items
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated]) # Order detail should typically require authentication
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # Ensure only the owner or staff can view the order
    if not request.user.is_staff and order.user != request.user:
        return Response({'error': 'You do not have permission to view this order.'}, status=status.HTTP_403_FORBIDDEN)
    serializer = OrderSerializer(order)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny]) # Allow anyone to update cart quantity
@csrf_exempt # Use @csrf_protect if you rely on Django's session-based CSRF for this API.
def update_cart_item_quantity_api(request):
    try:
        product_id = request.data.get('product_id')
        new_quantity = request.data.get('quantity')

        if not product_id or not isinstance(new_quantity, int) or new_quantity < 0:
            return Response({'success': False, 'error': 'Invalid product ID or quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(request) # <--- Use the helper here

        try:
            # CORRECTED LINE: Use 'items' to access CartItems
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

        # cart.update_totals() is implicitly called by CartItem's save/delete methods
        request.session['cart_total_items'] = cart.total_items # Update session for frontend display

        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Error updating cart quantity:")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny]) # Allow anyone to remove from cart
@csrf_exempt # Use @csrf_protect if you rely on Django's session-based CSRF for this API.
def remove_from_cart_api(request):
    try:
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'success': False, 'error': 'Product ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(request) # <--- Use the helper here

        try:
            # CORRECTED LINE: Use 'items' to access CartItems
            cart_item = cart.items.get(product__id=product_id)
            cart_item.delete()
            message = 'Item successfully removed from cart.'
        except CartItem.DoesNotExist:
            message = 'Item was not in cart (already removed or never existed).'
            # Even if item wasn't there, it's a success from the user's perspective (they wanted it gone)
            return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

        # cart.update_totals() is implicitly called by CartItem's save/delete methods
        request.session['cart_total_items'] = cart.total_items # Update session for frontend display

        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Error removing from cart:")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny]) # Allow both authenticated and guest users to place orders
@csrf_protect # Crucial for security, especially when handling financial transactions
def place_order_api(request):
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        return Response({'error': 'Your cart is empty. Please add items before placing an order.'},
                         status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    payment_method_id = data.get('payment_method_id') # For the first call to create PI
    payment_intent_id = data.get('payment_intent_id') # For the second call to finalize PI

    # For guest users, the email is mandatory as it's their identifier for the order
    email = data.get('email')
    if not email:
        return Response({'error': 'Email is required for guest checkout.'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate required checkout fields (basic check)
    required_fields = ['first_name', 'last_name', 'email', 'address_line_1', 'city', 'state', 'zip_code', 'country']
    for field in required_fields:
        if not data.get(field):
            return Response({'error': f'{field.replace("_", " ").title()} is required.'}, status=status.HTTP_400_BAD_REQUEST)

    # --- SECURITY CRITICAL: Calculate total amount securely on the backend ---
    try:
        final_total_amount = Decimal('0.00')
        # Ensure you are fetching product price from the Product model, not just item.total_price from cart item,
        # unless item.total_price is dynamically calculated on item.save() based on current product prices.
        # It's safer to recalculate from Product model here.
        for item in cart.items.all():
            if item.product.discounted_price is not None:
                product_price = item.product.discounted_price
            else:
                product_price = item.product.original_price
            if not isinstance(product_price, Decimal):
                product_price = Decimal(str(product_price)) # Ensure Decimal for calculations
            final_total_amount += product_price * item.quantity

        # Add shipping costs, taxes, etc., if applicable
        shipping_cost = Decimal('5.00') # Example static shipping cost
        final_total_amount += shipping_cost

        total_amount_cents = int(final_total_amount * 100) # Convert to smallest currency unit (cents)

        if total_amount_cents <= 0:
            return Response({'error': 'Cart total must be greater than zero after all calculations.'}, status=status.HTTP_400_BAD_REQUEST)

    except Product.DoesNotExist: # Or whatever exception your product retrieval might throw
        return Response({'error': 'One or more products in your cart could not be found or have an invalid price.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error calculating total amount in place_order_api:")
        return Response({'error': f'Failed to calculate order total: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # --- End of secure total calculation ---


    try:
        with transaction.atomic():
            order = None # Initialize order to None

            # --- Payment Intent Confirmation Flow (Second call from frontend) ---
            if payment_intent_id:
                try:
                    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

                    # Check if an order already exists for this payment_intent_id
                    existing_order = Order.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
                    if existing_order:
                        logger.info(f"Duplicate call for PI {payment_intent_id}. Order {existing_order.id} already exists.")
                        my_return_url = f'{settings.BASE_URL}/order-confirmation/{existing_order.id}'
                        print(f"DEBUG: Attempting to create PaymentIntent with return_url: {my_return_url}") # <--- ADD THIS LINE
                        return Response({
                            'success': True,
                            'message': 'Order already processed successfully!',
                            'redirect_url': my_return_url
                        }, status=status.HTTP_200_OK)

                    # Crucial check: Ensure the retrieved PaymentIntent matches the calculated amount
                    # This protects against a user manipulating the PI ID to complete a cheaper payment.
                    if payment_intent.amount != total_amount_cents:
                        logger.warning(f"Amount mismatch for PI {payment_intent_id}. Expected {total_amount_cents}, got {payment_intent.amount}.")
                        return Response({'error': 'Payment amount mismatch. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)


                    if payment_intent.status == 'succeeded':
                        order_data = {
                            'total_amount': final_total_amount, # Use the Decimal amount
                            'status': 'Processing', # Initial status for new order, can be 'Pending'
                            'payment_status': 'Paid',
                            'first_name': data.get('first_name'),
                            'last_name': data.get('last_name'),
                            'shipping_cost': shipping_cost,
                            'email': email,
                            'phone': data.get('phone', ''), # Provide default empty string for optional fields
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
                            'stripe_payment_intent_id': payment_intent.id, # Save the PI ID
                            'payment_method': data.get('paymentMethod'), # This should be 'card', 'paypal', etc. from client
                        }
                        if request.user.is_authenticated:
                            order_data['user'] = request.user
                        else:
                            # For guest users, store the session key
                            # Ensure the session has been saved/created for the key to exist
                            if request.session.session_key:
                                order_data['session_key'] = request.session.session_key
                            else:
                                # This should ideally not happen if get_or_create_cart is working,
                                # but as a fallback, ensure session is saved
                                request.session.save()
                                order_data['session_key'] = request.session.session_key

                        order = Order.objects.create(**order_data)
                        price = item.product.discounted_price if item.product.discounted_price is not None else item.product.original_price
                        for item in cart.items.all():
                            OrderItem.objects.create(
                                order=order,
                                product=item.product,
                                quantity=item.quantity,
                                price= price, # Use product's current price at order time for OrderItem
                                total_price=item.quantity * price
                            )

                        cart.items.all().delete() # Clear the cart items
                        # If you want to delete the cart itself if it's empty, you could do:
                        # if not cart.items.exists():
                        #     cart.delete()

                        # Send order confirmation email
                        subject = 'Your PetStore Order Confirmation'
                        recipient_email = order.email
                        html_message = render_to_string('email/order_confirmation_email.html', {'order': order, 'user': order.user if order.user else None})
                        plain_message = f'Thank you for your order, {order.first_name}! Your order ID is {order.id}.'
                        send_mail(subject, plain_message, settings.EMAIL_HOST_USER, [recipient_email], html_message=html_message)
                        my_return_url = f'{settings.BASE_URL}/order-confirmation/{order.id}'
                        print(f"DEBUG: Attempting to create PaymentIntent with return_url: {my_return_url}") # <--- ADD THIS LINE

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

            # --- Payment Intent Creation Flow (First call from frontend) ---
            elif payment_method_id:
                try:
                    intent = stripe.PaymentIntent.create(
                        amount=total_amount_cents,
                        currency='usd',
                        payment_method=payment_method_id,
                        confirmation_method='automatic', # <--- **FIXED THIS LINE**
                        confirm=True, # <--- REMOVE THIS LINE
                        return_url=f'{settings.BASE_URL}/order-confirmation/', # Crucial for 3DS! e.g., 'http://localhost:8000/checkout-success/'
                        metadata={
                            'cart_id': str(cart.id), # Metadata values must be strings
                            'customer_email': email,
                            'is_guest_checkout': 'true' if not request.user.is_authenticated else 'false',
                            'user_id': str(request.user.id) if request.user.is_authenticated else 'guest'
                        },
                        # It's good practice to send shipping details to Stripe too
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
                    # Return client_secret to frontend for client-side confirmation
                    return Response({
                        'success': True, # Indicate that creation was successful and client needs to confirm
                        'client_secret': intent.client_secret,
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

    except Exception as e: # Catch any other unexpected errors during the entire process
        logger.exception("Unhandled error in place_order_api:")
        return Response({'error': f'An unexpected error occurred: {str(e)}'},
                                     status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Authentication Views ---
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
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'success': True,
            'message': 'Login successful.',
            'username': user.username,
            'token': token.key,
        }, status=status.HTTP_200_OK)
    else:
        return Response({'success': False, 'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

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

# --- New Admin-Specific API ViewSets ---
class ProductAdminViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductAdminSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter] # Add filter backends
    filterset_fields = ['category'] # Enable filtering by category ID
    search_fields = ['name', 'description'] # Enable searching by name and description

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class OrderAdminViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderAdminSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter] # Add filter backends
    filterset_fields = ['status'] # Enable filtering by the 'status' field
    search_fields = ['id', 'billing_first_name', 'billing_email'] # Optional: Add search functionality

class BillingViewSet(viewsets.ModelViewSet):
    queryset = Billing.objects.all()
    serializer_class = BillingSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    # Include prefetch_related for efficiency when fetching order lists or details
    queryset = Order.objects.all().prefetch_related('order_items')


class RegisteredCustomerAPIView(generics.ListCreateAPIView):
    """
    API View to list all registered customers (GET) and register new ones (POST).
    """
    queryset = User.objects.all() # This queryset is used for listing (GET)

    # Override get_serializer_class to use different serializers for GET and POST
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RegisterSerializer # Use RegisterSerializer for creating (POST)
        return RegisteredCustomerSerializer # Use RegisteredCustomerSerializer for listing (GET)

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
        for product in products.distinct(): # Use distinct() if you combined querysets
            price = 0
            image_url = request.build_absolute_uri(product.image.url) if product.image else ''
            print(image_url)
            if product.discounted_price is not None:
                price = product.discounted_price
            else:
                price = product.original_price
            product_data.append({
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': float(price), # Convert Decimal to float for JSON
                'image': image_url, # Get full URL
            })

        return Response(product_data)
    except Exception as e:
        print(f"Error fetching products by category {category_id}: {e}")
        return Response({'error': str(e)}, status=500)
    


class FeedbackAPIView(View):
    def post(self, request, *args, **kwargs):
        # Django automatically handles multipart/form-data for file uploads.
        # request.POST will contain text fields, request.FILES will contain files.

        form = FeedbackForm(request.POST)
        # Initialize the formset with POST data and FILES data
        # 'images' is the prefix for the formset, based on related_name in FeedbackImage model
        formset = FeedbackImageFormSet(request.POST, request.FILES, prefix='images')

        if form.is_valid() and formset.is_valid():
            feedback = form.save(commit=False)
            if request.user.is_authenticated:
                feedback.user = request.user # Link feedback to the logged-in user
            feedback.save() # Save the main feedback object first

            # Save the images, linking them to the newly created feedback object
            for form_in_formset in formset:
                if form_in_formset.cleaned_data.get('image'): # Check if an image file was actually provided
                    image_instance = form_in_formset.save(commit=False)
                    image_instance.feedback = feedback # Link image to the saved feedback
                    image_instance.save()

            return JsonResponse({'message': 'Feedback submitted successfully!', 'status': 'success'}, status=200)
        else:
            # If validation fails, compile error messages from both form and formset
            errors = {}
            if form.errors:
                errors.update(form.errors.as_json()) # Get general form errors
            if formset.errors:
                formset_errors_list = []
                for i, fs_form in enumerate(formset):
                    if fs_form.errors:
                        # Append errors for each image form in the formset
                        formset_errors_list.append(f"Image {i+1}: {fs_form.errors.as_json()}")
                errors['images'] = formset_errors_list # Assign all image-related errors under 'images' key

            return JsonResponse({'message': 'Validation failed', 'status': 'error', 'errors': errors}, status=400)

# --- 3. API View to Get All Feedback (for Frontend Display) ---
@api_view(['GET'])
def get_feedback_api(request):
    """
    API endpoint to retrieve all submitted feedback for display.
    Includes associated images and user/email information.
    """
    # Fetch all Feedback objects, order by newest first
    # Use Prefetch to get all related images efficiently in a single query
    feedback_queryset = Feedback.objects.all().order_by('-submitted_at').prefetch_related(
        Prefetch('images', queryset=FeedbackImage.objects.all())
    )

    # Serialize the queryset using the FeedbackSerializer
    serializer = FeedbackSerializer(feedback_queryset, many=True, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)

