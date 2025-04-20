from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Like, Comment, Share
from purepost.notification_service.utils import send_notification


@receiver(post_save, sender=Like)
def like_notification(sender, instance, created, **kwargs):
    if created:  # Only send notification for new likes
        send_notification(
            instance.post.user.user_profile,
            'like',
            f"{instance.user.username} liked your post",
            instance.post
        )


@receiver(post_save, sender=Comment)
def comment_notification(sender, instance, created, **kwargs):
    if created:
        # Send notification to the post owner
        send_notification(
            instance.post.user.user_profile,
            'comment',
            f"{instance.user.username} commented on your post",
            instance.post
        )


@receiver(post_save, sender=Share)
def share_notification(sender, instance, created, **kwargs):
    if created:
        # Send notification to the post owner
        send_notification(
            instance.parent.user.user_profile,
            'share',
            f"{instance.user.username} shared your post",
            instance.parent
        )
