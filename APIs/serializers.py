# Furry/APIs/serializers.py
from rest_framework import serializers
from datetime import datetime, timezone # Make sure this import is present if you use default=timezone.now

# Explicitly import models from PetStore.models with an alias for Product
from PetStore.models import Product as PetStoreProduct, Category, Cart, CartItem, Order, OrderItem
# Explicitly import models from Admin.models
from Admin.models import Customer, Billing

# --- Teammate's Existing Serializers (UPDATED to use PetStoreProduct) ---
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetStoreProduct
        fields = ['id', 'name', 'original_price', 'discounted_price', 'stock', 'image']

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = CartItem
        fields = ['product', 'quantity', 'total_price']

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True)

    class Meta:
        model = Order
        fields = '__all__'

# --- New Admin-Specific Serializers (MODIFIED ProductAdminSerializer) ---

# Ensure CategorySerializer is defined before ProductAdminSerializer if nested
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductAdminSerializer(serializers.ModelSerializer):
    # For READ operations (output) - sends the full nested category
    category = CategorySerializer(read_only=True)
    
    # For WRITE operations (input) - accepts just the category ID
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category', # Maps this field to the 'category' ForeignKey
        write_only=True    # This field is only for input, not for output
    )

    # IMPORTANT CHANGE FOR created_at:
    # If your PetStoreProduct model has created_at = models.DateTimeField(auto_now_add=True),
    # then set it to read_only=True here. The API will handle populating it.
    # It will still be formatted as DD/MM/YY for output.
    created_at = serializers.DateTimeField(format="%d/%m/%y", read_only=True) 

    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = PetStoreProduct
        fields = '__all__' # Includes both 'category' (read) and 'category_id' (write), and 'created_at' (read-only)

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

class OrderAdminSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, read_only=True)
    class Meta:
        model = Order
        fields = '__all__'

class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = '__all__'