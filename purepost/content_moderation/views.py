from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Post, Folder, SavedPost
from .serializers import (
    PostSerializer, PostCreateSerializer,
    FolderSerializer, SavedPostSerializer, SavedPostListSerializer
)
from .permissions import IsOwnerOrReadOnly


class PostViewSet(viewsets.ModelViewSet):
    """Post ViewSet - Handles CRUD operations for Post model"""
    queryset = Post.objects.all()
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['content']
    ordering_fields = ['created_at', 'like_count',
                       'comment_count', 'share_count']
    ordering = ['-created_at']  # Default order by creation time descending

    def get_serializer_class(self):
        """Choose appropriate serializer based on action type"""
        if self.action == 'create':
            return PostCreateSerializer
        return PostSerializer

    def get_queryset(self):
        """Filter queryset based on request parameters"""
        queryset = Post.objects.all()

        # Filter by visibility - only owner can see their private posts
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='private', user=self.request.user)
            )
        else:
            queryset = queryset.filter(visibility='public')

        # Filter by user ID
        user_id = self.request.query_params.get('user_id')
        if user_id:
            if user_id == 'me':
                user_id = self.request.user.id
            # Get posts of the specified user
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def perform_create(self, serializer):
        """Set current user as author when creating a post"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """Like a post"""
        post = self.get_object()

        # Check if already liked (assuming Like model exists, adjust as needed)
        # Comment this section if Like model is not yet implemented
        
        if post.likes.filter(user=request.user).exists():
            return Response(
                {"detail": "You have already liked this post"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create like record
        post.likes.create(user=request.user)
        

        # Update like count
        post.like_count += 1
        post.save()

        return Response({"detail": "Post liked successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unlike(self, request, pk=None):
        """Unlike a post"""
        post = self.get_object()

        # If Like model exists, adjust as needed
        try:
            like = post.likes.filter(user=request.user).first()
            if like:
                like.delete()
        except AttributeError:
            # if Like model is not implemented, pass
            pass

        # Update like count, ensure it doesn't go below 0
        if post.like_count > 0:
            post.like_count -= 1
            post.save()

        return Response({"detail": "Post unliked successfully"}, status=status.HTTP_200_OK)


class FolderViewSet(viewsets.ModelViewSet):
    """Folder ViewSet - Handles CRUD operations for Folder model"""
    serializer_class = FolderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        """Return only folders owned by the current user"""
        return Folder.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Set current user as owner when creating a folder"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        """Get posts in a folder"""
        folder = self.get_object()
        saved_posts = SavedPost.objects.filter(
            folder=folder, user=request.user)
        serializer = SavedPostListSerializer(
            saved_posts, many=True, context={'request': request})
        return Response(serializer.data)


class SavedPostViewSet(viewsets.ModelViewSet):
    """SavedPost ViewSet - Handles CRUD operations for SavedPost model"""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Choose appropriate serializer based on action"""
        if self.action == 'list' or self.action == 'retrieve':
            return SavedPostListSerializer
        return SavedPostSerializer

    def get_queryset(self):
        """Return only saved posts owned by the current user"""
        queryset = SavedPost.objects.filter(user=self.request.user)

        # Filter by folder ID
        folder_id = self.request.query_params.get('folder_id')
        if folder_id:
            if folder_id == 'null':  # Find saved posts not categorized in a folder
                queryset = queryset.filter(folder__isnull=True)
            else:
                queryset = queryset.filter(folder_id=folder_id)

        return queryset

    def perform_create(self, serializer):
        """Set current user as owner when creating a saved post"""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='toggle')
    def toggle_save(self, request):
        """Toggle post save status - save if not saved, unsave if already saved"""
        post_id = request.data.get('post_id')
        folder_id = request.data.get('folder_id')

        if not post_id:
            return Response(
                {"detail": "Post ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        post = get_object_or_404(Post, id=post_id)
        folder = None

        if folder_id:
            folder = get_object_or_404(Folder, id=folder_id, user=request.user)

        # Check if post is already saved in this folder (or without folder)
        saved_post = SavedPost.objects.filter(
            user=request.user,
            post_id=post_id,
            folder=folder
        ).first()

        if saved_post:
            # If already saved, unsave it
            saved_post.delete()
            return Response(
                {"detail": "Post removed from saved"},
                status=status.HTTP_200_OK
            )
        else:
            # If not saved, save it
            saved_post = SavedPost.objects.create(
                user=request.user,
                post=post,
                folder=folder
            )
            serializer = SavedPostSerializer(
                saved_post, context={'request': request})
            return Response(
                {"detail": "Post saved successfully",
                    "saved_post": serializer.data},
                status=status.HTTP_201_CREATED
            )
