from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Follow(models.Model):
    class Meta:
        unique_together = (('follower', 'following'),)
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['following']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Follow'
        verbose_name_plural = 'Follows'

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_relations',
        help_text="User who follows"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower_relations',
        help_text="User being followed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(
        default=True, help_text="Whether the follow relationship is active")

    def __str__(self):
        status = "follows" if self.is_active else "unfollowed"
        return f"{self.follower.username} {status} {self.following.username}"

    @classmethod
    def follow(cls, follower, following):
        """Create a follow relationship or activate an existing one"""
        if follower == following:
            raise ValueError("Users cannot follow themselves")

        obj, created = cls.objects.get_or_create(
            follower=follower,
            following=following,
            defaults={'is_active': True}
        )

        if not created and not obj.is_active:
            obj.is_active = True
            obj.save(update_fields=['is_active', 'updated_at'])

        return obj, created

    @classmethod
    def unfollow(cls, follower, following):
        """Deactivate a follow relationship"""
        try:
            follow = cls.objects.get(follower=follower, following=following)
            if follow.is_active:
                follow.is_active = False
                follow.save(update_fields=['is_active', 'updated_at'])
                return True
            return False
        except cls.DoesNotExist:
            return False

    @staticmethod
    def is_following(follower, following):
        """Check if a user is following another user"""
        return Follow.objects.filter(
            follower=follower,
            following=following,
            is_active=True
        ).exists()

    @staticmethod
    def get_follower_count(user):
        """Get the count of active followers for a user"""
        return Follow.objects.filter(following=user, is_active=True).count()

    @staticmethod
    def get_following_count(user):
        """Get the count of users a user is actively following"""
        return Follow.objects.filter(follower=user, is_active=True).count()


class Block(models.Model):
    class Meta:
        unique_together = (('blocker', 'blocked'),)
        indexes = [
            models.Index(fields=['blocker']),
            models.Index(fields=['blocked']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Block'
        verbose_name_plural = 'Blocks'

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocking_relations',
        help_text="User who blocks"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocker_relations',
        help_text="User being blocked"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True,
                              help_text="Optional reason for blocking")

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

    @classmethod
    def block_user(cls, blocker, blocked, reason=None):
        """Block a user"""
        if blocker == blocked:
            raise ValueError("Users cannot block themselves")

        Follow.unfollow(blocker, blocked)
        Follow.unfollow(blocked, blocker)

        obj, created = cls.objects.get_or_create(
            blocker=blocker,
            blocked=blocked,
            defaults={'reason': reason}
        )

        if not created and reason:
            obj.reason = reason
            obj.save(update_fields=['reason'])

        return obj, created

    @classmethod
    def unblock_user(cls, blocker, blocked):
        """Unblock a user"""
        try:
            block = cls.objects.get(blocker=blocker, blocked=blocked)
            block.delete()
            return True
        except cls.DoesNotExist:
            return False

    @staticmethod
    def is_blocked(blocker, blocked):
        """Check if a user has blocked another user"""
        return Block.objects.filter(
            blocker=blocker,
            blocked=blocked
        ).exists()

    @staticmethod
    def get_blocked_users(user):
        """Get all users blocked by this user"""
        return Block.objects.filter(
            blocker=user
        ).values_list('blocked', flat=True)

    @staticmethod
    def can_interact(user1, user2):
        """Check if two users can interact based on block status"""
        # If either user has blocked the other, they cannot interact
        return not (
            Block.objects.filter(blocker=user1, blocked=user2).exists() or
            Block.objects.filter(blocker=user2, blocked=user1).exists()
        )


# Notification System (Optional)
@receiver(post_save, sender=Follow)
def follow_notification(sender, instance, created, **kwargs):
    if created and instance.is_active:
        pass


# Notification System (Optional)
@receiver(post_save, sender=Block)
def block_notification(sender, instance, created, **kwargs):
    if created:
        pass
