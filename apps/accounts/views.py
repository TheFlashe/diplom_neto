from django.shortcuts import render
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.core.mail import send_mail, EmailMultiAlternatives
from .models import User
from django.conf import settings
from .serializers import (UserLoginSerializer, UserProfileSerializer, UserRegistrationSerializer,
                          UpdateUserProfileSerializer, ChangePasswordSerializer)


class RegisterView(generics.CreateAPIView):
    """Вью регистрации пользователя"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        try:
            send_mail(subject='Успешная регистрация',
                      message=f'Привет, {user.email}! Вы успешно зарегистрировались в нашем приложении.',
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[user.email],
                      fail_silently=False)
        except Exception as e:
            print(f"Ошибка отправки email: {e}")

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Пользователь успешно зарегистрирован'
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """Вью входа пользователя"""
    serializer_class = UserLoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        login(request, user)
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Пользователь успешно залогинился'
        }, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Просмотр и обновление профиля"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UpdateUserProfileSerializer
        return UserProfileSerializer


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user = self.request.user


        msg = EmailMultiAlternatives(
            f"Пароль измене для {user.email}",
            "Ваш пароль изменен.",
            settings.EMAIL_HOST_USER,
            [user.email]
        )
        msg.send()

        return Response({
            'message': 'Пароль изменен успешно'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """Выход из профиля"""
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({
            'message': 'Выход выполнен успешно!'
        }, status=status.HTTP_200_OK)
    except Exception:
        return Response({
            'error': 'Не верный токен'
        }, status=status.HTTP_400_BAD_REQUEST)
