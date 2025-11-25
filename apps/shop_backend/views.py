import requests
import yaml
from django.core.validators import URLValidator
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Category, Contact, Order, OrderItem, Parameter, Product, ProductInfo, ProductParameter, Shop
from .serializers import (
    CategorySerializer,
    ContactSerializer,
    OrderItemSerializer,
    OrderSerializer,
    ProductInfoSerializer,
    ProductSerializer,
    ShopSerializer,
)
from .signals import order_change_status


class ShopViewSet(ModelViewSet):
    """Вью магазина"""

    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ["get"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class CategoryViewSet(ModelViewSet):
    """Вью категорий"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    permission_classes = [permissions.AllowAny]
    http_method_names = ["get"]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        "shops__name": ["exact", "icontains"],  # фильтр по названию мазагина"""
        "shops__id": ["exact"],  # фильтр по id магазина"""
        "name": ["exact", "icontains"],
    }  # """фильтр по названию категории"""
    ordering_fields = ["name"]
    ordering = ["name"]


class ProductViewSet(ModelViewSet):
    """Вью продуктов"""

    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ["get"]
    parser_classes = [MultiPartParser, FormParser]


class ProductInfoViewSet(ModelViewSet):
    """Вью деталей продуктов"""

    queryset = ProductInfo.objects.all()
    serializer_class = ProductInfoSerializer
    http_method_names = ["get"]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = ProductInfo.objects.select_related("product", "shop").prefetch_related(
            "product_parameters__parameter"
        )

        shop_id = self.request.query_params.get("shop_id")
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)

        available = self.request.query_params.get("available")
        if available == "true":
            queryset = queryset.filter(available=True, quantity__gt=0)

        return queryset


class BasketViewSet(ModelViewSet):
    """Вью корзины"""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user, status="basket")

    def list(self, request):
        """корзина пользователя"""
        basket, created = Order.objects.get_or_create(user=request.user, status="basket")
        serializer = self.get_serializer(basket)
        return Response(serializer.data)

    def create(self, request):
        """добавляем товар в корзину"""
        product_id = request.data.get("product_id")
        shop_id = request.data.get("shop_id")
        quantity = request.data.get("quantity", 1)

        if not all([product_id, shop_id]):
            return Response(
                {"error": "Необходимо указать product_id и shop_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        basket, created = Order.objects.get_or_create(user=request.user, status="basket")

        try:
            product = Product.objects.get(id=product_id)
            shop = Shop.objects.get(id=shop_id)

            # Проверяем доступность товара
            product_info = ProductInfo.objects.filter(product=product, shop=shop, available=True).first()

            if not product_info:
                return Response(
                    {"error": "Товар недоступен в указанном магазине"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if product_info.quantity < quantity:
                return Response(
                    {"error": f"Недостаточно товара. Доступно: {product_info.quantity}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Создаем или обновляем позицию в корзине
            order_item, created = OrderItem.objects.get_or_create(
                order=basket,
                product=product,
                shop=shop,
                defaults={"quantity": quantity},
            )

            if not created:
                order_item.quantity += quantity
                order_item.save()
                action = "updated"
            else:
                action = "created"

            serializer = OrderItemSerializer(order_item)
            return Response(
                {"action": action, "item": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        except (Product.DoesNotExist, Shop.DoesNotExist):
            return Response(
                {"error": "Товар или магазин не найдены"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def add_items(self, request):

        items_data = request.data.get("items", [])
        if not items_data:
            return Response(
                {"error": "Не указаны товары для добавления"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        basket, created = Order.objects.get_or_create(user=request.user, status="basket")

        added_count = 0
        errors = []

        for item_data in items_data:
            product_id = item_data.get("product_id")
            shop_id = item_data.get("shop_id")
            quantity = item_data.get("quantity", 1)

            if not all([product_id, shop_id]):
                errors.append("Для каждого товара product_id и shop_id")
                continue

            try:
                product = Product.objects.get(id=product_id)
                shop = Shop.objects.get(id=shop_id)

                # Проверяем доступность товара
                product_info = ProductInfo.objects.filter(product=product, shop=shop, available=True).first()

                if not product_info:
                    errors.append(f"Товар {product.name} недоступен в магазине {shop.name}")
                    continue

                if product_info.quantity < quantity:
                    errors.append(f"Недостаточно товара {product.name}. Доступно: {product_info.quantity}")
                    continue

                # Создаем или обновляем позицию в корзине
                order_item, created = OrderItem.objects.get_or_create(
                    order=basket,
                    product=product,
                    shop=shop,
                    defaults={"quantity": quantity},
                )

                if not created:
                    order_item.quantity += quantity
                    order_item.save()

                added_count += 1

            except (Product.DoesNotExist, Shop.DoesNotExist) as e:
                errors.append(f"Товар или магазин не найдены: {e}")
                continue

        response_data = {"added_count": added_count, "basket_id": basket.id}

        if errors:
            response_data["errors"] = errors
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)

        return Response(response_data)

    @action(detail=False, methods=["put"])
    def update_items(self, request):
        """изменяем кол-во товара в корзине"""
        items_data = request.data.get("items", [])
        if not items_data:
            return Response(
                {"error": "Не указаны товары для обновления"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            basket = Order.objects.get(user=request.user, status="basket")
        except Order.DoesNotExist:
            return Response({"error": "Корзина не найдена"}, status=status.HTTP_404_NOT_FOUND)

        updated_count = 0
        errors = []

        for item_data in items_data:
            item_id = item_data.get("id")
            quantity = item_data.get("quantity")

            if not all([item_id, quantity]):
                errors.append("Для обновления id и quantity")
                continue

            if quantity <= 0:
                errors.append(f"Количество должно быть положительным для позиции {item_id}")
                continue

            try:
                order_item = OrderItem.objects.get(id=item_id, order=basket)

                # Проверяем доступное количество
                product_info = ProductInfo.objects.filter(product=order_item.product, shop=order_item.shop).first()

                if product_info and quantity <= product_info.quantity:
                    order_item.quantity = quantity
                    order_item.save()
                    updated_count += 1
                else:
                    errors.append(f"Недостаточно товара {order_item.product.name}")

            except OrderItem.DoesNotExist:
                errors.append(f"Позиция с id {item_id} не найдена в корзине")

        response_data = {"updated_count": updated_count}

        if errors:
            response_data["errors"] = errors
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)

        return Response(response_data)

    @action(detail=False, methods=["delete"])
    def remove_items(self, request):
        """удалить корзину"""
        item_ids = request.data.get("items", [])
        if not item_ids:
            return Response(
                {"error": "Не указаны товары для удаления"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            basket = Order.objects.get(user=request.user, status="basket")
        except Order.DoesNotExist:
            return Response({"error": "Корзина не найдена"}, status=status.HTTP_404_NOT_FOUND)

        deleted_count, _ = OrderItem.objects.filter(order=basket, id__in=item_ids).delete()

        return Response({"deleted_count": deleted_count})

    @action(detail=False, methods=["post"])
    def clear(self, request):
        """очистить корзину"""
        try:
            basket = Order.objects.get(user=request.user, status="basket")
            deleted_count, _ = basket.items.all().delete()
            return Response({"deleted_count": deleted_count})
        except Order.DoesNotExist:
            return Response({"error": "Корзина не найдена"}, status=status.HTTP_404_NOT_FOUND)


class OrderViewSet(ModelViewSet):
    """Управление заказами"""

    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).exclude(status="basket")

    def _send_status_notification(self, order, status):
        """Вспомогательный метод для отправки уведомлений"""
        try:
            order_change_status.send(
                sender=self.__class__,
                user_id=order.user.id,
                order_id=order.id,
                status=status,
            )
        except Exception as e:
            print(f"Notification error: {e}")

    def create(self, request):
        """создать заказ"""
        try:
            basket = Order.objects.get(user=request.user, status="basket")
        except Order.DoesNotExist:
            return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

        if not basket.items.exists():
            return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем доступность всех товаров
        errors = []
        for item in basket.items.all():
            try:
                product_info = ProductInfo.objects.get(product=item.product, shop=item.shop)

                if not product_info.available:
                    errors.append(f"Товар {item.product.name} недоступен в магазине {item.shop.name}")
                elif product_info.quantity < item.quantity:
                    errors.append(f"Недостаточно товара {item.product.name}. Доступно: {product_info.quantity}")

            except ProductInfo.DoesNotExist:
                errors.append(f"Товар {item.product.name} не найден в магазине {item.shop.name}")

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        # Меняем статус корзины на 'new'
        basket.status = "new"
        basket.save()

        # Отправляем уведомление о создании заказа
        self._send_status_notification(basket, "new")

        serializer = self.get_serializer(basket)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"])
    def update_status(self, request, pk=None):
        """Изменение статуса заказа"""
        order = self.get_object()
        new_status = request.data.get("status")

        valid_statuses = [
            "new",
            "confirmed",
            "assembled",
            "sent",
            "delivered",
            "canceled",
        ]
        if not new_status or new_status not in valid_statuses:
            return Response(
                {"error": f'Недопустимый статус. Допустимые: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        order.save()

        # Отправляем уведомление об изменении статуса
        self._send_status_notification(order, new_status)

        return Response(
            {
                "message": f"Статус заказа изменен на: {new_status}",
                "order_id": order.id,
                "status": new_status,
            }
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """отменить заказ"""
        order = self.get_object()
        if order.status not in ["delivered", "canceled"]:
            order.status = "canceled"
            order.save()

            # Отправляем уведомление об отмене заказа
            self._send_status_notification(order, "canceled")

            return Response({"status": "Заказ отменен"})
        else:
            return Response(
                {"error": "Невозможно отменить доставленный или уже отмененный заказ"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ContactViewSet(ModelViewSet):
    """профиль пользователя"""

    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PartnerUpdate(APIView):
    """обновить прайс"""

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        # 1. Проверка авторизации
        if not request.user.is_authenticated:
            return Response({"Status": False, "Error": "Log in required"}, status=403)

        # 2. Проверка что пользователь - владелец магазина
        # У вас нет user.type, проверяем через существование магазина
        user_shops = Shop.objects.filter(owner=request.user)
        if not user_shops.exists():
            return Response(
                {"Status": False, "Error": "Только для владельцев магазинов"},
                status=403,
            )

        # 3. Валидация URL
        url = request.data.get("url")
        if not url:
            return Response({"Status": False, "Error": "Не указан URL"}, status=400)

        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return Response({"Status": False, "Error": str(e)}, status=400)

        try:
            # 4. Загрузка YAML
            response = requests.get(url)
            response.raise_for_status()
            data = yaml.safe_load(response.content)

        except Exception as e:
            return Response({"Status": False, "Error": f"Ошибка загрузки файла: {e}"}, status=400)

        try:
            # 5. Получаем магазин пользователя (первый найденный)
            shop = user_shops.first()

            # ИЛИ: если в YAML указан магазин, ищем его среди магазинов пользователя
            shop_name = data.get("shop")
            if shop_name:
                shop = user_shops.filter(name=shop_name).first()
                if not shop:
                    return Response(
                        {
                            "Status": False,
                            "Error": f'Магазин "{shop_name}" не найден среди ваших магазинов',
                        },
                        status=403,
                    )

            # 6. Обработка категорий
            for category_data in data.get("categories", []):
                category, created = Category.objects.get_or_create(
                    name=category_data["name"], defaults={"name": category_data["name"]}
                )
                # Связываем категорию с магазином
                category.shops.add(shop)

            # 7. Деактивация старых товаров магазина
            ProductInfo.objects.filter(shop=shop).update(available=False)

            # 8. Обработка товаров
            for item in data.get("goods", []):
                # Находим категорию товара
                category_id = item.get("category")
                if not category_id:
                    continue

                # Создаем или получаем продукт
                product, created = Product.objects.get_or_create(name=item["name"], category_id=category_id)

                # Создаем или обновляем информацию о продукте
                product_info, created = ProductInfo.objects.update_or_create(
                    product=product,
                    shop=shop,
                    defaults={
                        "name": item["name"],  # используем name из вашей модели
                        "price": item["price"],
                        "price_rrc": item["price_rrc"],
                        "quantity": item["quantity"],
                        "available": item.get("quantity", 0) > 0,
                    },
                )

                # 9. Обработка параметров
                for param_name, param_value in item.get("parameters", {}).items():
                    parameter, _ = Parameter.objects.get_or_create(name=param_name)

                    # Преобразуем значение в строку
                    if isinstance(param_value, bool):
                        str_value = "Да" if param_value else "Нет"
                    else:
                        str_value = str(param_value)

                    ProductParameter.objects.update_or_create(
                        product_info=product_info,
                        parameter=parameter,
                        defaults={"value": str_value},
                    )

            return Response(
                {
                    "Status": True,
                    "Message": f"Прайс-лист успешно обновлен для магазина {shop.name}",
                }
            )

        except Exception as e:
            return Response(
                {"Status": False, "Error": f"Ошибка обработки данных: {str(e)}"},
                status=500,
            )
