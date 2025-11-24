from typing import Type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import Signal,receiver
from apps.shop_backend.models import User

new_order = Signal()

@receiver(new_order)
def new_order_status(user_id, **kwargs):
    """отправка письма при изменении статуса заказа"""

    user = User.objects.get(id=user_id)

    msg = EmailMultiAlternatives(
        f'Обновление статуса заказа',
        settings.EMAIL_HOST_USER,
        [user.email]

    )
    msg.send()
