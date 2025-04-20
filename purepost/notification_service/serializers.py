from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'notification_type', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'recipient', 'notification_type', 'message', 'created_at']


class NotificationListSerializer(serializers.Serializer):
    """Serializer for handling lists of notification IDs"""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of notification IDs to process"
    )