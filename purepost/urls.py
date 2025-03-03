from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include("purepost.auth_service.urls")),
    path('users/', include('purepost.user_service.urls')),
    path('content/', include('purepost.content_moderation.urls')),
]
