from django.contrib.auth import get_user_model
from rest_framework import serializers

from purepost.social_service.models import Follow, Block

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Serializer for basic user information"""
    class Meta:
        model = User
        fields = ['id', 'username']
        read_only_fields = fields


class FollowSerializer(serializers.ModelSerializer):
    """Serializer for Follow relationships"""
    follower_details = UserBasicSerializer(source='follower', read_only=True)
    following_details = UserBasicSerializer(source='following', read_only=True)
    
    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at', 'updated_at', 
                  'is_active', 'follower_details', 'following_details']
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active', 
                           'follower_details', 'following_details']
    
    def create(self, validated_data):
        follower = validated_data.get('follower')
        following = validated_data.get('following')
        
        if follower == following:
            raise serializers.ValidationError("Users cannot follow themselves.")
        
        follow_obj, created = Follow.follow(follower, following)
        return follow_obj


class BlockSerializer(serializers.ModelSerializer):
    """Serializer for Block relationships"""
    blocker_details = UserBasicSerializer(source='blocker', read_only=True)
    blocked_details = UserBasicSerializer(source='blocked', read_only=True)
    
    class Meta:
        model = Block
        fields = ['id', 'blocker', 'blocked', 'reason', 'created_at', 
                  'blocker_details', 'blocked_details']
        read_only_fields = ['id', 'created_at', 'blocker_details', 'blocked_details']


class FollowStatusSerializer(serializers.Serializer):
    """Serializer for follow status information"""
    is_following = serializers.BooleanField()
    follower_count = serializers.IntegerField()
    following_count = serializers.IntegerField()