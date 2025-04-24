from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from purepost import settings
from .models import Notification, NotificationPreference


def send_notification(recipient_profile, notification_type, message, related_object=None):
    """
    Send a notification to a user if they have enabled that notification type
    Args:
        recipient_profile: Profile model instance
        notification_type: str, one of Notification.NOTIFICATION_TYPES
        message: str, notification message
        related_object: Optional model instance related to the notification
    """
    # Check if the user has disabled this notification type
    try:
        preference = NotificationPreference.objects.get(
            profile=recipient_profile,
            notification_type=notification_type
        )
        if not preference.enabled:
            # User has disabled this notification type
            return None
    except NotificationPreference.DoesNotExist:
        # If no preference exists, create one with default (enabled=True)
        NotificationPreference.objects.create(
            profile=recipient_profile,
            notification_type=notification_type,
            enabled=True
        )

    # Create notification in database
    notification = Notification.objects.create(
        recipient=recipient_profile,
        notification_type=notification_type,
        message=message,
        content_type=ContentType.objects.get_for_model(related_object) if related_object else None,
        object_id=str(related_object.id) if related_object else None
    )

    # Prepare notification data
    notification_data = {
        'id': str(notification.id),
        'type': notification_type,
        'message': message,
        'created_at': notification.created_at.isoformat()
    }

    # Send to websocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_{recipient_profile.user.id}",
        {
            'type': 'notification_message',
            'notification': notification_data
        }
    )

    return notification


@shared_task
def send_email_async(subject, to_email, template_name, context, from_email=None):
    from_email = from_email or settings.EMAIL_HOST_USER
    message = render_to_string(template_name, context)
    email = EmailMessage(subject, message, to=to_email, from_email=from_email)
    email.content_subtype = "html"
    email.send()
