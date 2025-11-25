from rest_framework import serializers
from .models import Shop, Category, Product, ProductInfo, ProductParameter, Parameter, Order, OrderItem, Contact


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'description', 'url', 'owner', 'created_at')


class CategorySerializer(serializers.ModelSerializer):
    shops = ShopSerializer(many=True, read_only=True)
    shops = ShopSerializer(many=True, read_only=True)
    shops = ShopSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'shops')


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'category_name', 'image')


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)

    class Meta:
        model = ProductParameter
        fields = ('parameter_name', 'value')


class ProductInfoSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    parameters = ProductParameterSerializer(many=True, read_only=True, source='product_parameters')

    class Meta:
        model = ProductInfo
        fields = (
            'id', 'name', 'description', 'quantity', 'price', 'price_rrc',
            'available', 'product', 'product_name', 'shop', 'shop_name',
            'parameters', 'created_at'
        )


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ('id', 'name')


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'product', 'product_name', 'shop', 'shop_name', 'quantity', 'price', 'total_price')
        read_only_fields = ('id', 'order')

    def get_price(self, obj):
        try:
            product_info = ProductInfo.objects.get(product=obj.product, shop=obj.shop, available=True
                                                   )
            return product_info.price
        except ProductInfo.DoesNotExist:
            return 0

    def get_total_price(self, obj):
        price = self.get_price(obj)
        return price * obj.quantity

    def validate(self, data):
        # Проверка доступности товара при создании/обновлении
        product = data.get('product')
        shop = data.get('shop')
        quantity = data.get('quantity', 1)

        if product and shop:
            try:
                product_info = ProductInfo.objects.get(product=product, shop=shop)
                if not product_info.available:
                    raise serializers.ValidationError("Товар недоступен")
                if product_info.quantity < quantity:
                    raise serializers.ValidationError(f"Недостаточно товара. Доступно: {product_info.quantity}")
            except ProductInfo.DoesNotExist:
                raise serializers.ValidationError("Товар не найден в указанном магазине")

        return data


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'user', 'dt', 'status', 'items', 'total_amount')

    def get_total_amount(self, obj):
        total = 0
        for item in obj.items.all():
            try:

                product_info = ProductInfo.objects.get(
                    product=item.product,
                    shop=item.shop,
                    available=True
                )
                total += item.quantity * product_info.price
            except ProductInfo.DoesNotExist:
                # Если товар не найден, пропускаем
                continue
        return total


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'type', 'user', 'value')
