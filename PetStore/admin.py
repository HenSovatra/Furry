from django.contrib import admin
from .models import *
# Register your models here.
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
    prepopulated_fields = {'slug': ('name',)} # Auto-fill slug from name in admin
    raw_id_fields = ('category',) # For better category selection if many categories
    date_hierarchy = 'created_at'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price')
    list_filter = ('cart', 'product')
    search_fields = ('cart__user__username', 'product__name')