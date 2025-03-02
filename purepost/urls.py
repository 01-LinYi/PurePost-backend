from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('messages/', include('purepost.message_service.urls')),
    path('auth/', include("purepost.auth_service.urls")),
    path('users/', include('purepost.user_service.urls')),
]