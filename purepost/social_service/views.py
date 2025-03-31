from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q, Exists, OuterRef
from rest_framework import status
from rest_framework.generics import ListAPIView, DestroyAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from purepost.social_service.FollowPagination import FollowPagination, BlockPagination
from purepost.social_service.models import Follow, Block
from purepost.social_service.serializers import (
    FollowSerializer, BlockSerializer, FollowStatusSerializer
)

User = get_user_model()


class FollowCreateView(CreateAPIView):
    """Create a follow relationship"""
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    
    def create(self, request, *args, **kwargs):
        following_id = kwargs.get('user_id') or request.data.get('following')
        if not following_id:
            return Response({"detail": "User ID to follow is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user to follow
        following = get_object_or_404(User, pk=following_id)
        
        # Check for blocks
        block_exists = Block.objects.filter(
            Q(blocker=request.user, blocked=following) | 
            Q(blocker=following, blocked=request.user)
        ).exists()
        
        if block_exists:
            return Response(
                {"detail": "Cannot follow a blocked user or a user who has blocked you"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create or activate follow relationship
        follow_obj, created = Follow.follow(request.user, following)
        
        serializer = self.get_serializer(follow_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class FollowDestroyView(DestroyAPIView):
    """Unfollow a user"""
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        following_id = self.kwargs.get('user_id')
        if not following_id:
            return Response({"detail": "User ID to unfollow is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user to unfollow
        following = get_object_or_404(User, pk=following_id)
        
        # Unfollow
        if Follow.unfollow(request.user, following):
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "Not following this user"}, status=status.HTTP_404_NOT_FOUND)


class FollowStatusView(APIView):
    """Get follow status information"""
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request, user_id=None):
        # Default to current user if no user_id provided
        if not user_id and request.user.is_authenticated:
            user_id = request.user.id
        elif not user_id:
            return Response({"detail": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(User, pk=user_id)
        
        # Get follow status efficiently
        follower_count = Follow.objects.filter(following=user, is_active=True).count()
        following_count = Follow.objects.filter(follower=user, is_active=True).count()
        
        is_following = False
        if request.user.is_authenticated and request.user.id != user_id:
            is_following = Follow.objects.filter(
                follower=request.user, 
                following=user,
                is_active=True
            ).exists()
        
        data = {
            'is_following': is_following,
            'follower_count': follower_count,
            'following_count': following_count
        }
        
        serializer = FollowStatusSerializer(data=data)
        serializer.is_valid()  # Always valid as we control the data
        return Response(serializer.data)


class CurrentFollowerListView(ListAPIView):
    """List Follow relationships where current user is being followed"""
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    pagination_class = FollowPagination
    
    def get_queryset(self):
        # Return Follow objects where current user is being followed
        return Follow.objects.filter(
            following=self.request.user,
            is_active=True
        ).select_related('follower').order_by('-created_at')


class CurrentFollowingListView(ListAPIView):
    """List Follow relationships where current user is following others"""
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    pagination_class = FollowPagination
    
    def get_queryset(self):
        # Return Follow objects where current user is following others
        return Follow.objects.filter(
            follower=self.request.user,
            is_active=True
        ).select_related('following').order_by('-created_at')


class UserFollowerListView(ListAPIView):
    """List Follow relationships where a specific user is being followed"""
    serializer_class = FollowSerializer
    pagination_class = FollowPagination
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, pk=user_id)
        
        # Check for blocks if authenticated
        request_user = self.request.user
        if request_user.is_authenticated:
            block_exists = Block.objects.filter(
                Q(blocker=user, blocked=request_user) | 
                Q(blocker=request_user, blocked=user)
            ).exists()
            
            if block_exists:
                return Follow.objects.none()
        
        # Return Follow objects where target user is being followed
        return Follow.objects.filter(
            following=user,
            is_active=True
        ).select_related('follower').order_by('-created_at')


class UserFollowingListView(ListAPIView):
    """List Follow relationships where a specific user is following others"""
    serializer_class = FollowSerializer
    pagination_class = FollowPagination
    
    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        user = get_object_or_404(User, pk=user_id)
        
        # Check for blocks if authenticated
        request_user = self.request.user
        if request_user.is_authenticated:
            block_exists = Block.objects.filter(
                Q(blocker=user, blocked=request_user) | 
                Q(blocker=request_user, blocked=user)
            ).exists()
            
            if block_exists:
                return Follow.objects.none()
        
        # Return Follow objects where target user is following others
        return Follow.objects.filter(
            follower=user,
            is_active=True
        ).select_related('following').order_by('-created_at')


class BlockCreateView(CreateAPIView):
    """Block a user"""
    permission_classes = [IsAuthenticated]
    serializer_class = BlockSerializer
    
    def create(self, request, *args, **kwargs):
        blocked_id = kwargs.get('user_id') or request.data.get('blocked')
        if not blocked_id:
            return Response({"detail": "User ID to block is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user to block
        blocked = get_object_or_404(User, pk=blocked_id)
        
        # Block user
        reason = request.data.get('reason', '')
        block_obj, created = Block.block_user(request.user, blocked, reason)
        
        serializer = self.get_serializer(block_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class BlockDestroyView(DestroyAPIView):
    """Unblock a user"""
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        blocked_id = self.kwargs.get('user_id')
        if not blocked_id:
            return Response({"detail": "User ID to unblock is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user to unblock
        blocked = get_object_or_404(User, pk=blocked_id)
        
        # Unblock user
        if Block.unblock_user(request.user, blocked):
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "User not blocked"}, status=status.HTTP_404_NOT_FOUND)


class BlockedUserListView(ListAPIView):
    """List Block relationships where current user has blocked others"""
    permission_classes = [IsAuthenticated]
    serializer_class = BlockSerializer
    pagination_class = BlockPagination
    
    def get_queryset(self):
        # Return Block objects where current user has blocked others
        return Block.objects.filter(
            blocker=self.request.user
        ).select_related('blocked').order_by('-created_at')