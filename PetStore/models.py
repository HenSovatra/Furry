from django.db import models
from django.utils.text import slugify 
from django.contrib.auth import get_user_model

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
        ordering = ['parent__order', 'order', 'title'] # Order by parent's order, then its own order
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
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=decimal.Decimal('0.00')) # Use Decimal for default

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
        self.total_items = sum(item.quantity for item in self.items.all())

        # Calculate total_price
        # Ensure that item.total_price is calculated correctly and is a Decimal
        self.total_price = sum(item.total_price for item in self.items.all())

        # Save the Cart instance to persist the updated totals
        self.save()


class CartItem(models.Model):
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # This ensures that each product can only appear once in a given cart
        # If you try to add the same product again, it will retrieve the existing CartItem
        # instead of creating a new one.
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart {self.cart.pk}"

    @property
    def total_price(self):
        # Always use the product's current_price for cart items
        # because the price hasn't been "locked in" like in an OrderItem yet.
        # Ensure current_price is a Decimal
        price = self.product.original_price if self.product.discounted_price is None else self.product.discounted_price
        if price is not None and self.quantity is not None:
            return self.quantity * price
        return decimal.Decimal('0.00') # Return Decimal 0 if values are missing

    def save(self, *args, **kwargs):
        # Update current_price on product for robustness, though current_price is a property
        # You don't need to save product here unless you're modifying product itself.

        super().save(*args, **kwargs) # Call the "real" save() method.
        # After saving this CartItem, update the parent Cart's totals.
        self.cart.update_totals()

    def delete(self, *args, **kwargs):
        cart_to_update = self.cart # Get reference to cart before item is deleted
        super().delete(*args, **kwargs)
        # Update the parent Cart's totals after deleting this item.
        cart_to_update.update_totals()

class Order(models.Model):
    # Link to a User (if authenticated) or allow null for guest checkout
    user = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    
    # Session key for guest users before or if not logged in
    session_key = models.CharField(max_length=40, null=True, blank=True) 

    # Shipping Address Details
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True) # Optional phone
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, null=True) # Optional state/province
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    # Order Status (you can customize these choices)
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')

    # Financial Details
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Payment status (can expand with more options later)
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='Pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {self.id} by {self.first_name} {self.last_name}"

    # Helper property to get the full shipping address
    @property
    def full_address(self):
        address = f"{self.address_line_1}"
        if self.address_line_2:
            address += f", {self.address_line_2}"
        address += f", {self.city}, {self.state or ''} {self.zip_code}, {self.country}"
        return address.strip(', ')


# Order Item Model
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at the time of order

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"

    # Property to calculate total price for this specific order item
    @property
    def total_price(self):
        return self.quantity * self.price
