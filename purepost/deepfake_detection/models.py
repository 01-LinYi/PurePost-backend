from django.db import models
import uuid
from django.conf import settings
from purepost.content_moderation.models import Post


class ImageAnalysis(models.Model):
    """
    Stores deepfake detection analysis results for images
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Reference to Post model
    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        null=True,
        related_name='deepfake_analysis'
    )

    # Analysis results
    is_deepfake = models.BooleanField(
        default=False, help_text="Final classification result")
    deepfake_score = models.FloatField(
        null=True, blank=True, help_text="Confidence score for deepfake class")
    real_score = models.FloatField(
        null=True, blank=True, help_text="Confidence score for real class")
    processing_time = models.FloatField(
        null=True, blank=True, help_text="Processing time in seconds")
    raw_result = models.JSONField(
        null=True, blank=True, help_text="Raw analysis result JSON")

    # Status tracking
    STATUS_CHOICES = [
        ('pending', 'Pending Analysis'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(
        blank=True, null=True, help_text="Reason for failure if status is 'failed'")
    task_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Celery task ID")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When analysis was completed")

    class Meta:
        verbose_name = "Image Analysis"
        verbose_name_plural = "Image Analyses"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_deepfake']),
        ]

    def __str__(self):
        """String representation of the analysis"""
        status_str = dict(self.STATUS_CHOICES).get(self.status, self.status)
        if self.status == 'completed':
            result = "Deepfake" if self.is_deepfake else "Real"
            return f"Analysis {self.post_id if hasattr(self, 'post_id') else self.id} - {result} ({self.deepfake_score:.2f})"
        return f"Analysis {self.post_id if hasattr(self, 'post_id') else self.id} - {status_str}"
