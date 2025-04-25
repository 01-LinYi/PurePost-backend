from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('messages/', include('purepost.message_service.urls')),
    path('social/', include('purepost.social_service.urls')),
    path('auth/', include("purepost.auth_service.urls")),
    path('users/', include('purepost.user_service.urls')),
    path('content/', include('purepost.content_moderation.urls')),
    path('deepfake/', include('purepost.deepfake_detection.urls')),
    path('notifications/', include('purepost.notification_service.urls')),
]
