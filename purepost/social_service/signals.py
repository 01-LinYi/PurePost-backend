from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Follow
from purepost.notification_service.utils import send_notification


@receiver(post_save, sender=Follow)
def follow_notification(sender, instance, created, **kwargs):
    if created:  # Only send notification for new likes
        send_notification(
            instance.following.user_profile,
            'follow',
            f"{instance.follower.username} follow you",
            None
        )
