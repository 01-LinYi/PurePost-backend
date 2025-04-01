from django.db.models import Count, Avg
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
import logging

from purepost.content_moderation.models import Post
from .models import ImageAnalysis
from .serializers import ImageAnalysisSerializer, ImageAnalysisDetailSerializer, AnalysisStatisticsSerializer
from .tasks import process_image_analysis

logger = logging.getLogger(__name__)


class ImageAnalysisViewSet(viewsets.ViewSet):
    """
    API endpoint for image deepfake analysis.
    Provides endpoints to manage analyses via post ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter analyses to show only those related to the current user's posts
        unless the user is staff requesting all analyses
        """
        user = self.request.user
        if user.is_staff and self.request.query_params.get('all') == 'true':
            return ImageAnalysis.objects.all()
        return ImageAnalysis.objects.filter(post__user=user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        return ImageAnalysisDetailSerializer if self.action == 'get_by_post' else ImageAnalysisSerializer

    def get_serializer(self, *args, **kwargs):
        """Get serializer instance"""
        serializer_class = self.get_serializer_class()
        return serializer_class(*args, **kwargs)

    def get_by_post(self, request, post_id=None):
        """
        Get analysis for a specific post

        Returns the deepfake analysis result for a given post ID
        """
        # Verify the post exists and user has permissions
        post = get_object_or_404(Post, id=post_id)

        # Check if user has permission to view this post
        if not request.user.is_staff and post.user != request.user:
            return Response(
                {"detail": "You do not have permission to view this analysis"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            analysis = ImageAnalysis.objects.get(post_id=post_id)

            # Only return completed analyses with high enough confidence
            if analysis.status == 'completed':
                serializer = self.get_serializer(analysis)
                return Response(serializer.data)
            elif analysis.status == 'failed':
                return Response(
                    {"status": "failed", "message": "Analysis failed to complete"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {"status": analysis.status,
                        "message": "Analysis not yet completed"},
                    status=status.HTTP_202_ACCEPTED
                )

        except ImageAnalysis.DoesNotExist:
            return Response(
                {"detail": "No analysis found for this post"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ImageAnalysis.MultipleObjectsReturned:
            # If there are multiple analyses, return the most recent one
            analysis = ImageAnalysis.objects.filter(
                post_id=post_id).order_by('-created_at').first()

            if analysis.status == 'completed':
                serializer = self.get_serializer(analysis)
                return Response(serializer.data)
            elif analysis.status == 'failed':
                return Response(
                    {"status": "failed", "message": "Analysis failed to complete"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {"status": analysis.status,
                        "message": "Analysis not yet completed"},
                    status=status.HTTP_202_ACCEPTED
                )

    def create_for_post(self, request, post_id=None):
        """
        Create a new analysis for a specific post

        Initiates deepfake detection analysis for the given post
        """
        # Check if post exists
        post = get_object_or_404(Post, id=post_id)

        # Check if user has permission to analyze this post
        if not request.user.is_staff and post.user != request.user:
            return Response(
                {"detail": "You do not have permission to analyze this post"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if an analysis already exists and is not failed
        existing_analysis = ImageAnalysis.objects.filter(
            post_id=post_id).exclude(status='failed').first()
        if existing_analysis:
            return Response(
                {"detail": f"An analysis already exists for this post with status: {existing_analysis.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new analysis or find a failed one to reuse
        analysis = ImageAnalysis.objects.filter(
            post_id=post_id, status='failed').first()
        if analysis:
            # Reset the failed analysis
            analysis.status = 'pending'
            analysis.failure_reason = None
            analysis.save(update_fields=['status', 'failure_reason'])
        else:
            # Create a new analysis
            analysis = ImageAnalysis.objects.create(
                post=post,
                status='pending'
            )
            # Update post status
            post.deepfake_status = 'analyzing'
            post.save(update_fields=['deepfake_status'])

        # Queue the analysis task
        task = process_image_analysis.delay(str(analysis.id))
        analysis.task_id = task.id
        analysis.save(update_fields=['task_id'])

        serializer = self.get_serializer(analysis)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retry_by_post(self, request, post_id=None):
        """
        Retry analysis for a specific post

        Retries a failed deepfake detection analysis
        """
        # Verify the post exists and user has permissions
        post = get_object_or_404(Post, id=post_id)

        # Check if user has permission to retry this post's analysis
        if not request.user.is_staff and post.user != request.user:
            return Response(
                {"detail": "You do not have permission to retry this analysis"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            analysis = ImageAnalysis.objects.get(post_id=post_id)

            # Check if this analysis can be retried
            if analysis.status != 'failed':
                return Response(
                    {"error": "Only failed analyses can be retried"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update status
            analysis.status = 'pending'
            analysis.failure_reason = None
            analysis.save(update_fields=['status', 'failure_reason'])
            
            post.deepfake_status = 'analyzing'
            post.save(update_fields=['deepfake_status'])
            # Queue the analysis task

            task = process_image_analysis.delay(str(analysis.id))
            analysis.task_id = task.id
            analysis.save(update_fields=['task_id'])

            return Response({"status": "Analysis queued for retry"})

        except ImageAnalysis.DoesNotExist:
            return Response(
                {"detail": "No analysis found for this post"},
                status=status.HTTP_404_NOT_FOUND
            )

    def cancel_by_post(self, request, post_id=None):
        """
        Cancel analysis for a specific post

        Cancels a pending or processing deepfake detection analysis
        """
        # Verify the post exists and user has permissions
        post = get_object_or_404(Post, id=post_id)

        # Check if user has permission to cancel this post's analysis
        if not request.user.is_staff and post.user != request.user:
            return Response(
                {"detail": "You do not have permission to cancel this analysis"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            analysis = ImageAnalysis.objects.get(post_id=post_id)

            if analysis.status not in ['pending', 'processing']:
                return Response(
                    {"error": "Only pending or processing analyses can be cancelled"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # If there's a Celery task, attempt to revoke it
            if analysis.task_id:
                from purepost.celery import app
                app.control.revoke(analysis.task_id, terminate=True)

            analysis.status = 'failed'
            analysis.failure_reason = 'Cancelled by user'
            analysis.save(update_fields=['status', 'failure_reason'])

            return Response({"status": "Analysis cancelled"})

        except ImageAnalysis.DoesNotExist:
            return Response(
                {"detail": "No analysis found for this post"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False)
    def statistics(self, request):
        """
        Get statistics about the user's analyses

        Returns aggregated statistics about deepfake analyses
        """
        queryset = self.get_queryset()

        stats = {
            'total': queryset.count(),
            'by_status': dict(queryset.values_list('status')
                              .annotate(count=Count('status'))
                              .values_list('status', 'count')),
            'deepfakes_detected': queryset.filter(status='completed', is_deepfake=True).count(),
            'real_images': queryset.filter(status='completed', is_deepfake=False).count(),
            'average_score': queryset.filter(status='completed')
            .aggregate(avg_score=Avg('deepfake_score'))['avg_score'],
            'recent_analyses': ImageAnalysisSerializer(
                queryset.order_by('-created_at')[:5],
                many=True,
                context={'request': request}
            ).data
        }

        serializer = AnalysisStatisticsSerializer(stats)
        return Response(serializer.data)
