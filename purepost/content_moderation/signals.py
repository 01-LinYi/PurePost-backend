from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from .models import Like, Comment, Share, Report, Post
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
def share_notification(sender, instance:Comment, created, **kwargs):
    if created:
        # Send notification to the post owner
        send_notification(
            instance.post.user.user_profile,
            'share',
            f"{instance.user.username} shared your post",
            instance.post
        )


@receiver(post_save, sender=Report)
def report_notification(sender, instance:Report, created, **kwargs):
    # Only send notification if the report status is changed
    if not created and hasattr(instance, '_old_status') and instance.status != instance._old_status:
        post_username = instance.post.user.username if instance.post else instance.post_author_username
        
        # check if the status is "resolved" and action_taken is not None
        if instance.status == "resolved" and instance.action_taken:
            send_notification(
                instance.reporter.user_profile,
                "report",
                f"Your report on {post_username}'s post has been resolved. Action taken: {instance.action_taken}.",
                instance.post
            )
        # handle other statuses
        else:
            send_notification(
                instance.reporter.user_profile,
                "report",
                f"Your report on {post_username}'s post is currently {instance.status.lower()}.",
                instance.post
            )


@receiver(pre_save, sender=Report)
def store_old_status(sender, instance, **kwargs):
    # Only store the old status if the instance is being updated
    if instance.pk:
        old_instance = Report.objects.get(pk=instance.pk)
        # Add a temporary attribute to store the old status
        instance._old_status = old_instance.status


@receiver(post_save, sender=Report)
def fill_post_author_username(sender, instance, created, **kwargs):
    if created and instance.post and instance.post.user:
        instance.post_author_username = instance.post.user.username
        instance.save(update_fields=['post_author_username'])
    if created:
        post_username = instance.post.user.username if instance.post else instance.post_author_username
        send_notification(
            instance.reporter.user_profile,
            "report",
            f"We' ve received your report on {post_username}'s post. It's now under review, and we will take action if necessary.",
            instance.post
        )


@receiver(pre_delete, sender=Post)
def update_report_action_on_post_delete(sender, instance, **kwargs):
    reports = Report.objects.filter(post=instance)
    reports.update(action_taken="Post deleted")
