# Furry/APIs/serializers.py
from rest_framework import serializers
from datetime import datetime, timezone # Make sure this import is present if you use default=timezone.now
from django.contrib.auth.models import User


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



class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        # Remove password2 before creating the user
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class OrderHistorySerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True) # Nested serializer for order items

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'session_key', 'total_amount', 'shipping_cost', 'status', 'payment_status',
            'first_name', 'last_name', 'email', 'phone',
            'address_line_1', 'address_line_2', 'city', 'state', 'zip_code', 'country',
            # Include billing if you want it in the history API
            'billing_first_name', 'billing_last_name', 'billing_email', 'billing_phone',
            'billing_address_line_1', 'billing_address_line_2', 'billing_city', 'billing_state',
            'billing_zip_code', 'billing_country',
            'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['user', 'session_key', 'total_amount', 'shipping_cost', 'status', 'payment_status', 'items', 'created_at', 'updated_at']