# scripts/import_yaml.py
import os
import sys
import django

# Добавляем корневую директорию проекта в Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Настраиваем Django - используем config.settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()

    from apps.shop_backend.services.yaml_importer import YamlImporter


    def main():
        # Укажите правильный путь к вашему YAML файлу
        yaml_file_path = 'data/shop_data.yaml'

        # Укажите username существующего пользователя
        owner_username = 'admin'  # замените на вашего пользователя

        try:
            importer = YamlImporter(yaml_file_path, owner_username)
            result = importer.import_data()

            print("\n=== Результаты импорта ===")
            print(f"Магазин: {result['shop']}")
            print(f"Категории: {result['categories']}")
            print(f"Товары: {result['products_success']} из {result['total_products']}")
            print(f"Ошибки: {result['products_errors']}")

        except Exception as e:
            print(f"Ошибка импорта: {e}")


    if __name__ == '__main__':
        main()

except Exception as e:
    print(f"Ошибка настройки Django: {e}")