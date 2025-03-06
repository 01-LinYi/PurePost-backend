from django.db.models import Count
from rest_framework import serializers
from .models import *


class ConversationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=True)  # Make name optional in requests
    participants = serializers.PrimaryKeyRelatedField(many=True, queryset=Profile.objects.all())

    class Meta:
        model = Conversation
        fields = ['id', 'name', 'created_at', 'participants']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        participants = validated_data.pop('participants', [])  # Extract participants

        # Check if there is a conversation with the exact same participants
        existing_conversation = (
            Conversation.objects.annotate(participant_count=Count('participants'))  # Annotate participant count
            .filter(participants__in=participants)  # Ensure participants match
            .filter(participant_count=len(participants))  # Ensure count matches
            .distinct()
            .first()
        )

        # Return old conversation if existed
        if existing_conversation:
            return existing_conversation

        # Generate default name
        usernames = sorted(participant.user.username for participant in participants)
        validated_data["name"] = ", ".join(usernames)

        conversation: Conversation = Conversation.objects.create(**validated_data)
        conversation.participants.set(participants)  # noqa Set the ManyToMany relationship
        return conversation

    def update(self, instance, validated_data):
        participants = validated_data.pop('participants', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if participants is not None:
            instance.participants.set(participants)  # Update the ManyToMany relationship
        return instance


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.IntegerField(required=True)
    conv = serializers.IntegerField(required=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'sender', 'conv']

    @staticmethod
    def validate_sender(value):
        from django.contrib.auth import get_user_model
        user_model = get_user_model()
        if not user_model.objects.filter(id=value).exists():
            raise serializers.ValidationError("Sender not found.")
        return value

    @staticmethod
    def validate_conv(value):
        if not Conversation.objects.filter(id=value).exists():
            raise serializers.ValidationError("Conversation not found.")
