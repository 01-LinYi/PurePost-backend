from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer, NotificationListSerializer


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
