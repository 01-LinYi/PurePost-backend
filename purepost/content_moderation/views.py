from rest_framework import viewsets, status, permissions, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Post, Folder, SavedPost, Share, Comment
from .serializers import (
    PostSerializer, PostCreateSerializer,
    FolderSerializer, SavedPostSerializer, SavedPostListSerializer,
    LikeSerializer, CommentSerializer, ShareSerializer
)
from .permissions import IsOwnerOrReadOnly

from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, PostSerializer

User = get_user_model()


class ProfilePostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class UserProfileView(generics.ListAPIView):
    """
    API endpoint to view a user's profile and posts with permission control.
    """
    serializer_class = PostSerializer
    pagination_class = ProfilePostPagination

    def get(self, request, username, *args, **kwargs):
        user = get_object_or_404(User, username=username)
        profile_serializer = UserSerializer(user, context={'request': request})

        # Check privacy settings
        if user.is_private and user != request.user:
            return Response({'detail': 'This profile is private.'}, status=403)

        # Retrieve visible posts
        posts = Post.objects.filter(user=user).order_by('-created_at')
        if user != request.user:
            posts = posts.filter(visibility='public')  # Only show public posts for others

        page = self.paginate_queryset(posts)
        post_serializer = PostSerializer(page, many=True, context={'request': request})

        return self.get_paginated_response({
            'profile': profile_serializer.data,
            'posts': post_serializer.data
        })


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
        if self.action in ['create', 'update']:
            return PostCreateSerializer
        return PostSerializer

    # Param options are: user_id: unknown, is_pinned: boolean.
    def get_queryset(self):
        """Filter queryset based on request parameters"""
        queryset = Post.objects.all()

        if self.action == 'scheduled':
            return queryset.filter(
                user=self.request.user,
                is_scheduled=True,
                is_published=False
            ).order_by('scheduled_time')
        
        # Filter by visibility - only owner can see their private posts and drafts
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(visibility='public', status='published') |
                Q(user=self.request.user)
            )
        else:
            queryset = queryset.filter(visibility='public', status='published')

        # Filter by user ID
        user_id = self.request.query_params.get('user_id')
        if user_id:
            if user_id == 'me':
                user_id = self.request.user.id
            # Get posts of the specified user
            queryset = queryset.filter(user_id=user_id)

        # Filter by pin status, default to all
        is_pinned = self.request.query_params.get('is_pinned')
        if is_pinned:
            pinned = None
            if is_pinned == 'true' or is_pinned == 'True':
                pinned = True
            elif is_pinned == 'false' or is_pinned == 'False':
                pinned = False
            else:
                return Response(
                    {"detail": "Invalid value for is_pinned parameter"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            queryset = queryset.filter(pinned=pinned)

        # Exclude scheduled posts from regular listings unless specifically requested
        if not self.request.query_params.get('include_scheduled'):
            queryset = queryset.filter(
                Q(is_scheduled=False) | 
                Q(user=self.request.user, is_scheduled=True)
            )

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set current user as author when creating a post"""
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Update post and handle disclaimer"""
        serializer.save()

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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def comment(self, request, pk=None):
        """Add a comment to a post"""
        post = self.get_object()
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, post=post)
            post.comment_count += 1
            post.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAuthenticated])
    def delete_comment(self, request, pk=None):
        """Delete a comment"""
        post = self.get_object()
        comment_id = request.data.get('comment_id')

        if not comment_id:
            return Response(
                {"detail": "Comment ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the comment
        comment = get_object_or_404(Comment, id=comment_id, post=post)

        # Ensure the user is the owner of the comment or an admin
        if comment.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You do not have permission to delete this comment"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete the comment
        comment.delete()

        # Update the comment count on the post
        post.comment_count = max(0, post.comment_count - 1)
        post.save()

        return Response(
            {"detail": "Comment deleted successfully"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def share(self, request, pk=None):
        """Share a post"""
        post = self.get_object()
        serializer = ShareSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, post=post)
            post.share_count += 1
            post.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_visibility(self, request, pk=None):
        """Allows users to update post visibility."""
        post = self.get_object()
        if post.user != request.user:
            return Response({'error': 'Unauthorized'}, status=403)

        new_visibility = request.data.get('visibility')
        if new_visibility not in ['public', 'private', 'friends']:
            return Response({'error': 'Invalid visibility option'}, status=400)

        post.visibility = new_visibility
        post.save()
        return Response({'message': 'Visibility updated', 'visibility': post.visibility})

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        post = Post.objects.get(pk=pk)
        if post.user != request.user:
            return Response({'error': 'Unauthorized'}, status=403)

        post.pinned = True
        post.save()
        return Response({'message': 'Post pinned'})

    @action(detail=True, methods=['post'])
    def unpin(self, request, pk=None):
        post = Post.objects.get(pk=pk)
        if post.user != request.user:
            return Response({'error': 'Unauthorized'}, status=403)

        post.pinned = False
        post.save()
        return Response({'message': 'Post unpinned'})

    @action(detail=False, methods=['get'], url_path='draft')
    def get_draft(self, request):
        """Get the user's draft post (assuming only one draft per user)"""
        draft = Post.objects.filter(user=request.user, status='draft').first()
        if not draft:
            return Response({"detail": "No draft found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(draft)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='save-draft')
    def save_draft(self, request):
        """Save or update the user's draft post"""
        # Check if user already has a draft
        existing_draft = Post.objects.filter(user=request.user, status='draft').first()
        
        if existing_draft:
            # Update existing draft
            serializer = self.get_serializer(existing_draft, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(status='draft')
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Create new draft
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user, status='draft')
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish_draft(self, request, pk=None):
        """Publish a draft post"""
        post = self.get_object()
        
        # Only the owner can publish their draft
        if post.user != request.user:
            return Response(
                {"detail": "You do not have permission to publish this draft"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Ensure it's a draft
        if post.status != 'draft':
            return Response(
                {"detail": "Only draft posts can be published"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that the post has required content
        if not (post.content or post.image or post.video):
            return Response(
                {"detail": "Post must have at least content, image, or video to be published"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update to published status
        post.status = 'published'
        post.save()
        
        # Return the updated post
        serializer = self.get_serializer(post)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-tag')
    def by_tag(self, request):
        """Search posts by tag"""
        tag_name = request.query_params.get('name')
        if not tag_name:
            return Response({'error': 'Tag name is required'}, status=status.HTTP_400_BAD_REQUEST)
        posts = Post.objects.filter(tags__name__iexact=tag_name,status='published').order_by('-created_at')
        page = self.paginate_queryset(posts)
        serializer = self.get_serializer(page, many=True)
        return Response(serializer.data)
    

    @action(detail=False, methods=['get'], url_path='scheduled')
    def scheduled_posts(self, request):
        """Get all scheduled posts for the current user"""
        queryset = Post.objects.filter(
            user=request.user,
            is_scheduled=True,
            is_published=False
        ).order_by('scheduled_time')
        
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='cancel-schedule')
    def cancel_schedule(self, request, pk=None):
        """Cancel a scheduled post"""
        post = self.get_object()
        if post.user != request.user:
            return Response(
                {'error': 'You can only cancel your own scheduled posts'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        post.is_scheduled = False
        post.scheduled_time = None
        post.save()
        
        return Response(
            {'message': 'Post scheduling cancelled successfully'},
            status=status.HTTP_200_OK
        )


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


class PostInteractionViewSet(viewsets.ViewSet):
    """ViewSet for retrieving post interactions (likes, shares, comments)."""

    permission_classes = [permissions.IsAuthenticated]

    def list_likes(self, request, pk=None):
        """Retrieve the list of users who liked a post"""
        post = get_object_or_404(Post, id=pk)
        users = User.objects.filter(likes__post=post).distinct()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def list_shares(self, request, pk=None):
        """Retrieve the list of users who shared a post."""
        post = get_object_or_404(Post, id=pk)
        users = User.objects.filter(share__post=post).distinct()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def list_comments(self, request, pk=None):
        """Retrieve the list of comments for a post"""
        post = get_object_or_404(Post, id=pk)
        comments = post.comments.filter(parent=None)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
