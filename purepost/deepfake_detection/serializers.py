from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ImageAnalysis

User = get_user_model()


class ImageAnalysisSerializer(serializers.ModelSerializer):
    """
    Basic serializer for ImageAnalysis model
    Used for list views and creation endpoints
    """
    processing_time_formatted = serializers.SerializerMethodField()
    post_user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ImageAnalysis
        fields = [
            'id', 'post', 'post_user',
            'status', 'is_deepfake', 'deepfake_score',
            'processing_time', 'processing_time_formatted',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 'is_deepfake', 'deepfake_score',
            'processing_time', 'processing_time_formatted',
            'created_at', 'updated_at', 'completed_at'
        ]

    def get_processing_time_formatted(self, obj):
        """Format processing time in milliseconds for display"""
        if obj.processing_time is None:
            return None

        # Convert to milliseconds and format
        ms = obj.processing_time * 1000
        if ms < 1000:
            return f"{ms:.1f} ms"
        else:
            return f"{ms/1000:.2f} s"

    def get_post_user(self, obj):
        """Get the username of the post owner"""
        if obj.post and obj.post.user:
            return obj.post.user.username
        return None


class ImageAnalysisDetailSerializer(ImageAnalysisSerializer):
    """
    Detailed serializer for ImageAnalysis model
    Used for detailed view of a single analysis
    Includes full result data and additional metadata
    """
    confidence_level = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta(ImageAnalysisSerializer.Meta):
        fields = ImageAnalysisSerializer.Meta.fields + [
            'real_score', 'raw_result', 'failure_reason',
            'task_id', 'confidence_level', 'status_display'
        ]
        read_only_fields = fields

    def get_confidence_level(self, obj):
        """Get human-readable confidence level based on deepfake score"""
        if obj.status != 'completed' or obj.deepfake_score is None:
            return None

        score = obj.deepfake_score

        if score > 0.9:
            return "Very High"
        elif score > 0.75:
            return "High"
        elif score > 0.6:
            return "Moderate"
        elif score > 0.4:
            return "Low"
        else:
            return "Very Low"

    def get_status_display(self, obj):
        """Get human-readable status"""
        status_map = {
            'pending': 'Queued for Analysis',
            'processing': 'Analysis in Progress',
            'completed': 'Analysis Complete',
            'failed': 'Analysis Failed'
        }
        return status_map.get(obj.status, obj.status)

    def to_representation(self, instance):
        """Add additional processing for raw_result if available"""
        data = super().to_representation(instance)

        # Format raw_result for better display if it exists
        if instance.raw_result and isinstance(instance.raw_result, dict):
            # Add processing time from microservice if available
            if 'processing_time' in instance.raw_result:
                data['model_processing_time'] = instance.raw_result.get(
                    'processing_time')
                data['model_processing_time_formatted'] = f"{instance.raw_result.get('processing_time', 0) * 1000:.1f} ms"

            # Extract any other useful metrics from raw_result
            if 'predictions' in instance.raw_result:
                data['all_predictions'] = instance.raw_result.get(
                    'predictions', [])

        return data


class AnalysisStatisticsSerializer(serializers.Serializer):
    """
    Serializer for analysis statistics
    Used for the statistics endpoint
    """
    total = serializers.IntegerField()
    by_status = serializers.DictField(child=serializers.IntegerField())
    deepfakes_detected = serializers.IntegerField()
    real_images = serializers.IntegerField()
    average_score = serializers.FloatField(allow_null=True)
    recent_analyses = ImageAnalysisSerializer(many=True)

    def to_representation(self, instance):
        """Add formatted percentages and additional statistics"""
        data = super().to_representation(instance)

        # Calculate percentages if we have completed analyses
        total_completed = data['deepfakes_detected'] + data['real_images']
        if total_completed > 0:
            data['deepfake_percentage'] = round(
                (data['deepfakes_detected'] / total_completed) * 100, 1)
            data['real_percentage'] = round(
                (data['real_images'] / total_completed) * 100, 1)
        else:
            data['deepfake_percentage'] = 0
            data['real_percentage'] = 0

        # Add status distribution percentages
        if data['total'] > 0:
            data['status_distribution'] = {
                status: {
                    'count': count,
                    'percentage': round((count / data['total']) * 100, 1)
                }
                for status, count in data['by_status'].items()
            }
        else:
            data['status_distribution'] = {}

        return data
