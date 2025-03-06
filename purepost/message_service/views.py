from rest_framework.generics import GenericAPIView, ListCreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated

from purepost.message_service.models import Conversation
from purepost.message_service.serializers import ConversationSerializer
from purepost.user_service.models import Profile


class ConversationView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationSerializer

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return Conversation.objects.filter(participants=profile).order_by('last_message_at')


class ConversationListCreateView(ListCreateAPIView, ConversationView):
    pass


class ConversationUpdateView(UpdateAPIView, ConversationView):
    pass
