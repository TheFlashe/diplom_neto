from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"shops", views.ShopViewSet, basename="shop")
router.register(r"categories", views.CategoryViewSet, basename="categories")
router.register(r"products", views.ProductViewSet, basename="products")
router.register(r"product_info", views.ProductInfoViewSet, basename="product_info")
router.register(r"basket", views.BasketViewSet, basename="basket")
router.register(r"orders", views.OrderViewSet, basename="order")
router.register(r"contacts", views.ContactViewSet, basename="contact")

urlpatterns = [
    path("partner/update/", views.PartnerUpdate.as_view(), name="partner-update"),
] + router.urls
