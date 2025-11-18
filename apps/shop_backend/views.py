from django.core.validators import URLValidator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, generics, status, filters
from rest_framework.validators import UniqueValidator
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import *
from .serializers import *

from django.db import transaction
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import yaml
import requests


class ShopViewSet(generics.ListAPIView):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    permission_classes = [permissions.AllowAny]
    http_method_names = ['get']

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'shops__name': ['exact', 'icontains'],  # фильтр по названию мазагина"""
        'shops__id': ['exact'],  # фильтр по id магазина"""
        'name': ['exact', 'icontains']}  # """фильтр по названию категории"""
    ordering_fields = ['name']
    ordering = ['name']


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get']
    parser_classes = [MultiPartParser, FormParser]


class ProductInfoViewSet(ModelViewSet):
    queryset = ProductInfo.objects.all()
    serializer_class = ProductInfoSerializer
    http_method_names = ['get']
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = ProductInfo.objects.select_related('product', 'shop').prefetch_related(
            'product_parameters__parameter')

        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)

        available = self.request.query_params.get('available')
        if available == 'true':
            queryset = queryset.filter(available=True, quantity__gt=0)

        return queryset


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика .Украденый клас обновления,не знал как реализовывать
    """

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # 1. Проверка авторизации
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': 'Log in required'}, status=403)

        # 2. Проверка что пользователь - владелец магазина
        # У вас нет user.type, проверяем через существование магазина
        user_shops = Shop.objects.filter(owner=request.user)
        if not user_shops.exists():
            return Response({'Status': False, 'Error': 'Только для владельцев магазинов'}, status=403)

        # 3. Валидация URL
        url = request.data.get('url')
        if not url:
            return Response({'Status': False, 'Error': 'Не указан URL'}, status=400)

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return Response({'Status': False, 'Error': str(e)}, status=400)

        try:
            # 4. Загрузка YAML
            response = requests.get(url)
            response.raise_for_status()
            data = yaml.safe_load(response.content)

        except Exception as e:
            return Response({'Status': False, 'Error': f'Ошибка загрузки файла: {e}'}, status=400)

        try:
            # 5. Получаем магазин пользователя (первый найденный)
            shop = user_shops.first()

            # ИЛИ: если в YAML указан магазин, ищем его среди магазинов пользователя
            shop_name = data.get('shop')
            if shop_name:
                shop = user_shops.filter(name=shop_name).first()
                if not shop:
                    return Response(
                        {'Status': False, 'Error': f'Магазин "{shop_name}" не найден среди ваших магазинов'},
                        status=403)

            # 6. Обработка категорий
            for category_data in data.get('categories', []):
                category, created = Category.objects.get_or_create(
                    name=category_data['name'],
                    defaults={'name': category_data['name']}
                )
                # Связываем категорию с магазином
                category.shops.add(shop)

            # 7. Деактивация старых товаров магазина
            ProductInfo.objects.filter(shop=shop).update(available=False)

            # 8. Обработка товаров
            for item in data.get('goods', []):
                # Находим категорию товара
                category_id = item.get('category')
                if not category_id:
                    continue

                # Создаем или получаем продукт
                product, created = Product.objects.get_or_create(
                    name=item['name'],
                    category_id=category_id
                )

                # Создаем или обновляем информацию о продукте
                product_info, created = ProductInfo.objects.update_or_create(
                    product=product,
                    shop=shop,
                    defaults={
                        'name': item['name'],  # используем name из вашей модели
                        'price': item['price'],
                        'price_rrc': item['price_rrc'],
                        'quantity': item['quantity'],
                        'available': item.get('quantity', 0) > 0
                    }
                )

                # 9. Обработка параметров
                for param_name, param_value in item.get('parameters', {}).items():
                    parameter, _ = Parameter.objects.get_or_create(name=param_name)

                    # Преобразуем значение в строку
                    if isinstance(param_value, bool):
                        str_value = "Да" if param_value else "Нет"
                    else:
                        str_value = str(param_value)

                    ProductParameter.objects.update_or_create(
                        product_info=product_info,
                        parameter=parameter,
                        defaults={'value': str_value}
                    )

            return Response({
                'Status': True,
                'Message': f'Прайс-лист успешно обновлен для магазина {shop.name}'
            })

        except Exception as e:
            return Response({'Status': False, 'Error': f'Ошибка обработки данных: {str(e)}'}, status=500)
