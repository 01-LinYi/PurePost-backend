import time
import logging
import traceback
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from .models import ImageAnalysis

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Container for deepfake detection results from microservice"""
    is_deepfake: bool
    deepfake_score: float
    real_score: float
    processing_time: float
    raw_data: Dict[str, Any]


@shared_task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    name="process_image_analysis"
)
def process_image_analysis(self, analysis_id: str) -> dict:
    """
    Process an image analysis request by sending it to the dfdetect-service.

    Args:
        analysis_id: UUID of the ImageAnalysis record

    Returns:
        dict: Results of the analysis
    """
    logger.info(f"Starting analysis for image {analysis_id}")
    start_time = time.time()

    try:
        # Get analysis record and mark as processing
        with transaction.atomic():
            analysis = ImageAnalysis.objects.select_for_update().get(id=analysis_id)

            if analysis.status != 'pending':
                logger.warning(
                    f"Analysis {analysis_id} is not pending (status: {analysis.status}), skipping")
                return {"status": analysis.status, "message": "Analysis was not in pending state"}

            analysis.status = 'processing'
            analysis.save(update_fields=['status', 'updated_at'])

        # Get image from Post
        if not analysis.post:
            _mark_analysis_failed(analysis, "No post associated with analysis")
            return {"status": "failed", "message": "No post associated with analysis"}

        # Here we assume the image is stored in the Post model
        # Implementation would depend on your storage model
        image_data = _retrieve_image(analysis.post)
        if not image_data:
            _mark_analysis_failed(analysis, "Failed to retrieve image")
            return {"status": "failed", "message": "Failed to retrieve image"}

        # Send to microservice for detection
        result = _call_detection_service(image_data)
        if not result:
            _mark_analysis_failed(
                analysis, "Deepfake detection service failed to process image")
            return {"status": "failed", "message": "Detection service failure"}

        # Update analysis with results
        total_processing_time = time.time() - start_time

        with transaction.atomic():
            analysis.refresh_from_db()

            if analysis.status == 'processing':
                analysis.is_deepfake = result.is_deepfake
                analysis.deepfake_score = result.deepfake_score
                analysis.real_score = result.real_score
                analysis.processing_time = result.processing_time
                analysis.raw_result = result.raw_data
                analysis.status = 'completed'
                analysis.completed_at = timezone.now()
                analysis.save()

                _post_process_analysis(analysis)

                logger.info(
                    f"Analysis {analysis_id} completed: is_deepfake={result.is_deepfake}, score={result.deepfake_score:.4f}")
                return {
                    "status": "completed",
                    "is_deepfake": result.is_deepfake,
                    "deepfake_score": result.deepfake_score,
                    "processing_time": total_processing_time,
                    "model_processing_time": result.processing_time
                }
            else:
                logger.warning(
                    f"Analysis {analysis_id} was not in processing state, skipping update")
                return {"status": analysis.status, "message": "Analysis was not in processing state"}

    except ImageAnalysis.DoesNotExist:
        logger.error(f"Analysis {analysis_id} not found")
        raise

    except Exception as e:
        logger.error(f"Error processing analysis {analysis_id}: {str(e)}")
        logger.debug(traceback.format_exc())

        try:
            analysis = ImageAnalysis.objects.get(id=analysis_id)
            _mark_analysis_failed(analysis, f"Processing error: {str(e)}")
        except Exception as inner_e:
            logger.error(f"Failed to mark analysis as failed: {str(inner_e)}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying analysis {analysis_id} ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        raise


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
    name="cleanup_stale_analyses"
)
def cleanup_stale_analyses():
    """
    Clean up analyses that have been stuck in 'processing' state for too long.
    """
    # Find analyses stuck in processing for more than 1 hour
    timeout = timezone.now() - timezone.timedelta(hours=1)
    stale_analyses = ImageAnalysis.objects.filter(
        status='processing',
        updated_at__lt=timeout
    )

    count = stale_analyses.count()
    if count > 0:
        logger.warning(f"Found {count} stale analyses, marking as failed")

        for analysis in stale_analyses:
            _mark_analysis_failed(analysis, "Analysis timed out")

    return {"cleaned_up": count}


@shared_task(
    bind=True,
    max_retries=1,
    name="check_microservice_health"
)
def check_microservice_health(self):
    """Check the health of the deepfake detection microservice"""
    try:
        url = f"{settings.DFDETECT_SERVICE_URL}/health"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            health_data = response.json()
            logger.info(
                f"Deepfake detection service is healthy: {health_data}")
            return {"status": "healthy", "details": health_data}
        else:
            logger.error(
                f"Deepfake detection service health check failed with status {response.status_code}")
            return {"status": "unhealthy", "details": {"status_code": response.status_code}}

    except Exception as e:
        logger.error(
            f"Failed to connect to deepfake detection service: {str(e)}")
        return {"status": "unreachable", "details": {"error": str(e)}}


def _retrieve_image(post) -> Optional[bytes]:
    """
    Retrieve image data from post

    Args:
        post: Post model instance containing the image

    Returns:
        bytes: Image data or None if retrieval failed
    """
    try:
        # Implementation depends on your storage backend
        # For example, assuming Post has an image field:
        if post.image:
            return post.image.read()

        logger.error(f"Image not found for post {post.id}")
        return None

    except Exception as e:
        logger.error(f"Error retrieving image for post {post.id}: {str(e)}")
        logger.debug(traceback.format_exc())
        return None


def _call_detection_service(image_data: bytes) -> Optional[DetectionResult]:
    """
    Send image to the deepfake detection microservice for analysis

    Args:
        image_data: Raw image bytes

    Returns:
        DetectionResult with detection results or None if service call failed
    """
    try:
        url = f"{settings.DFDETECT_SERVICE_URL}/predict"

        # Prepare multipart/form-data request with image
        files = {'file': ('image.jpg', image_data, 'image/jpeg')}

        # Set timeout to avoid hanging indefinitely
        response = requests.post(
            url, files=files, timeout=settings.DFDETECT_SERVICE_TIMEOUT)

        if response.status_code != 200:
            logger.error(
                f"Detection service returned error status {response.status_code}: {response.text}")
            return None

        # Parse response
        result = response.json()

        if not result.get('success'):
            logger.error(f"Detection service reported failure: {result}")
            return None

        # Extract predictions
        predictions = result.get('predictions', [])
        if not predictions:
            logger.error("Detection service returned no predictions")
            return None

        # Find deepfake and real scores
        deepfake_score = 0.0
        real_score = 0.0

        for pred in predictions:
            if pred['label'].lower() == 'deepfake':
                deepfake_score = pred['score']
            elif pred['label'].lower() == 'real':
                real_score = pred['score']

        # Determine if image is classified as deepfake
        is_deepfake = deepfake_score > real_score

        # Return structured result
        return DetectionResult(
            is_deepfake=is_deepfake,
            deepfake_score=deepfake_score,
            real_score=real_score,
            processing_time=result.get('processing_time', 0.0),
            raw_data=result
        )

    except requests.RequestException as e:
        logger.error(f"Error calling deepfake detection service: {str(e)}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error in detection service call: {str(e)}")
        logger.debug(traceback.format_exc())
        return None


def _mark_analysis_failed(analysis: ImageAnalysis, reason: str):
    """Mark analysis as failed and update post"""
    analysis.status = 'failed'
    analysis.failure_reason = reason
    analysis.save(update_fields=['status', 'failure_reason', 'updated_at'])
    
    # Update post status
    if analysis.post:
        try:
            analysis.post.deepfake_status = 'analysis_failed'
            analysis.post.save(update_fields=['deepfake_status'])
        except Exception as e:
            logger.error(f"Error updating post status: {str(e)}")
            
    logger.warning(f"Analysis {analysis.id} marked as failed: {reason}")


def _post_process_analysis(analysis: ImageAnalysis):
    """Perform post-processing after analysis completion"""
    if analysis.post:
        try:
            # Set appropriate deepfake status based on result and confidence
            if analysis.status == 'completed':
                if analysis.is_deepfake and analysis.deepfake_score >= settings.DEEPFAKE_THRESHOLD:
                    analysis.post.deepfake_status = 'flagged'
                    analysis.post.deepfake_score = analysis.deepfake_score
                else:
                    analysis.post.deepfake_status = 'not_flagged'
                    analysis.post.deepfake_score = analysis.deepfake_score
            else:
                # Should not happen normally but handles edge cases
                analysis.post.deepfake_status = 'analyzing'

            analysis.post.save(
                update_fields=['deepfake_status', 'deepfake_score'])
            logger.info(
                f"Updated post {analysis.post.id} with deepfake status: {analysis.post.deepfake_status}")
        except Exception as e:
            logger.error(
                f"Error updating post with deepfake results: {str(e)}")
