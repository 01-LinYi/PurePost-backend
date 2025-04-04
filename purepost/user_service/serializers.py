from rest_framework import serializers
from .models import Profile
from ..social_service.models import Follow


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the Profile model.
    Serializes all fields of the Profile model and provides validation for updating user profiles.
    """
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    is_private = serializers.BooleanField(source="user.is_private", read_only=True)
    is_followed = serializers.SerializerMethodField()  # whether the current user follows the returning profile

    class Meta:
        model = Profile
        fields = [
            # Auth User fields
            "user_id",
            "username",
            "email",
            "is_active",
            "is_private",

            # Profile fields
            "avatar",
            "bio",
            "location",
            "website",
            "date_of_birth",
            "created_at",
            "updated_at",
            "is_followed",
        ]
        # These fields can't be modified
        read_only_fields = [
            "username", "email",
            "is_active", "is_private",
            "created_at", "updated_at"
        ]

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

    def get_is_followed(self, obj) -> bool:
        """
        Custom method to check if the currently logged-in user follows the profile user.
        """
        request = self.context.get('request')  # Access the request from the serializer context
        if request and request.user.is_authenticated:  # Ensure the user is logged in
            return Follow.objects.filter(follower=request.user, following=obj.user).exists()
        return False  # If the user isn't logged in, return False as the default

    def to_representation(self, instance):
        """
        Override to conditionally hide fields based on privacy settings.
        If the profile is private and the user isn't followed, hide certain fields.
        """
        # Get the base representation
        ret = super().to_representation(instance)

        # Define fields to hide for private profiles when not followed
        private_hidden_fields = [
            "bio",
            "location",
            "website",
            "date_of_birth",
        ]

        # Check if the profile is private and the user isn't followed
        if ret.get('is_private') and not ret.get('is_followed'):
            # The current user isn't the profile owner and doesn't follow them
            request = self.context.get('request')

            # If it's not the user's own profile, hide the fields
            if not (request and request.user.is_authenticated and request.user.id == instance.user_id):
                # Remove the private fields from the response
                for field in private_hidden_fields:
                    if field in ret:
                        ret.pop(field)

        return ret
