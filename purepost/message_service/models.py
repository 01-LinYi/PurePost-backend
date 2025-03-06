import uuid

from django.db import models

from purepost.user_service.models import Profile


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4(), editable=False)  # Use UUID for ID
    participants = models.ManyToManyField(
        Profile,
        related_name="conversations"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    image = models.BooleanField(default=False)

    def __str__(self):
        return f"Conversation {self.name}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE
    )
    sender = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    content = models.TextField()

    def __str__(self):
        return f"{self.sender.user.username} sent a message to {self.conversation.name}"
