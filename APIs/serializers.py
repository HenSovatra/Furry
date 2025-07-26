# Furry/APIs/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from Admin.models import Order, OrderItem 
from PetStore.models import Product as PetStoreProduct, Category, Cart, CartItem, Order, OrderItem, Feedback, FeedbackImage, Post
from Admin.models import Customer, Billing
from django.db import transaction 
from Admin.models import Customer 
class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetStoreProduct
        fields = ['id', 'name', 'original_price', 'discounted_price', 'stock', 'image']

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = OrderItem
        fields = ['id','product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True)

    class Meta:
        model = Order
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductAdminSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category', 
        write_only=True    
    )

    created_at = serializers.DateTimeField(format="%d/%m/%y", read_only=True) 

    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = PetStoreProduct
        fields = '__all__' 

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
    username = serializers.CharField(write_only=True, required=True, max_length=150)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}) 
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=False, max_length=100)
    last_name = serializers.CharField(required=False, max_length=100)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    address = serializers.CharField(required=False, allow_blank=True, style={'base_template': 'textarea.html'})


    class Meta:
        model = Customer 
        fields = [
            'username', 'password', 'password2', 
            'email', 'first_name', 'last_name', 'phone_number', 'address' 
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "This username is already taken."})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        return data

    def validate_email(self, value):
        """
        Check if a Customer with this email already exists.
        This specifically checks the Customer profile's email field.
        """
        if Customer.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email address is already in use by another customer.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            password = validated_data.pop('password')
            username = validated_data.pop('username')
            password2 = validated_data.pop('password2')
            user = User.objects.create_user(
                username=username,
                email=validated_data['email'], 
                password=password
            )
            customer = Customer.objects.create(user=user, **validated_data)
            return user

    
class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    class Meta:
        model = OrderItem
        fields = '__all__' 

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


class OrderHistorySerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'session_key', 'total_amount', 'shipping_cost', 'status', 'payment_status',
            'first_name', 'last_name', 'email', 'phone',
            'address_line_1', 'address_line_2', 'city', 'state', 'zip_code', 'country',
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
    
class FeedbackImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackImage
        fields = ['image'] # Only need the image URL for display in the API

# Serializer for Feedback objects, including nested images
class FeedbackSerializer(serializers.ModelSerializer):
    # 'images' here refers to the related_name='images' on the ForeignKey in FeedbackImage model
    images = FeedbackImageSerializer(many=True, read_only=True)
    # Custom field to display username or email
    user_display = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        # Fields to include in the API response for Feedback objects
        fields = ['id', 'user_display', 'email', 'subject', 'message', 'images', 'submitted_at']
        # These fields are read-only and won't be expected in API input
        read_only_fields = ['id', 'user_display', 'submitted_at']

    def get_user_display(self, obj):
        # Method to determine how the user is displayed
        if obj.user:
            return obj.user.username # If a user is linked, show their username
        return obj.email or 'Anonymous'

class PostSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    image = serializers.ImageField()


    class Meta:
        model = Post
        fields = ['id', 'title', 'image', 'author', 'content',
                  'short_description', 'category','category_id', 'published_date',
                  'updated_at', 'is_published']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
