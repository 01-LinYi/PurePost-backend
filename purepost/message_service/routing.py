from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/messages/<uuid:conv_id>/', consumers.MessagesConsumer.as_asgi()),
]
