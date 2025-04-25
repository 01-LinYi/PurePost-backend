from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationPreferenceSerializer,
    NotificationTypeSerializer
)


class NotificationListView(APIView):
    """View to list all notifications for the authenticated user"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """Get all notifications for the authenticated user"""
        notifications = Notification.objects.filter(recipient=request.user.user_profile)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class MarkNotificationsReadView(APIView):
    """View to mark multiple notifications as read"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request):
        """Mark a list of notifications as read"""
        serializer = NotificationListSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        notification_ids = serializer.validated_data['notification_ids']

        # Update only notifications that belong to the current user
        updated_count = Notification.objects.filter(
            id__in=notification_ids,
            recipient=request.user.user_profile,
            is_read=False
        ).update(is_read=True)

        return Response({
            'message': f'{updated_count} notifications marked as read',
            'updated_count': updated_count
        })


class DeleteNotificationsView(APIView):
    """View to permanently delete multiple notifications"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request):
        """Delete a list of notifications"""
        serializer = NotificationListSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        notification_ids = serializer.validated_data['notification_ids']

        # Delete only notifications that belong to the current user
        deleted_count, _ = Notification.objects.filter(
            id__in=notification_ids,
            recipient=request.user.user_profile
        ).delete()

        return Response({
            'message': f'{deleted_count} notifications deleted',
            'deleted_count': deleted_count
        })


class NotificationTypesView(APIView):
    """View to list all available notification types"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """Get all available notification types"""
        notification_types = [
            {'value': key, 'display': value}
            for key, value in dict(Notification.NOTIFICATION_TYPES).items()
        ]
        serializer = NotificationTypeSerializer(notification_types, many=True)
        return Response(serializer.data)


class NotificationPreferenceListView(APIView):
    """View to list and manage notification preferences for the authenticated user"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        """Get all notification preferences for the authenticated user"""
        # Get existing preferences
        preferences = NotificationPreference.objects.filter(profile=request.user.user_profile)

        # Create any missing preferences with default values
        existing_types = set(pref.notification_type for pref in preferences)
        all_types = dict(Notification.NOTIFICATION_TYPES).keys()

        # Create missing preferences
        new_preferences = []
        for notification_type in all_types:
            if notification_type not in existing_types:
                new_pref = NotificationPreference.objects.create(
                    profile=request.user.user_profile,
                    notification_type=notification_type,
                    enabled=True  # Default to enabled
                )
                new_preferences.append(new_pref)

        # Combine existing and new preferences
        all_preferences = list(preferences) + new_preferences
        serializer = NotificationPreferenceSerializer(all_preferences, many=True)
        return Response(serializer.data)


class NotificationPreferenceDetailView(APIView):
    """View to update a specific notification preference"""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def put(request, notification_type):
        """Update a specific notification preference"""
        # Validate notification type
        valid_types = dict(Notification.NOTIFICATION_TYPES).keys()
        if notification_type not in valid_types:
            return Response(
                {'error': f'Invalid notification type. Valid types are: {list(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create the preference
        preference, created = NotificationPreference.objects.get_or_create(
            profile=request.user.user_profile,
            notification_type=notification_type,
            defaults={'enabled': True}
        )

        # Update the preference
        serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
