from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import PostViewSet, FolderViewSet, SavedPostViewSet, PostInteractionViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet)
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'saved-posts', SavedPostViewSet, basename='saved-post')

urlpatterns = [
    path('', include(router.urls)),
    path('posts/<int:pk>/like/', PostViewSet.as_view({'post': 'like'}), name='post-like'),
    path('posts/<int:pk>/unlike/', PostViewSet.as_view({'post': 'unlike'}), name='post-unlike'),
    path('posts/<int:pk>/share/', PostViewSet.as_view({'post': 'share'}), name='post-share'),
    path('posts/<int:pk>/comment/', PostViewSet.as_view({'post': 'comment'}), name='post-comment'),
    path('posts/<int:pk>/delete-comment/', PostViewSet.as_view({'delete': 'delete_comment'}), name='post-delete-comment'),
    path('posts/<int:pk>/interactions/likes/', PostInteractionViewSet.as_view({'get': 'list_likes'}), name='post-likes'),
    path('posts/<int:pk>/interactions/shares/', PostInteractionViewSet.as_view({'get': 'list_shares'}), name='post-shares'),
    path('posts/<int:pk>/interactions/comments/', PostInteractionViewSet.as_view({'get': 'list_comments'}), name='post-comments'),
]
