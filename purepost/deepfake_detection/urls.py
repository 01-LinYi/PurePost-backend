from django.urls import path
from . import views


urlpatterns = [
    # Post-based endpoints only
    path('posts/<int:post_id>/analysis/',
         views.ImageAnalysisViewSet.as_view({'get': 'get_by_post', 'post': 'create_for_post'}),
         name='post-analysis'),
    
    path('posts/<int:post_id>/analysis/retry/',
         views.ImageAnalysisViewSet.as_view({'post': 'retry_by_post'}),
         name='post-analysis-retry'),
    
    path('posts/<int:post_id>/analysis/cancel/',
         views.ImageAnalysisViewSet.as_view({'post': 'cancel_by_post'}),
         name='post-analysis-cancel'),
    
    path('statistics/',
         views.ImageAnalysisViewSet.as_view({'get': 'statistics'}),
         name='analysis-statistics'),
]