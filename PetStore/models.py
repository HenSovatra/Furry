from django.db import models
from django.utils.text import slugify 
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.conf import settings
import decimal
User = get_user_model()
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
    
    requires_login = models.BooleanField(
        default=False,
        help_text="Check this if the menu item should only be visible to logged-in users."
    )
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='children',
        help_text="Select a parent menu item if this is a sub-menu item."
    )

    class Meta:
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
        ordering = ['order'] 
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
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories', 
        help_text="Select a parent category if this is a sub-category (e.g., 'Dogs' under 'Health products')."
    )

    class Meta:
        ordering = ['parent__order', 'order', 'name'] 
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

    category = models.ForeignKey(
        'Category', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='products', 
        help_text="The category this product belongs to."
    )

    class Meta:
        ordering = ['-created_at', 'name'] 
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
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

    def update_totals(self):
        """
        Recalculates and updates the total items count (sum of quantities)
        and the total price of all items in the cart.
        """
        self.total_items = sum(item.quantity for item in self.items.all())

        self.total_price = sum(item.total_price for item in self.items.all())

        self.save()


class CartItem(models.Model):
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_at_addition = models.DecimalField(max_digits=10, decimal_places=2, default=decimal.Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart {self.cart.pk}"

    @property
    def total_price(self):
        if self.price_at_addition is not None and self.quantity is not None:
            return self.quantity * self.price_at_addition
        return decimal.Decimal('0.00')

    def save(self, *args, **kwargs):
        if not self.pk: 
            if self.product.discounted_price is not None:
                self.price_at_addition = self.product.discounted_price
            else:
                self.price_at_addition = self.product.original_price

        if isinstance(self.price_at_addition, float):
             self.price_at_addition = decimal.Decimal(str(self.price_at_addition))

        super().save(*args, **kwargs)
        self.cart.update_totals()

    def delete(self, *args, **kwargs):
        cart_to_update = self.cart 
        super().delete(*args, **kwargs)
        cart_to_update.update_totals()


class Order(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True) 
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=50, default='Pending') 
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
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"
    
class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                             help_text="The user who submitted the feedback (if logged in).")
    email = models.EmailField(max_length=255, blank=True, null=True,
                              help_text="Email of the user if not logged in or prefers to provide it.")
    subject = models.CharField(max_length=255, blank=True, null=True,
                               help_text="Optional subject for the feedback.")
    message = models.TextField(help_text="The main feedback message.")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Feedback"
        verbose_name_plural = "Feedback"
        ordering = ['-submitted_at'] 

    def __str__(self):
        submitter = self.user.username if self.user else self.email
        if not submitter:
            submitter = 'Anonymous'
        return f"Feedback from {submitter} - {self.submitted_at.strftime('%Y-%m-%d %H:%M')}"

class FeedbackImage(models.Model):
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='feedback_images/') 
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Feedback Image"
        verbose_name_plural = "Feedback Images"

    def __str__(self):
        return f"Image for Feedback #{self.feedback.id}"
    

class Post(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    author = models.CharField(max_length=100, default='Admin')
    content = models.TextField()
    short_description = models.TextField(blank=True, null=True, help_text="A short summary for display on blog cards.")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    published_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-published_date']
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    def __str__(self):
        return self.title