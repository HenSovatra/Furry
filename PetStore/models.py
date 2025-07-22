from django.db import models
from django.utils.text import slugify 
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.conf import settings
import decimal

class MenuItem(models.Model):
    title = models.CharField(max_length=100, help_text="The text displayed in the navigation bar.")
    url = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="The URL this menu item links to. Leave blank for parent items that only serve as dropdowns."
    )
    order = models.IntegerField(default=0, help_text="The order in which menu items appear (lower numbers first).")
    is_active = models.BooleanField(default=True, help_text="Whether this menu item should be displayed.")
    
    # NEW FIELD:
    requires_login = models.BooleanField(
        default=False,
        help_text="Check this if the menu item should only be visible to logged-in users."
    )
    
    # Self-referential Foreign Key for parent-child relationship
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        help_text="Select a parent menu item if this is a sub-menu item."
    )

    class Meta:
        # Update ordering to potentially include requires_login or keep as is.
        # It's usually better to filter by requires_login in the view/template.
        ordering = ['parent__order', 'order', 'title'] 
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"

    def __str__(self):
        if self.parent:
            return f"{self.parent.title} > {self.title}"
        return self.title


class Slide(models.Model):
    image = models.ImageField(upload_to='slides/', help_text="Upload the image for this slide.")
    tagline = models.CharField(max_length=200, help_text="The small paragraph text (e.g., 'Premium pet supplies for happy tails').")
    heading = models.CharField(max_length=150, help_text="The large heading text (e.g., 'Pet Shop').")
    button_text = models.CharField(max_length=50, default="Shop Now", help_text="Text for the call-to-action button.")
    button_url = models.CharField(max_length=255, default="#", help_text="The URL the button links to (e.g., '/shop/').")
    order = models.IntegerField(default=0, help_text="The display order of the slide (lower numbers first).")
    is_active = models.BooleanField(default=True, help_text="Whether this slide should be displayed in the slideshow.")

    class Meta:
        ordering = ['order'] # Order slides by their 'order' field
        verbose_name = "Slideshow Slide"
        verbose_name_plural = "Slideshow Slides"

    def __str__(self):
        return f"Slide {self.order}: {self.heading}"
    
class Category(models.Model):
    name = models.CharField(max_length=100, help_text="Name of the category (e.g., 'Pet foods', 'Dogs').")
    url = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="The URL this category links to (e.g., '/shop/pet-foods/'). Leave blank for parent categories that only serve as headers for collapsible menus."
    )
    icon_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="The ID of the SVG symbol to use for this category (e.g., 'dairy', 'meat', 'health')."
    )
    order = models.IntegerField(default=0, help_text="The order in which categories appear (lower numbers first).")
    is_active = models.BooleanField(default=True, help_text="Whether this category should be displayed.")
    
    # Self-referential Foreign Key for parent-child relationship (for collapsible sub-menus)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories', # Renamed to 'subcategories' for clarity
        help_text="Select a parent category if this is a sub-category (e.g., 'Dogs' under 'Health products')."
    )

    class Meta:
        ordering = ['parent__order', 'order', 'name'] # Order by parent's order, then its own order
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    

class Product(models.Model):
    name = models.CharField(max_length=200, help_text="Name of the product.")
    image = models.ImageField(upload_to='products/', help_text="Main image for the product.")
    original_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Original price of the product.")
    discounted_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Discounted price of the product (optional)."
    )
    # Using a slug for clean, human-readable URLs for single product pages
    slug = models.SlugField(
        max_length=200, 
        unique=True, 
        blank=True, 
        help_text="A short, unique label for the product URL (auto-generated if left blank)."
    )
    description = models.TextField(blank=True, help_text="Detailed description of the product.")
    stock = models.IntegerField(default=0, help_text="Current stock quantity.")
    is_active = models.BooleanField(default=True, help_text="Whether this product is available for sale.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Link to the Category model
    category = models.ForeignKey(
        'Category', # Referencing the Category model
        on_delete=models.SET_NULL, # Products won't be deleted if a category is removed
        null=True, 
        blank=True,
        related_name='products', # Allows you to get products from a category: category.products.all()
        help_text="The category this product belongs to."
    )

    class Meta:
        ordering = ['-created_at', 'name'] # Order by newest first, then by name
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    # Override save method to auto-generate slug if not provided
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure slug is unique if a product with the same name exists
            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_items = models.PositiveIntegerField(default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=decimal.Decimal('0.00'))

    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"

    def __str__(self):
        return f"Cart {self.pk} (User: {self.user.username if self.user else self.session_key[:5] if self.session_key else 'Guest'})"

    # THIS IS THE METHOD THAT NEEDS TO BE PRESENT AND CORRECTLY SPELLED
    def update_totals(self):
        """
        Recalculates and updates the total items count (sum of quantities)
        and the total price of all items in the cart.
        """
        # Calculate total_items
        # Access cart items via the related_name 'items' defined in CartItem
        self.total_items = sum(item.quantity for item in self.items.all())

        # Calculate total_price
        # Ensure that item.total_price is calculated correctly and is a Decimal
        # The .items.all() refers to CartItem instances linked to this cart
        self.total_price = sum(item.total_price for item in self.items.all())

        # Save the Cart instance to persist the updated totals
        self.save()


class CartItem(models.Model):
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    # --- IMPORTANT ADDITION / CHANGE ---
    # This field captures the price *at the moment* the item was added to the cart or last updated.
    # This is crucial because product prices can change, but the price in the cart should reflect what the user saw/agreed to.
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2, default=decimal.Decimal('0.00'))
    # --- END IMPORTANT ADDITION / CHANGE ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart {self.cart.pk}"

    @property
    def total_price(self):
        # Calculate total based on the price_at_addition field, not the current product price.
        # This reflects the price captured when the item was added/last updated in the cart.
        if self.price_at_addition is not None and self.quantity is not None:
            return self.quantity * self.price_at_addition
        return decimal.Decimal('0.00')

    def save(self, *args, **kwargs):
        # --- IMPORTANT CHANGE: Capture product's current_price here ---
        # Before saving, set price_at_addition to the product's current price
        # This ensures the price is "locked in" for this cart item
        if not self.pk: # Only set price_at_addition on initial creation
            if self.product.discounted_price is not None:
                self.price_at_addition = self.product.discounted_price
            else:
                self.price_at_addition = self.product.original_price
        # If you want price_at_addition to update when quantity changes, you can put this
        # outside the 'if not self.pk' block. However, typically it's only set once.
        # Consider a separate mechanism if product price changes should affect existing cart items.
        # For a standard e-commerce flow, price_at_addition is set on first add.
        # For updates to quantity, the price_at_addition usually remains the same.
        # If the product's price changes *after* it's in the cart, you might want to show an alert.
        # For now, let's keep it simple: price_at_addition is set on initial addition.

        # Ensure price_at_addition is always a Decimal
        if isinstance(self.price_at_addition, float):
             self.price_at_addition = decimal.Decimal(str(self.price_at_addition))

        super().save(*args, **kwargs) # Call the "real" save() method.
        # After saving this CartItem, update the parent Cart's totals.
        self.cart.update_totals()

    def delete(self, *args, **kwargs):
        cart_to_update = self.cart # Get reference to cart before item is deleted
        super().delete(*args, **kwargs)
        # Update the parent Cart's totals after deleting this item.
        cart_to_update.update_totals()


class Order(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True) # For guest orders
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='Pending') # e.g., 'Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'
    payment_status = models.CharField(max_length=50, default='Pending') # e.g., 'Pending', 'Paid', 'Refunded', 'Failed'
    created_at = models.DateTimeField(auto_now_add=True)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)

    billing_first_name = models.CharField(max_length=100, blank=True, null=True)
    billing_last_name = models.CharField(max_length=100, blank=True, null=True)
    billing_email = models.EmailField(blank=True, null=True)
    billing_phone = models.CharField(max_length=20, blank=True, null=True)
    billing_address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    billing_address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    billing_city = models.CharField(max_length=100, blank=True, null=True)
    billing_state = models.CharField(max_length=100, blank=True, null=True)
    billing_zip_code = models.CharField(max_length=20, blank=True, null=True)
    billing_country = models.CharField(max_length=100, blank=True, null=True)
    # Billing Information (from checkout form)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    # NEW: Field to store Stripe Payment Intent ID
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, unique=True)


    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} by {self.user.username if self.user else self.session_key}"

    @property
    def get_cart_total(self):
        return sum(item.get_total for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at time of order
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"