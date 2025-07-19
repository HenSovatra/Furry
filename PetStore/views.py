# myproject/blog/views.py

from django.shortcuts import render, get_object_or_404
from .models import *
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt 

def CategoryView(request):
    main_menu_items = MenuItem.objects.filter(parent__isnull=True, is_active=True).order_by('order').prefetch_related('children')

    context = {
        'main_menu_items': main_menu_items,
    }
    return render(request, 'category.html', context) 



def HomeView (request):
    main_menu_items = MenuItem.objects.filter(parent__isnull=True, is_active=True).order_by('order').prefetch_related('children')
    slides = Slide.objects.filter(is_active=True).order_by('order')
    top_level_categories = Category.objects.filter(parent__isnull=True, is_active=True).order_by('order').prefetch_related('subcategories')
    products = Product.objects.filter(is_active=True).order_by('-created_at') 
    context = {
        'main_menu_items': main_menu_items,
        'slides': slides,
        'top_level_categories': top_level_categories,
        'products': products,
    }
    return render(request, 'index.html', context) 

def single_product_view(request, pk):
    # Retrieve the product based on its primary key (pk)
    product = get_object_or_404(Product, pk=pk, is_active=True)

    context = {
        'product': product,
        'main_menu_items': MenuItem.objects.filter(parent__isnull=True, is_active=True).order_by('order').prefetch_related('children'),
        'top_level_categories': Category.objects.filter(parent__isnull=True, is_active=True).order_by('order').prefetch_related('subcategories'),
    }
    return render(request, 'single-product.html', context)


def product_quick_view(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    context = {
        'product': product, 
    }
    return render(request, 'product_modal_content.html', context)



@require_POST
@csrf_exempt # For simplicity during development, but use CsrfViewMiddleware in production
def add_to_cart(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    if not product_id or not quantity:
        return JsonResponse({'success': False, 'error': 'Product ID and quantity are required.'}, status=400)

    try:
        product = get_object_or_404(Product, pk=product_id, is_active=True)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Product not found or not active.'}, status=404)

    # Validate quantity
    if not isinstance(quantity, int) or quantity < 1:
        return JsonResponse({'success': False, 'error': 'Quantity must be a positive integer.'}, status=400)

    if product.stock < quantity:
        return JsonResponse({'success': False, 'error': f'Not enough stock for {product.name}. Available: {product.stock}'}, status=400)

    # Get or create cart
    cart = None
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # Use session key for anonymous users
        session_key = request.session.session_key
        if not session_key:
            request.session.save() # Ensure session key exists
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)

    # Add/Update cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity # If newly created, set quantity directly
    cart_item.save()

    # Update total items in session for easy access in templates
    request.session['cart_total_items'] = cart.total_items

    return JsonResponse({
        'success': True,
        'message': f'{quantity} x {product.name} added to cart.',
        'cart_total_items': cart.total_items,
        'product_added': {
            'id': product.pk,
            'name': product.name,
            'image_url': product.image.url,
            'quantity': cart_item.quantity, # Current quantity of this item in cart
            'price': float(product.original_price), # Convert Decimal to float for JSON
            'total_item_price': float(cart_item.total_price),
        }
    })

# New view to get cart details for the dialog
def get_cart_details(request):
    cart = None
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()

    cart_items_data = []
    if cart:
        for item in cart.items.all():
            cart_items_data.append({
                'product_id': item.product.pk,
                'product_name': item.product.name,
                'product_image_url': item.product.image.url if item.product.image else '',
                'quantity': item.quantity,
                'price': float(item.product.original_price),
                'total_item_price': float(item.total_price),
            })

    return JsonResponse({
        'cart_items': cart_items_data,
        'cart_total_price': float(cart.total_price) if cart else 0.0,
        'cart_total_items': cart.total_items if cart else 0,
    })