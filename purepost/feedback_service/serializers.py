from rest_framework import serializers
from .models import Feedback
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(source='user_profile.bio', read_only=True)
    profile_picture = serializers.ImageField(
        source='user_profile.avatar', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email',
                  'bio', 'profile_picture', 'is_private']


class FeedbackSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'user', 'feedback_type',
                  'content','is_finished', 'created_at',  'updated_at']
        read_only_fields = ['created_at', 'user']
