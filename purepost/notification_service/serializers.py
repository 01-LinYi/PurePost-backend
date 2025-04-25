from rest_framework import serializers
from .models import Notification, NotificationPreference


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


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for NotificationPreference model"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = NotificationPreference
        fields = ['id', 'notification_type', 'notification_type_display', 'enabled', 'updated_at']
        read_only_fields = ['id', 'notification_type_display', 'updated_at']


class NotificationTypeSerializer(serializers.Serializer):
    """Serializer for notification types"""
    value = serializers.CharField()
    display = serializers.CharField()