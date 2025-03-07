from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PostViewSet, FolderViewSet, SavedPostViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet)
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'saved-posts', SavedPostViewSet, basename='saved-post')

urlpatterns = [
    path('', include(router.urls)),
]
