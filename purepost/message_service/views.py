from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404, RetrieveUpdateAPIView, ListAPIView, ListCreateAPIView, \
    UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.views import APIView

from purepost.message_service.models import Conversation
from purepost.message_service.serializers import ConversationSerializer
from purepost.user_service.models import Profile


class ConversationView(ListCreateAPIView, UpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ConversationSerializer

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return Conversation.objects.filter(participants=profile).order_by('last_message_at')

#
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_all_user_conv(request: Request) -> Response:
#     user_conversations = Conversation.objects.filter(participants=request.user).order_by('last_message_at')
#
#     serializer = ConversationSerializer(user_conversations, many=True)
#     return Response(serializer.data, status=HTTP_200_OK)
#
#
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def get_conv_by_id(request: Request) -> Response:
#     conv = get_object_or_404(Conversation, request.query_params.get('id'))
#     serializer = ConversationSerializer(conv)
#     return Response(serializer.data, status=HTTP_200_OK)
#
#
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_conv(request: Request):
#     serializer = ConversationSerializer(data=request.data)
#     if serializer.is_valid():
#         conv: Conversation = serializer.save()
#         return Response(conv, status=HTTP_201_CREATED)
#     return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
#
#
# @api_view(['PUT', 'PATCH', 'POST'])
# @permission_classes([IsAuthenticated])
# def update_conv(request: Request):
#     conv = get_object_or_404(Conversation, request.data.get('id'))
#
#     serializer = ConversationSerializer(instance=conv, data=request.data, partial=True)
#     if serializer.is_valid():
#         conv = serializer.save()
#         return Response(conv, status=HTTP_200_OK)
#     return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
