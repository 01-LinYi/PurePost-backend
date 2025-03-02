from django.urls import path
from .views import PostViewSet, FolderViewSet, SavedPostViewSet

urlpatterns = [
    path('posts/', PostViewSet.as_view(), name='post'),
    path('folders/', FolderViewSet.as_view(), name='folder'),
    path('saved-posts/', SavedPostViewSet.as_view(), name='savedpost'),
]
