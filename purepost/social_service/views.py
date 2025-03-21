from rest_framework.generics import DestroyAPIView, CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated

from purepost.social_service.FollowPagination import FollowPagination
from purepost.social_service.models import Follow
from purepost.social_service.serializers import FollowSerializer


class CurrentFollowerService(ListAPIView, CreateAPIView, DestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'following__id'
    serializer_class = FollowSerializer
    pagination_class = FollowPagination

    def get_queryset(self):
        curr_user = self.request.user
        return Follow.objects.filter(following=curr_user).order_by('created_at').reverse()


class CurrentFollowingService(ListAPIView, CreateAPIView, DestroyAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'follower__id'
    serializer_class = FollowSerializer
    pagination_class = FollowPagination

    def get_queryset(self):
        curr_user = self.request.user
        return Follow.objects.filter(follower=curr_user).order_by('created_at').reverse()


class OtherFollowerService(ListAPIView):
    serializer_class = FollowSerializer
    pagination_class = FollowPagination

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        if not user_id:
            raise ValueError('user_id is required')
        return Follow.objects.filter(following_id=user_id).order_by('created_at').reverse()


class OtherFollowingService(ListAPIView):
    serializer_class = FollowSerializer
    pagination_class = FollowPagination

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        if not user_id:
            raise ValueError('user_id is required')
        return Follow.objects.filter(follower_id=user_id).order_by('created_at').reverse()
