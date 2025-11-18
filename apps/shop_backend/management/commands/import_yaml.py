# apps/shop_backend/management/commands/import_yaml.py
import os
import yaml
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from apps.shop_backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter

User = get_user_model()


class Command(BaseCommand):
    help = 'Import products from YAML file'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='data/shop_data.yaml', help='Path to YAML file')
        parser.add_argument('--owner', type=str, required=True, help='Owner username')

    def handle(self, *args, **options):
        file_path = options['file']
        owner_username = options['owner']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'Файл {file_path} не найден!'))
            return

        try:
            importer = YamlImporter(file_path, owner_username)
            result = importer.import_data()

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Успешно импортировано {result['products_success']} товаров "
                    f"в магазин {result['shop']} ({result['categories']} категорий)"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка импорта: {e}'))


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
            # Сначала пытаемся найти существующую категорию
            category = Category.objects.filter(name=cat_data['name']).first()

            if not category:
                # Создаем новую категорию с правильным slug
                slug = slugify(cat_data['name'])
                # Проверяем уникальность slug
                counter = 1
                base_slug = slug
                while Category.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                category = Category.objects.create(
                    name=cat_data['name'],
                    slug=slug
                )
                print(f"Создана категория: {category.name} (slug: {category.slug})")
            else:
                print(f"Найдена существующая категория: {category.name}")

            self.category_map[cat_data['id']] = category
            category.shops.add(self.shop)

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

            # Создаем или получаем продукт с правильным slug
            product = Product.objects.filter(name=product_data['name'], category=category).first()

            if not product:
                slug = slugify(product_data['name'])
                # Проверяем уникальность slug
                counter = 1
                base_slug = slug
                while Product.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                product = Product.objects.create(
                    name=product_data['name'],
                    category=category,
                    slug=slug
                )
                print(f"Создан продукт: {product.name}")
            else:
                print(f"Найден существующий продукт: {product.name}")

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

            print(f"✓ Обработан товар: {product_data['name']}")
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
            print(f"📂 Обработано категорий: {len(data['categories'])}")

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