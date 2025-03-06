import json
import uuid
from asyncio.log import logger

from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework.exceptions import PermissionDenied

from purepost.message_service.models import Message
from purepost.user_service.models import Profile


class MessagesConsumer(AsyncWebsocketConsumer):
    profile: Profile = None  # TODO: update when profile change?
    conv_id: uuid = None
    conv_group_name: str = None

    async def connect(self):
        print(f"MessagesConsumer: Connect method called. User: {self.scope['user']}")
        self.conv_id = self.scope["url_route"]["kwargs"]["conv_id"]
        self.conv_group_name = f"conv_{self.conv_id}"

        # Debug log: Check authenticated user
        print(f"WebSocket connect: Authenticated user: {self.scope['user']}")

        # Check if the user is authenticated (after token authentication)
        if self.scope["user"].is_authenticated:
            # Fetch the Profile of the authenticated user
            try:
                self.profile = await database_sync_to_async(
                    lambda: Profile.objects.select_related("user").get(user=self.scope["user"])
                )()
            except Profile.DoesNotExist:
                raise PermissionDenied("Authenticated user does not have an associated profile.")
        else:
            raise PermissionDenied("User is not authenticated.")

        print("MessagesConsumer: User is authenticated")

        # Join room group
        await self.channel_layer.group_add(self.conv_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, _):
        # Leave room group
        await self.channel_layer.group_discard(self.conv_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data: Any = None, bytes_data: Any = None):
        text_data_json = json.loads(text_data)
        message: str = text_data_json["message"]

        print(f"MessagesConsumer: Received message: {message}")

        # Send message to room group
        await self.channel_layer.group_send(
            self.conv_group_name,
            {
                "type": "chat.message",
                "message": message,
            }
        )

    # Receive message from room group
    async def chat_message(self, event: dict[str, str]):
        message: str = event["message"]

        print(f"MessagesConsumer: Received message from room group: {message}")

        await Message.objects.acreate(
            conversation_id=self.conv_id,
            sender=self.profile,
            content=message)

        print(f"MessagesConsumer: Message saved to database. Sending message to WebSocket.")

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "message": message,
                    "sender": {
                        "id": self.profile.user.id,
                        "username": self.profile.user.username,
                        "name": f"{self.profile.user.first_name} {self.profile.user.last_name}",
                        "avatar": self.profile.avatar.url if self.profile.avatar else None,
                    }
                }
            )
        )
