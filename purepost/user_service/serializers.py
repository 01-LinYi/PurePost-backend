from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the Profile model.
    Serializes all fields of the Profile model and provides validation for updating user profiles.
    """
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "username",  # Profile has a foreign key to the User model
            "avatar",
            "bio",
            "location",
            "website",
            "date_of_birth",
            "created_at",
            "updated_at",
        ]
        # These fields cannot be modified
        read_only_fields = ["username", "created_at", "updated_at"]

    def validate_bio(self, value: str) -> str:
        """
        Custom validation for the `bio` field.
        Ensures the bio does not exceed the maximum allowed length.
        """
        if len(value) > 200:
            raise serializers.ValidationError(
                "The bio must not exceed 200 characters.")
        return value

    def validate_website(self, value: str) -> str:
        """
        Custom validation for the `website` field.
        Ensures the website URL is valid if provided.
        """
        if value and not value.startswith(("http://", "https://")):
            raise serializers.ValidationError(
                "The website URL must start with http:// or https://.")
        return value

    def validate_date_of_birth(self, value):
        """
        Custom validation for the `date_of_birth` field.
        Ensures the date of birth is not in the future.
        """
        from datetime import date
        if value and value > date.today():
            raise serializers.ValidationError(
                "The date of birth cannot be in the future.")
        return value
