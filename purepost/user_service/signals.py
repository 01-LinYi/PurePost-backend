from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings  # For AUTH_USER_MODEL
from .models import Profile  # Import the Profile model


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(_, instance, created):
    """
    Auto-create a Profile whenever a new User is created.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(_, instance):
    """
    Save the Profile when the associated User is saved.
    """
    # Ensure the Profile is also saved if the User is updated
    if hasattr(instance, "user_profile"):
        instance.user_profile.save()
