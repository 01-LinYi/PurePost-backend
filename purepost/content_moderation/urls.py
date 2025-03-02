'''
from django.urls import path
from .views import PostViewSet, FolderViewSet, SavedPostViewSet

urlpatterns = [
    path('posts/', PostViewSet.as_view(), name='post'),
    path('folders/', FolderViewSet.as_view(), name='folder'),
    path('saved-posts/', SavedPostViewSet.as_view(), name='savedpost'),
]
'''

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet, FolderViewSet, SavedPostViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'saved-posts', SavedPostViewSet, basename='savedpost')

urlpatterns = [
    path('api/', include(router.urls)),  # Ensure prefix is correctly set
]

