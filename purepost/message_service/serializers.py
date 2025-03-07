from rest_framework import serializers
from .models import *


class ConversationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=True)  # Make name optional in requests
    participants = serializers.PrimaryKeyRelatedField(many=True, queryset=Profile.objects.all())
    is_existing = False

    class Meta:
        model = Conversation
        fields = ['id', 'name', 'created_at', 'participants']
        read_only_fields = ['id', 'created_at']

    @staticmethod
    def validate_participants(value):
        """
        Validate that participant IDs are unique.
        """
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate participant IDs are not allowed.")
        return value

    def create(self, validated_data):
        # Extract the participants from the validated data
        participants = validated_data.pop('participants')  # Remove participants from validated_data

        # print(f"Participants: {participants}")

        # # Check if a conversation with the exact same participants exists
        # existing_conversation = (
        #     Conversation.objects.annotate(participant_count=Count("participants"))
        #     .filter(participant_count=len(participants))  # Match participant count
        #     .filter(participants__in=participants)
        #     .distinct()
        # )
        #
        # print(f"Existing conversations: {existing_conversation}")
        #
        # # Verify if an exact match exists
        # for conv in existing_conversation:
        #     if set(conv.participants.values_list("user_id", flat=True)) == set([p.user.id for p in participants]):
        #         print("Conversation already exists")
        #         self.is_existing = True
        #         return conv
        #
        # print("Conversation does not exist")

        # Generate default name if not provided
        if 'name' not in validated_data or not validated_data['name']:
            usernames = sorted(participant.user.username for participant in participants)
            validated_data["name"] = ", ".join(usernames)

        # Create the conversation
        conversation = Conversation.objects.create(**validated_data)

        # Set the ManyToMany relationship for participants
        conversation.participants.set(participants)

        # Ensure the `is_existing` flag is set for a new conversation
        self.is_existing = False

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
