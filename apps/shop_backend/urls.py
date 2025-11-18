from rest_framework.routers import DefaultRouter
from django.urls import path
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'product_info', views.ProductInfoViewSet)

urlpatterns = [
    path('shop/', views.ShopViewSet.as_view(), name='shop'),





] + router.urls
