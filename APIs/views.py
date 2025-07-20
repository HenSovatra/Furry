from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from PetStore.models import *
from .serializers import ProductSerializer, CartItemSerializer, OrderSerializer
from django.shortcuts import get_object_or_404
import json 
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.mail import send_mail # NEW: Import send_mail
from django.template.loader import render_to_string # NEW: For rendering email templates
from django.conf import settings

@api_view(['GET'])
def product_list(request):
    products = Product.objects.filter(is_active=True).order_by('-created_at')
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    serializer = ProductSerializer(product)
    return Response(serializer.data)

@api_view(['POST'])
def add_to_cart_api(request):
    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key or request.session.save()
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity', 1))
    
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    
    if product.stock < quantity:
        return Response({'error': 'Not enough stock.'}, status=status.HTTP_400_BAD_REQUEST)

    cart, _ = Cart.objects.get_or_create(user=user, session_key=session_key)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    return Response({'success': True, 'message': 'Added to cart.'})

@api_view(['GET'])
def cart_details(request):
    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key
    cart = Cart.objects.filter(user=user).first() if user else Cart.objects.filter(session_key=session_key).first()

    if not cart:
        return Response({'cart_items': [], 'total': 0})

    items = cart.items.all()
    serializer = CartItemSerializer(items, many=True)
    print(serializer.data)
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
@csrf_exempt # REMOVE IN PRODUCTION. Use proper CSRF protection.
def update_cart_item_quantity_api(request):
    try:
        data = json.loads(request.body) # Use json.loads for request.body
        product_id = data.get('product_id')
        new_quantity = data.get('quantity') # This is the absolute new quantity, not a change

        if not product_id or not isinstance(new_quantity, int) or new_quantity < 0:
            return Response({'success': False, 'error': 'Invalid product ID or quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None
        session_key = request.session.session_key
        # Get cart based on user or session
        if user:
            cart = Cart.objects.filter(user=user).first()
        else:
            if not session_key: # Ensure session exists for guest users
                request.session.create()
                session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first()

        if not cart:
            return Response({'success': False, 'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = CartItem.objects.get(cart=cart, product__id=product_id)
        except CartItem.DoesNotExist:
            return Response({'success': False, 'error': 'Item not found in cart.'}, status=status.HTTP_404_NOT_FOUND)

        product = cart_item.product # Get the associated product to check stock

        if new_quantity == 0:
            # If new quantity is 0, remove the item
            cart_item.delete() # This will trigger cart.update_totals()
            message = 'Item removed from cart.'
        else:
            # Check stock before updating quantity
            if product.stock < new_quantity:
                return Response({'error': f'Only {product.stock} left in stock. Cannot update to {new_quantity}.'}, status=status.HTTP_400_BAD_REQUEST)

            cart_item.quantity = new_quantity
            cart_item.save() # This will trigger cart.update_totals()
            message = 'Cart quantity updated.'

        # Explicitly call update_totals just in case, or to ensure 'cart' object in memory is updated
        cart.update_totals()
        request.session['cart_total_items'] = cart.total_items # Update session cart count

        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except json.JSONDecodeError:
        return Response({'success': False, 'error': 'Invalid JSON request.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Error updating cart quantity: {e}")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@csrf_exempt # REMOVE IN PRODUCTION. Use proper CSRF protection.
def remove_from_cart_api(request):
    try:
        data = json.loads(request.body) # Use json.loads for request.body
        product_id = data.get('product_id')

        if not product_id:
            return Response({'success': False, 'error': 'Product ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user if request.user.is_authenticated else None
        session_key = request.session.session_key
        # Get cart based on user or session
        if user:
            cart = Cart.objects.filter(user=user).first()
        else:
            if not session_key: # Ensure session exists for guest users
                request.session.create()
                session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first()

        if not cart:
            return Response({'success': False, 'error': 'Cart not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = CartItem.objects.get(cart=cart, product__id=product_id)
            cart_item.delete() # This will trigger cart.update_totals()
            message = 'Item successfully removed from cart.'
        except CartItem.DoesNotExist:
            message = 'Item was not in cart (already removed or never existed).'
            # It's often better to return 200 OK even if not found, if the desired state is "not in cart"
            return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

        # Explicitly call update_totals just in case, or to ensure 'cart' object in memory is updated
        cart.update_totals()
        request.session['cart_total_items'] = cart.total_items # Update session cart count

        return Response({'success': True, 'message': message, 'cart_total_items': cart.total_items}, status=status.HTTP_200_OK)

    except json.JSONDecodeError:
        return Response({'success': False, 'error': 'Invalid JSON request.'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"Error removing from cart: {e}")
        return Response({'success': False, 'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt # IMPORTANT: REMOVE THIS IN PRODUCTION AND USE PROPER CSRF PROTECTION
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
        email = data.get('email') # Recipient email
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

        order = None # Define order outside try-except for email sending
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

            current_price = 0
            if item.product.discounted_price:
                current_price = item.product.discounted_price
            else:
                current_price = item.product.original_price
            for item in cart.items.all():
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

        # --- Email Sending Logic (AFTER successful transaction) ---
        if order: # Ensure order was created successfully
            try:
                subject = f'Order Confirmation - PetStore Order #{order.id}'
                # You can render an HTML email template for a nicer email
                # For now, let's create a simple text message
                message = render_to_string('email/order_confirmation_email.txt', {'order': order})
                html_message = render_to_string('email/order_confirmation_email.html', {'order': order})

                send_mail(
                    subject,
                    message, # Plain text message
                    settings.DEFAULT_FROM_EMAIL, # Sender email from settings
                    [order.email], # Recipient email (from the order)
                    fail_silently=False, # Set to True in production to avoid crashing on email failure
                    html_message=html_message, # HTML version of the email
                )
                print(f"Order confirmation email sent to {order.email} for order {order.id}")
            except Exception as email_e:
                print(f"Failed to send order confirmation email for order {order.id}: {email_e}")
                # Log this error, but don't prevent the order from being placed.
                # In a real system, you might queue failed emails for retry.

        return Response({
            'success': True,
            'message': 'Order placed successfully!',
            'order_id': order.id,
            'redirect_url': f'/order-confirmation/{order.id}/'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"Error during order placement: {e}")
        return Response({'success': False, 'error': 'An internal server error occurred during order placement.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
