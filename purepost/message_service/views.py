from rest_framework.generics import GenericAPIView, ListCreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated

from purepost.message_service.models import Conversation
from purepost.message_service.serializers import ConversationSerializer
from purepost.user_service.models import Profile


class ConversationView(GenericAPIView):
    """
    Handles the retrieval of conversation data for an authenticated user.

    This view provides functionality to fetch a queryset of conversations in
    which the currently authenticated user's profile is a participant.
    It uses token-based authentication to ensure access is restricted to
    verified users and supports the serialization of conversation objects.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        """
        Fetches the queryset of conversations the current user belongs to
        and orders them by the time of the last message.

        Returns:
            QuerySet: A queryset of Conversation objects filtered by the current user's profile
            and sorted in ascending order based on the timestamp of the last message.
        """
        profile = Profile.objects.get(user=self.request.user)
        return Conversation.objects.filter(participants=profile).order_by('last_message_at')


class ConversationListCreateView(ListCreateAPIView, ConversationView):
    """
    Class representing a view for listing and creating conversations.

    This class inherits from both ListCreateAPIView and ConversationView.
    It is designed to handle operations related to conversations,
    specifically listing existing conversations and creating new ones.
    The primary purpose of this view is to provide an API endpoint for managing conversation objects.
    """
    pass


class ConversationUpdateView(UpdateAPIView, ConversationView):
    """
    Provides functionality to update a conversation.

    This class is designed to handle updating an existing conversation.
    It combines the capabilities of an UpdateAPIView
    for handling API updates and the custom functionalities of ConversationView for managing conversation-specific logic.
    It adheres to Django's API framework to facilitate modular and scalable development.
    This view should be used where updating conversation objects is required.
    """
    pass
