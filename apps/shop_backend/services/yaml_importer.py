# apps/shop_backend/services/yaml_importer.py
import yaml
from django.db import transaction
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from apps.shop_backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter

User = get_user_model()


class YamlImporter:
    def __init__(self, file_path, owner_username):
        self.file_path = file_path
        try:
            self.owner = User.objects.get(username=owner_username)
        except User.DoesNotExist:
            raise Exception(f"Пользователь {owner_username} не существует!")
        self.shop = None
        self.category_map = {}
        self.parameter_cache = {}

    def load_yaml_data(self):
        """Загружаем данные из YAML файла"""
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)

    def create_or_get_shop(self, shop_name):
        """Создаем или получаем магазин"""
        shop, created = Shop.objects.get_or_create(
            name=shop_name,
            defaults={
                'owner': self.owner,
                'description': f'Магазин {shop_name}',
                'url': f'https://{slugify(shop_name)}.ru'
            }
        )
        return shop

    def create_categories(self, categories_data):
        """Создаем категории и связываем с магазином"""
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'name': cat_data['name']}
            )
            self.category_map[cat_data['id']] = category
            category.shops.add(self.shop)
            if created:
                print(f"Создана категория: {category.name}")

    def get_or_create_parameter(self, param_name):
        """Получаем или создаем параметр"""
        if param_name not in self.parameter_cache:
            parameter, created = Parameter.objects.get_or_create(name=param_name)
            self.parameter_cache[param_name] = parameter
        return self.parameter_cache[param_name]

    def create_product(self, product_data):
        """Создаем продукт и связанные данные"""
        try:
            # Находим категорию по ID из YAML
            category = self.category_map.get(product_data['category'])
            if not category:
                print(f"Категория с ID {product_data['category']} не найдена")
                return False

            # Создаем или получаем продукт
            product, product_created = Product.objects.get_or_create(
                name=product_data['name'],
                category=category,
                defaults={
                    'name': product_data['name'],
                    'category': category
                }
            )

            # Создаем информацию о продукте в магазине
            product_info, info_created = ProductInfo.objects.get_or_create(
                product=product,
                shop=self.shop,
                defaults={
                    'name': product_data['name'],
                    'quantity': product_data.get('quantity', 0),
                    'price': product_data['price'],
                    'price_rrc': product_data['price_rrc'],
                    'available': product_data.get('quantity', 0) > 0
                }
            )

            # Обновляем информацию если продукт уже существует
            if not info_created:
                product_info.quantity = product_data.get('quantity', 0)
                product_info.price = product_data['price']
                product_info.price_rrc = product_data['price_rrc']
                product_info.available = product_data.get('quantity', 0) > 0
                product_info.save()

            # Добавляем параметры
            parameters = product_data.get('parameters', {})
            for param_name, param_value in parameters.items():
                parameter = self.get_or_create_parameter(param_name)

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

            print(f"✓ Создан товар: {product_data['name']}")
            return True

        except Exception as e:
            print(f"✗ Ошибка при создании товара {product_data['name']}: {e}")
            return False

    @transaction.atomic
    def import_data(self):
        """Основная функция импорта"""
        try:
            # Загружаем данные из YAML
            data = self.load_yaml_data()
            print(f"🛒 Загружены данные магазина: {data['shop']}")

            # Создаем магазин
            self.shop = self.create_or_get_shop(data['shop'])
            print(f"🏪 Магазин: {self.shop.name}")

            # Создаем категории
            self.create_categories(data['categories'])
            print(f"📂 Создано категорий: {len(data['categories'])}")

            # Создаем товары
            success_count = 0
            error_count = 0

            print(f"📦 Начинаем импорт {len(data['goods'])} товаров...")

            for product_data in data['goods']:
                if self.create_product(product_data):
                    success_count += 1
                else:
                    error_count += 1

            print(f"✅ Импорт завершен: Успешно - {success_count}, Ошибок - {error_count}")

            return {
                'shop': self.shop.name,
                'categories': len(data['categories']),
                'products_success': success_count,
                'products_errors': error_count,
                'total_products': len(data['goods'])
            }

        except Exception as e:
            print(f"❌ Критическая ошибка импорта: {e}")
            raise e