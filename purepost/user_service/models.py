from django.db import models
from django.conf import settings


class Profile(models.Model):
    """
    A model to store additional user information linked to the User model.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name='user_profile',  # Allows reverse lookup via `user.user_profile`
        help_text="The user this profile belongs to.",
        db_index=True  # Explicitly index the field for performance
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        default='avatars/defaults.png',  # Path to the default image
        help_text="User's profile picture."
    )
    bio = models.TextField(
        max_length=200,
        blank=True,
        help_text="Short description about the user (maximum 200 characters)."
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's location (optional)."
    )
    website = models.URLField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Personal or professional website link."
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="User's date of birth (optional)."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time when the profile was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="The date and time when the profile was last updated."
    )

    def __str__(self) -> str:
        """
        String representation of the Profile model.
        Uses a stable field like user.id to avoid issues with mutable fields.
        """
        return f"Profile of User ID {self.user.id}"
