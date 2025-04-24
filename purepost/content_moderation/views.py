import logging
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from rest_framework import viewsets, status, permissions, filters, generics
from rest_framework.serializers import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware, make_aware
from django.utils import timezone



from .models import Post, Folder, SavedPost, Share, Comment, Report
from .serializers import (
    UserSerializer, PostSerializer, PostCreateSerializer,
    FolderSerializer, SavedPostSerializer, SavedPostListSerializer,
    CommentSerializer, ShareSerializer, 
    ReportSerializer, ReportUpdateSerializer, ReportStatsSerializer, ReportMiniSerializer
)
from .permissions import IsOwnerOrReadOnly, IsReporterOrAdmin
from .throttling import ReportRateThrottle

from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from purepost.auth_service.permissions import IsAdminUser

User = get_user_model()
logger = logging.getLogger(__name__)


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
            # Only show public posts for others
            posts = posts.filter(visibility='public')

        page = self.paginate_queryset(posts)
        post_serializer = PostSerializer(
            page, many=True, context={'request': request})

        return self.get_paginated_response({
            'profile': profile_serializer.data,
            'posts': post_serializer.data
        })


class PostViewSet(viewsets.ModelViewSet):
    """Post ViewSet - Handles CRUD operations for Post model"""

    class CustomSearchFilter(filters.SearchFilter):
        """Custom search filter to allow searching by specific fields"""

        def get_search_fields(self, view, request):
            only_field = request.query_params.get('only')
            if only_field:
                return [only_field]
            return super().get_search_fields(view, request)

    queryset = Post.objects.all()
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    search_fields = ['content', 'caption', 'tags', '=user__username']
    ordering_fields = ['created_at', 'like_count',
                       'comment_count', 'share_count']
    ordering = ['-created_at']  # Default order by creation time descending
    filter_backends = [CustomSearchFilter, filters.OrderingFilter]
    pagination_class = ProfilePostPagination

    def get_serializer_class(self):
        """Choose appropriate serializer based on action type"""
        if self.action in ['create', 'update']:
            return PostCreateSerializer
        return PostSerializer

    # Param options are: user_id: unknown, is_pinned: boolean.
    def get_queryset(self):
        """Filter queryset based on request parameters"""
        queryset = Post.objects.all()

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

        return queryset

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
        existing_draft = Post.objects.filter(
            user=request.user, status='draft').first()

        if existing_draft:
            # Update existing draft
            serializer = self.get_serializer(
                existing_draft, data=request.data, partial=True)
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
    
    @action(detail=True, methods=['post'], url_path='schedule')
    def schedule_post(self, request, pk=None):
        """Schedule a post for future publication"""
        post = self.get_object()
        
        # Make sure the post belongs to the requesting user
        if post.user != request.user:
            return Response(
                {"detail": "You don't have permission to schedule this post."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get scheduled_for from request data
        scheduled_for = request.data.get('scheduled_for')
        if not scheduled_for:
            return Response(
                {"detail": "scheduled_for date is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Parse the datetime string
            scheduled_datetime = parse_datetime(scheduled_for)
            if not scheduled_datetime:
                raise ValueError("Invalid datetime format")
                
            # Ensure timezone awareness
            if not is_aware(scheduled_datetime):
                scheduled_datetime = make_aware(scheduled_datetime)
            
            # Ensure the scheduled time is in the future
            if scheduled_datetime <= timezone.now():
                return Response(
                    {"detail": "Scheduled time must be in the future"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update the post
            post.status = 'scheduled'
            post.scheduled_for = scheduled_datetime
            post.save()
            
            serializer = self.get_serializer(post)
            return Response(serializer.data)
            
        except ValueError as e:
            return Response(
                {"detail": str(e) or "Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"},
                status=status.HTTP_400_BAD_REQUEST
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
        """Retrieve the list of users who commented on a post"""
        post = get_object_or_404(Post, id=pk)
        users = User.objects.filter(comments__post=post).distinct()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class ReportViewSet(viewsets.ModelViewSet):
    """
    Report ViewSet - Handles CRUD operations for Report model.

    Allows users to report posts for moderation.
    Allows admins to view and manage reports.

    Regular users can only:
    - Create new reports
    - View their own reports
    - Delete their own reports (if still pending)

    Admins can:
    - View all reports
    - Update report status
    - Delete any report
    - Access reporting statistics
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reason', 'additional_info', 'post__title']
    ordering_fields = ['created_at', 'updated_at', 'status']
    ordering = ['-created_at']
    throttle_classes = []

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Report.objects.all()
        return Report.objects.filter(reporter=user)

    def get_serializer_class(self):
        if self.action == 'update' or self.action == 'partial_update':
            return ReportUpdateSerializer
        if self.action == 'stats':
            return ReportStatsSerializer
        return ReportSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update']:
            return [IsAdminUser()]
        elif self.action == 'destroy':
            return [IsReporterOrAdmin()]
        elif self.action in ['stats', 'pending', 'resolve', 'reject', 'bulk_update']:
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    def get_throttles(self):
        if self.action == 'create':
            # Apply throttling only for the create action
            self.throttle_scope = 'report_create'
            self.throttle_classes = [ReportRateThrottle]
        else:
            # Use default throttling for other actions
            self.throttle_classes = []
        return [throttle() for throttle in self.throttle_classes]

    def perform_create(self, serializer):
        """create a new report and send notification"""
        try:
            post_id = serializer.validated_data.get('post_id')
            post = get_object_or_404(Post, id=post_id)
            user = self.request.user

            # check if the post exists
            if Report.objects.filter(post_id=post_id, reporter=user).exists():
                raise ValidationError(
                    {"non_field_errors": [_("You have already reported this post")]})

            # save
            report = serializer.save(reporter=user, post=post)

            '''
            # send notification to the reporter
            try:
                from .tasks import send_report_notification
                send_report_notification.delay(
                    report.id,
                    report.reporter.id,
                    f"您已举报帖子 '{report.post.title[:30]}...' 的 {report.get_reason_display()}",
                )

                # If the report count exceeds a threshold, notify the admin
                report_count = Report.objects.filter(post_id=post_id).count()
                if report_count >= 5:  # Config here
                    send_admin_alert.delay(
                        post_id,
                        f"Post '{report.post.title[:30]}...' has been reported {report_count} times.",
                    )
            except Exception as e:
                logger.error(f"Failed to send report notification: {str(e)}")
            '''

        except Exception as e:
            logger.error(f"Failed to create report: {str(e)}")
            raise

    def perform_update(self, serializer):
        """Update report status and send notification"""
        try:
            old_status = serializer.instance.status
            report = serializer.save(handled_by=self.request.user)
            new_status = report.status

            """if old_status != new_status:
                try:
                    from .tasks import send_report_notification
                    send_report_notification.delay(
                        report.id,
                        report.reporter.id,
                        f"Report Staus Update: {report.get_status_display()}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send status update notification: {str(e)}")
            """

        except Exception as e:
            logger.error(f"Failed to update report: {str(e)}")
            raise

    def perform_destroy(self, instance):
        """Check before deleting a report"""
        try:
            if not self.request.user.is_admin and instance.status != 'pending':
                raise permissions.PermissionDenied(
                    _("You cannot delete a report that has been processed")
                )

            logger.info(
                f"Report {instance.id} deleted by {self.request.user.username}")
            instance.delete()
        except Exception as e:
            logger.error(f"Failed to delete report: {str(e)}")
            raise

    @action(detail=False, methods=['get'])
    def my_reports(self, request):
        """get all reports submitted by the user"""
        reports = Report.objects.filter(reporter=request.user)

        # filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            reports = reports.filter(status=status_filter)

        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = ReportMiniSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReportMiniSerializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending reports (admin only)"""
        if not request.user.is_admin:
            return Response(
                {"detail": _("Only administrators can view pending reports")},
                status=status.HTTP_403_FORBIDDEN
            )

        reports = Report.objects.filter(status='pending')

        # filter by reason
        reason_filter = request.query_params.get('reason')
        if reason_filter:
            reports = reports.filter(reason=reason_filter)

        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """mark a report as resolved (admin only)"""
        report = self.get_object()
        old_status = report.status

        if old_status == 'resolved':
            return Response(
                {"detail": _("This report is already resolved")},
                status=status.HTTP_400_BAD_REQUEST
            )

        report.status = 'resolved'
        report.handled_by = request.user
        report.save()

        # Send notification to the reporter
        """try:
            from .tasks import send_report_notification
            send_report_notification.delay(
                report.id,
                report.reporter.id,
                f"Your report on post '{report.post.title[:30]}...' has been resolved.",
            )
        except Exception as e:
            logger.error(f"Failed to send resolution notification: {str(e)}")"""

        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a report (admin only)"""
        report = self.get_object()
        old_status = report.status

        if old_status == 'rejected':
            return Response(
                {"detail": _("This report is already rejected")},
                status=status.HTTP_400_BAD_REQUEST
            )

        report.status = 'rejected'
        report.handled_by = request.user
        report.save()

        """try:
            from .tasks import send_report_notification
            send_report_notification.delay(
                report.id,
                report.reporter.id,
                f"Your report on post '{report.post.title[:30]}...' has been rejected. There is no violation found.",
            )
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {str(e)}")"""

        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """get report statistics (admin only)"""
        if not request.user.is_admin:
            return Response(
                {"detail": _("Only administrators can view report statistics")},
                status=status.HTTP_403_FORBIDDEN
            )

        # basic statistics
        total = Report.objects.count()
        pending = Report.objects.filter(status='pending').count()
        reviewing = Report.objects.filter(status='reviewing').count()
        resolved = Report.objects.filter(status='resolved').count()
        rejected = Report.objects.filter(status='rejected').count()

        # by reason
        reason_stats = (
            Report.objects.values('reason')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # last 7 days trend
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=6)

        trend_data = []
        for i in range(7):
            day = seven_days_ago + timedelta(days=i)
            next_day = day + timedelta(days=1)
            count = Report.objects.filter(
                created_at__gte=day,
                created_at__lt=next_day
            ).count()
            trend_data.append({
                'date': day.strftime('%Y-%m-%d'),
                'count': count
            })

        # top 5 reported posts
        top_reported_posts = (
            Post.objects.annotate(report_count=Count('reports'))
            .filter(report_count__gt=0)
            .order_by('-report_count')[:5]
            .values('id', 'caption', 'report_count')
        )

        data = {
            'total': total,
            'by_status': {
                'pending': pending,
                'reviewing': reviewing,
                'resolved': resolved,
                'rejected': rejected
            },
            'by_reason': list(reason_stats),
            'trend': trend_data,
            'top_reported_posts': list(top_reported_posts)
        }

        return Response(data)
