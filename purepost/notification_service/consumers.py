import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder

from purepost.user_service.models import Profile
from .models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.profile = None
        self.notification_group = None

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close(4001, "Unauthorized")
            return

        # Fetch the Profile of the authenticated user
        try:
            self.profile = await database_sync_to_async(
                lambda: Profile.objects.select_related("user").get(user=self.scope["user"])
            )()
        except Profile.DoesNotExist:
            await self.close(4001, "Unauthorized")

        # Create a user-specific notification group
        self.notification_group = f"notifications_{self.profile.user.id}"

        # Join user's notification group
        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name
        )

        await self.accept()

        # Send unread notifications on connect
        await self.send_unread_notifications()

    async def disconnect(self, close_code):
        if hasattr(self, 'notification_group'):
            await self.channel_layer.group_discard(
                self.notification_group,
                self.channel_name
            )

    @database_sync_to_async
    def get_unread_notifications(self):
        return list(Notification.objects.filter(
            recipient=self.profile,
            is_read=False
        ).values('id', 'message', 'notification_type', 'created_at'))

    async def send_unread_notifications(self):
        notifications = await self.get_unread_notifications()
        if notifications:
            await self.send(text_data=json.dumps({
                'type': 'unread_notifications',
                'notifications': notifications
            }, cls=DjangoJSONEncoder))

    async def notification_message(self, event):
        """Handle incoming notifications"""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }, cls=DjangoJSONEncoder))
