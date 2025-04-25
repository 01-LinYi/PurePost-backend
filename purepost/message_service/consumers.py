import json

from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder

from purepost.message_service.models import Message, Conversation
from purepost.user_service.models import Profile


class MessagesConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.conv_group_name = None
        self.conv_id = None
        self.profile = None

    async def connect(self):
        print(f"MessagesConsumer: Connect method called")
        self.conv_id = self.scope["url_route"]["kwargs"]["conv_id"]
        self.conv_group_name = f"conv_{self.conv_id}"

        # Check if the user is authenticated (after token authentication)
        if not self.scope["user"].is_authenticated:
            await self.close(4001, "Unauthorized")

        # Fetch the Profile of the authenticated user
        try:
            self.profile = await database_sync_to_async(
                lambda: Profile.objects.select_related("user").get(user=self.scope["user"])
            )()
        except Profile.DoesNotExist:
            await self.close(4001, "Unauthorized")

        print("MessagesConsumer: User is authenticated")

        # Fetch the conversation and ensure the user is a participant
        try:
            conversation = await Conversation.objects.aget(pk=self.conv_id)
            is_participant = await database_sync_to_async(
                lambda: conversation.participants.filter(user_id=self.profile.user.id).exists()
            )()
            if not is_participant:
                print("MessagesConsumer: User is not part of the conversation")
                await self.close(code=4002)  # User is not part of the conversation
                return
        except Conversation.DoesNotExist:
            print("MessagesConsumer: Conversation does not exist")
            await self.close(code=4001)  # Conversation doesn't exist
            return

        # Join room group
        await self.channel_layer.group_add(self.conv_group_name, self.channel_name)
        await self.accept()

        # Fetch and send the messages
        messages = await database_sync_to_async(
            lambda: [
                {
                    "id": message.id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "sender": {
                        "id": message.sender.user.id,
                        "username": message.sender.user.username,
                        "name": f"{message.sender.user.first_name} {message.sender.user.last_name}",
                        "avatar": message.sender.avatar.url if message.sender.avatar else None
                    }
                }
                for message in
                Message.objects.select_related("sender__user").filter(conversation=conversation).order_by(
                    "-created_at").reverse()
            ]
        )()

        await self.send(text_data=json.dumps(messages, cls=DjangoJSONEncoder))

    async def disconnect(self, _):
        # Leave room group
        await self.channel_layer.group_discard(self.conv_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data: Any = None, bytes_data: Any = None):
        text_data_json = json.loads(text_data)
        message: str = text_data_json["message"]

        print(f"MessagesConsumer: Received message: {message}")

        msg_obj = await Message.objects.acreate(
            conversation_id=self.conv_id,
            sender=self.profile,
            content=message)

        print(f"MessagesConsumer: Message saved to database. Sending message to WebSocket.")

        # Send message to room group
        await self.channel_layer.group_send(
            self.conv_group_name,
            {
                "type": "chat.message",
                "id": msg_obj.id,
                "content": message,
                "created_at": msg_obj.created_at.isoformat(),
                "sender": {
                    "id": self.profile.user.id,
                    "username": self.profile.user.username,
                    "name": f"{self.profile.user.first_name} {self.profile.user.last_name}",
                    "avatar": self.profile.avatar.url if self.profile.avatar else None,
                }
            }
        )

    # Receive message from room group
    async def chat_message(self, event: dict[str, Any]):
        message = event["content"]
        sender = event["sender"]
        created_at = event["created_at"]
        message_id = event["id"]

        print(f"MessagesConsumer: Received message from room group: {message}")

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                [
                    {
                        "id": message_id,
                        "content": message,
                        "created_at": created_at,
                        "sender": sender
                    }
                ],
                cls=DjangoJSONEncoder
            )
        )
