# content_moderation/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from .models import Post
import logging

logger = logging.getLogger(__name__)

def publish_scheduled_posts():
    """
    Task to publish posts that have reached their scheduled publication time
    """
    now = timezone.now()
    
    # Find all posts scheduled for publication now or earlier
    posts_to_publish = Post.objects.filter(
        status='scheduled',
        scheduled_for__lte=now
    )
    
    count = posts_to_publish.count()
    
    if count > 0:
        # Update all posts at once
        posts_to_publish.update(status='published')
        
        # Log the IDs of published posts for audit purposes
        post_ids = list(posts_to_publish.values_list('id', flat=True))
        logger.info(f"Published {count} scheduled posts. Post IDs: {post_ids}")
        
        return f"Successfully published {count} scheduled posts"
    else:
        logger.debug("No scheduled posts to publish at this time")
        return "No scheduled posts to publish at this time"

def start():
    """
    Start the scheduler.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Add job: run every minute
    scheduler.add_job(
        publish_scheduled_posts,
        'interval', 
        minutes=1,
        id='publish_scheduled_posts',
        replace_existing=True,
        max_instances=1  # Prevent multiple instances of the job from running concurrently
    )
    
    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully!")