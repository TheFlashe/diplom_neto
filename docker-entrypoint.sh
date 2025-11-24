#!/bin/bash

# Ожидание доступности PostgreSQL с таймаутом
echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
timeout=30
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
  timeout=$((timeout-1))
  if [ $timeout -eq 0 ]; then
    echo "Timeout waiting for PostgreSQL"
    exit 1
  fi
done
echo "PostgreSQL started"

# Применение миграций
echo "Applying migrations..."
python manage.py migrate

# Создание суперпользователя
echo "Creating superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(email='admin@example.com').exists():
    User.objects.create_superuser('admin@example.com', 'admin123')
    print('Superuser created: admin@example.com / admin123')
else:
    print('Superuser already exists')
"

# Запуск сервера
echo "Starting Django server..."
exec "$@"