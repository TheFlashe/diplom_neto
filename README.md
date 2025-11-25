# Дипломный проект профессии «Python-разработчик: расширенный курс»
## Backend-приложение для автоматизации закупок
### Цель дипломного проекта
Создать проект по автоматизации закупок в розничной сети, проработать модели данных, импорт товаров, API views.

Для запуска потребуется :<br>
1. Клонирование репозитория: git clone <https://github.com/TheFlashe/diplom_neto><br>
2. Создание виртуального окружения: python -m venv venv<br>
3. Установка зависимостей: pip install -r requirements.txt<br>

# Реализовано два приложения:
## accounts(регистрация пользователей) и shop_backend(основная логика работы магазина)
# Описание запросов Магазина:
- GET    /api/shops/                    - список магазинов

## Категории  
- GET    /api/categories/               - список категорий
- GET    /api/categories/{id}/          - детали категории

## Товары
- GET    /api/products/                 - список товаров
- GET    /api/products/{id}/            - детали товара

## Информация о товарах
- GET    /api/product_info/             - список товаров с информацией
- GET    /api/product_info/{id}/        - детали товара с информацией

## Корзина
- GET    /api/basket/                   - посмотреть корзину
- POST   /api/basket/                   - добавить один товар
- POST   /api/basket/add_items/         - добавить несколько товаров
- PUT    /api/basket/update_items/      - обновить количество
- DELETE /api/basket/remove_items/      - удалить товары
- POST   /api/basket/clear/             - очистить корзину

## Заказы
- GET    /api/orders/                   - список заказов
- GET    /api/orders/{id}/              - детали заказа
- POST   /api/orders/                   - создать заказ из корзины
- POST   /api/orders/{id}/cancel/       - отменить заказ

## Контакты
- GET    /api/contacts/                 - список контактов
- POST   /api/contacts/                 - создать контакт
- GET    /api/contacts/{id}/            - детали контакта
- PUT    /api/contacts/{id}/            - обновить контакт
- DELETE /api/contacts/{id}/            - удалить контакт

## Партнерское обновление
- POST   /api/partner/update/           - обновить прайс-лист

# Описание запросов для регистрации,сброса пароля и тд.:
## Регистрация и вход
-POST /api/auth/register/ - регистрация нового пользователя
-POST /api/auth/login/ - вход в систему
-POST /api/auth/logout/ - выход из системы
-POST /api/auth/token/refresh/ - обновление JWT токена

## Управление профилем
-GET /api/auth/profile/ - просмотр профиля пользователя
-PUT /api/auth/profile/ - обновление профиля пользователя
-PATCH /api/auth/profile/ - частичное обновление профиля

## Сброс пароля
-PUT /api/auth/change-password/ - изменение пароля пользователя