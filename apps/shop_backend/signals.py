from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.dispatch import Signal, receiver
from apps.shop_backend.models import User

order_change_status = Signal()


@receiver(order_change_status)
def send_order_status_email(user_id, order_id, status, **kwargs):
    """отправка письма при изменении статуса заказа"""
    try:
        user = User.objects.get(id=user_id)

        send_mail(
            subject=f'Статус заказ {order_id} изменен',
            message=f'Статус вашего заказа {order_id} измене на: {status}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
                    )
    except Exception as e:
        print(f'Email error: {e}')




