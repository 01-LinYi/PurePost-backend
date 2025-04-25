from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FeedbackViewSet, FeedbackAdminViewSet

router = DefaultRouter()
router.register(r'forms', FeedbackViewSet, basename='feedback-form')
router.register(r'admin/forms', FeedbackAdminViewSet, basename='admin-feedback-form')
urlpatterns = [
    path('', include(router.urls)),
]
