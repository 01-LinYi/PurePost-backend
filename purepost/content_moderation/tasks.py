from celery import shared_task
from django.utils import timezone
from .models import Post
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@shared_task
def publish_scheduled_posts():
    """Celery task to publish scheduled posts whose time has come"""
    now = timezone.now()
    
    try:
        with transaction.atomic():
            # Get posts ready to publish
            posts_to_publish = Post.objects.filter(
                is_scheduled=True,
                is_published=False,
                scheduled_time__lte=now
            ).select_for_update()
            
            if not posts_to_publish.exists():
                logger.info("No scheduled posts to publish at %s", now)
                return
            
            published_count = 0
            for post in posts_to_publish:
                post.status = 'published'
                post.is_published = True
                post.is_scheduled = False
                post.save()
                published_count += 1
                logger.info(
                    "Published scheduled post %d by user %s",
                    post.id,
                    post.user.username
                )
            
            logger.info(
                "Successfully published %d scheduled posts",
                published_count
            )
            
    except Exception as e:
        logger.error(
            "Error publishing scheduled posts: %s",
            str(e),
            exc_info=True
        )
        raise