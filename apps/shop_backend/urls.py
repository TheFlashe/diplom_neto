from rest_framework.routers import DefaultRouter

from .views import ShopViewSet

router = DefaultRouter()
router.register(r'shops', ShopViewSet)

urlpatterns = router.urls
