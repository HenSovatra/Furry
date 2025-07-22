from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
# Explicitly import models from PetStore.models with an alias for Product
from PetStore.models import Product as PetStoreProduct, Category, Cart, CartItem, Order, OrderItem
# Explicitly import models from Admin.models
from Admin.models import Customer, Billing # Add specific imports if needed
# Ensure all serializers are imported
from .serializers import (
    ProductSerializer, CartItemSerializer, OrderSerializer, OrderItemSerializer,
    ProductAdminSerializer, CustomerSerializer, OrderAdminSerializer, BillingSerializer, CategorySerializer
)
from django.shortcuts import get_object_or_404
import json
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework import viewsets # Import viewsets for Admin APIs

# --- Teammate's Existing API Views (UPDATED to use PetStoreProduct) ---
@api_view(['GET'])
def product_list(request):
    products = PetStoreProduct.objects.filter(is_active=True).order_by('-created_at') # Changed to PetStoreProduct
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def product_detail(request, pk):
    product = get_object_or_404(PetStoreProduct, pk=pk, is_active=True) # Changed to PetStoreProduct
    serializer = ProductSerializer(product)
    return Response(serializer.data)

@api_view(['POST'])
def add_to_cart_api(request):
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity', 1))

    product = get_object_or_404(PetStoreProduct, pk=product_id, is_active=True)

    if product.stock < quantity:
        return Response({'error': 'Not enough stock.'}, status=status.HTTP_400_BAD_REQUEST)

    cart = None
    if request.user.is_authenticated:
        # Try to get cart for authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        # If an anonymous cart exists, associate it with the user and delete the old user cart if present
        if not created and request.session.session_key:
            # Find an anonymous cart that is not already associated with this user (could be a leftover)
            anonymous_cart = Cart.objects.filter(session_key=request.session.session_key, user__isnull=True).first()
            if anonymous_cart and anonymous_cart.pk != cart.pk: # Ensure we're not merging a cart with itself
                # Merge items from anonymous cart into authenticated user's cart
                for item in anonymous_cart.items.all():
                    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=item.product)
                    if not item_created:
                        cart_item.quantity += item.quantity
                    else:
                        # If the item was not created (already existed in the user's cart),
                        # and you want to ensure the quantity from the anonymous cart is added,
                        # ensure the above `+=` handles it. If you want to override, change `+=` to `=`.
                        cart_item.quantity = item.quantity # Keep current quantity or adjust based on your merge logic
                    cart_item.save()
                anonymous_cart.delete() # Delete the now-merged anonymous cart
                request.session.pop('cart_total_items', None) # Clear old session total

    if not cart: # If user is not authenticated or no user cart was found/created yet
        # Ensure a session key exists for anonymous users
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key

        # For anonymous carts, we only use session_key for lookup
        # The user field should be null for genuinely anonymous carts
        cart, _ = Cart.objects.get_or_create(session_key=session_key, defaults={'user': None})
        
        # Additional check in case an anonymous cart previously had a user assigned (e.g., user logged out)
        # and you want to ensure it's still treated as an anonymous cart for this session.
        # This is generally handled by 'defaults={'user': None}' above, but good for clarity.
        if cart.user and cart.user != request.user: # If the cart found by session_key has a different user
                                                  # this indicates an edge case. For now, we proceed,
                                                  # but in a production system you might want more robust handling
                                                  # e.g., creating a new anonymous cart or disassociating the old user.
            pass # The existing cart linked to this session_key has a user, so use it as is.

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    # Update total items in session (if applicable) and cart
    request.session['cart_total_items'] = cart.total_items
    cart.update_totals() # This is crucial if Cart model has update_totals method

    return Response({'success': True, 'message': 'Added to cart.'})

@api_view(['GET'])
def cart_details(request):
    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key
    cart = Cart.objects.filter(user=user).first() if user else Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return Response({'cart_items': [], 'total': 0, 'total_items': 0}) # Ensure total_items is returned

    items = cart.items.all()
    serializer = CartItemSerializer(items, many=True)
    return Response({
        'cart_items': serializer.data,
        'total': cart.total_price,
        'total_items': cart.total_items
    })

@api_view(['GET'])
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    serializer = OrderSerializer(order)
    return Response(serializer.data)

@api_view(['POST'])
@csrf_exempt
def update_cart_item_quantity_api(request):
    try:
        product_id = request.data.get('product_id')
        new_quantity = request.data.get('quantity')

        if not product_id or not isinstance(new_quantity, int) or new_quantity < 0:
            return Response({'success': False, 'error': 'Invalid product ID or quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart = Cart.objects.filter(user=user).first() if user else Cart.objects.filter(session_key=session_key).first()
        print(f"Product ID: {product_id}")
        print(f"New Quantity: {new_quantity}")
        if not cart:
            return Response({'success': False, 'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = CartItem.objects.get(cart=cart, product__id=product_id)
        except CartItem.DoesNotExist:
            return Response({'success': False, 'error': 'Item not found in cart.'}, status=status.HTTP_404_NOT_FOUND)

        product = cart_item.product # This 'product' is a PetStoreProduct due to the CartItem relationship

        if new_quantity == 0:
            cart_item.delete()
            message = 'Item removed from cart.'
        else:
            if product.stock < new_quantity:
                return Response({'success': False, 'error': f'Only {product.stock} left in stock. Cannot update to {new_quantity}.'}, status=status.HTTP_400_BAD_REQUEST)

            cart_item.quantity = new_quantity
            cart_item.save()
            message = 'Cart quantity updated.'

        cart.update_totals()
        request.session['cart_total_items'] = cart.total_items

        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error updating cart quantity: {e}")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@csrf_exempt
def remove_from_cart_api(request):
    try:
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({'success': False, 'error': 'Product ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        cart = Cart.objects.filter(user=user).first() if user else Cart.objects.filter(session_key=session_key).first()

        if not cart:
            return Response({'success': False, 'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = CartItem.objects.get(cart=cart, product__id=product_id)
            cart_item.delete()
            message = 'Item successfully removed from cart.'
        except CartItem.DoesNotExist:
            message = 'Item was not in cart (already removed or never existed).'
            return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

        cart.update_totals()
        request.session['cart_total_items'] = cart.total_items

        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error removing from cart: {e}")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@csrf_exempt
def place_order_api(request):
    cart = None
    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key

    if user:
        cart = Cart.objects.filter(user=user).first()
    elif session_key:
        cart = Cart.objects.filter(session_key=session_key).first()
    else:
        return Response({'success': False, 'error': 'Session expired or cart not found.'}, status=status.HTTP_400_BAD_REQUEST)

    if not cart or cart.items.count() == 0:
        return Response({'success': False, 'error': 'Your cart is empty. Please add items to proceed.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data = request.data

        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        phone = data.get('phone', '')
        address_line_1 = data.get('address_line_1')
        address_line_2 = data.get('address_line_2', '')
        city = data.get('city')
        state = data.get('state', '')
        zip_code = data.get('zip_code')
        country = data.get('country')
        payment_method = data.get('paymentMethod')

        errors = {}
        if not first_name: errors['first_name'] = ['First name is required.']
        if not last_name: errors['last_name'] = ['Last name is required.']
        if not email: errors['email'] = ['Email is required.']
        if not address_line_1: errors['address_line_1'] = ['Address Line 1 is required.']
        if not city: errors['city'] = ['City is required.']
        if not zip_code: errors['zip_code'] = ['Zip Code is required.']
        if not country: errors['country'] = ['Country is required.']
        if not payment_method: errors['payment_method'] = ['Payment method is required.']

        for item in cart.items.all():
            if item.product.stock < item.quantity:
                errors['stock'] = [f'Not enough stock for {item.product.name}. Available: {item.product.stock}']
                break

        if errors:
            return Response({'success': False, 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        order = None
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                session_key=session_key if not user else None,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                state=state,
                zip_code=zip_code,
                country=country,
                total_amount=cart.total_price,
                payment_status='Pending',
                status='Pending'
            )

            for item in cart.items.all():
                current_price = item.product.discounted_price if item.product.discounted_price else item.product.original_price # Corrected price logic
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=current_price
                )
                item.product.stock -= item.quantity
                item.product.save()

            cart.items.all().delete()
            cart.delete()
            request.session['cart_total_items'] = 0

        if order:
            try:
                subject = f'Order Confirmation - PetStore Order #{order.id}'
                message = render_to_string('email/order_confirmation_email.txt', {'order': order})
                html_message = render_to_string('email/order_confirmation_email.html', {'order': order})

                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [order.email],
                    fail_silently=False,
                    html_message=html_message,
                )
                print(f"Order confirmation email sent to {order.email} for order {order.id}")
            except Exception as email_e:
                print(f"Failed to send order confirmation email for order {order.id}: {email_e}")

        return Response({
            'success': True,
            'message': 'Order placed successfully!',
            'order_id': order.id,
            'redirect_url': f'/order-confirmation/{order.id}/'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error during order placement: {e}")
        return Response({'success': False, 'error': 'An internal server error occurred during order placement.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- New Admin-Specific API ViewSets ---
class ProductAdminViewSet(viewsets.ModelViewSet):
    queryset = PetStoreProduct.objects.all() # Changed to PetStoreProduct
    serializer_class = ProductAdminSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class OrderAdminViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderAdminSerializer

class BillingViewSet(viewsets.ModelViewSet):
    queryset = Billing.objects.all()
    serializer_class = BillingSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer