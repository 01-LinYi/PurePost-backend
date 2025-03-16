from django.contrib.auth import get_user_model
from rest_framework import serializers

from purepost.social_service.models import Follow


class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.PrimaryKeyRelatedField(default=serializers.CurrentUserDefault(), queryset=get_user_model().objects.all())
    created_at = serializers.DateTimeField(read_only=True, required=False)

    class Meta:
        model = Follow
        fields = ['follower', 'following', 'created_at']
