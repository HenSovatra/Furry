from django.contrib import admin
from pyparsing import Or
from .models import *
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'order', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('title', 'url')

@admin.register(Slide)
class SlideAdmin(admin.ModelAdmin):
    list_display = ('heading', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('heading', 'tagline')
    ordering = ('order',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'icon_id', 'order', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'url', 'icon_id')
    ordering = ('order',)
    raw_id_fields = ('parent',) 

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'original_price', 'discounted_price', 'stock', 'is_active', 'created_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)} 
    raw_id_fields = ('category',) 
    date_hierarchy = 'created_at'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price')
    list_filter = ('cart', 'product')
    search_fields = ('cart__user__username', 'product__name')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    readonly_fields = ['price', 'total_price'] 
    fields = ['product', 'quantity', 'price', 'total_price'] 


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_display', 'full_name', 'email', 'total_amount', 'status', 'payment_status', 'created_at'
    )

    list_filter = ('status', 'payment_status', 'created_at')

    search_fields = ('id__iexact', 'first_name__icontains', 'last_name__icontains', 'email__icontains', 'user__username__icontains')
  
    date_hierarchy = 'created_at'
    raw_id_fields = ('user',) 

    def user_display(self, obj):
        return obj.user.username if obj.user else 'Guest'
    user_display.short_description = 'User'
    user_display.admin_order_field = 'user__username'

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Customer Name'
    full_name.admin_order_field = 'last_name'

    inlines = [OrderItemInline] 


class FeedbackImageInline(admin.TabularInline):
    model = FeedbackImage
    extra = 0 
    max_num = 5 
    can_delete = False 

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'email', 'subject', 'submitted_at')
    list_filter = ('submitted_at', 'user') 
    search_fields = ('message', 'subject', 'user__username', 'email') 
    inlines = [FeedbackImageInline] 

    def user_display(self, obj):
        return obj.user.username if obj.user else 'Anonymous'
    user_display.short_description = 'User'

@admin.register(FeedbackImage)
class FeedbackImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'feedback', 'image', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('feedback__subject', 'feedback__message')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'published_date', 'is_published', 'updated_at')
    list_filter = ('category', 'is_published', 'published_date')
    search_fields = ('title', 'content', 'short_description', 'author')
    date_hierarchy = 'published_date'
    fieldsets = (
        (None, {
            'fields': ('title', 'short_description', 'content', 'image', 'category', 'author', 'is_published')
        }),
    )