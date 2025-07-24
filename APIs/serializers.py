# Furry/APIs/serializers.py
from rest_framework import serializers
from datetime import datetime, timezone # Make sure this import is present if you use default=timezone.now
from django.contrib.auth.models import User
from Admin.models import Order, OrderItem 
from django.db.models import Sum
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
    
    # Add fields for the Customer profile
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone_number', 'address' # Include new fields
        )
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return data

    def create(self, validated_data):
        # Pop fields for Customer model before creating the User
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        phone_number = validated_data.pop('phone_number', '')
        address = validated_data.pop('address', '')
        
        # Remove password2 before creating the user
        validated_data.pop('password2')
        
        # Create the User
        user = User.objects.create_user(**validated_data)

        # Create the Customer profile linked to the newly created User
        Customer.objects.create(
            user=user, # Link the User instance
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            address=address
        )
        return user # Return the user instance
    
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__' # Or specify the fields you need, e.g., ['product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    # This is the key part: define a field to include nested order items
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


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


class RegisteredCustomerSerializer(serializers.ModelSerializer):
    registration_date = serializers.DateTimeField(source='date_joined', format="%Y-%m-%d", read_only=True)
    total_products_bought = serializers.SerializerMethodField()
    billing_address = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'registration_date', 'billing_address', 'total_products_bought']

    def get_total_products_bought(self, user):
        orders = Order.objects.filter(user=user)
        return sum(item.quantity for order in orders for item in order.items.all())

    def get_billing_address(self, user):
        latest_order = Order.objects.filter(user=user).order_by('-created_at').first()
        if latest_order:
            return {
                "line1": latest_order.billing_address_line_1,
                "city": latest_order.billing_city,
                "state": latest_order.billing_state,
                "country": latest_order.billing_country,
            }
        return None
    
