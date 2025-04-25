# purepost/management/commands/publish_scheduled_posts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from purepost.content_moderation.models import Post
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Continuously checks for and publishes scheduled posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon (continuously)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Check interval in seconds (default: 60)',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit',
        )

    def handle(self, *args, **options):
        is_daemon = options['daemon']
        run_once = options['once']
        interval = options['interval']
        
        if run_once:
            self.stdout.write(self.style.SUCCESS('Running post publishing once'))
            self._publish_scheduled_posts()
            return
            
        if is_daemon:
            self.stdout.write(self.style.SUCCESS(f'Starting daemon to publish posts every {interval} seconds'))
            
            try:
                while True:
                    self._publish_scheduled_posts()
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS('Stopped post publishing daemon'))
        else:
            self._publish_scheduled_posts()
    
    def _publish_scheduled_posts(self):
        now = timezone.now()
        
        # Use select_for_update() to avoid race conditions
        try:
            posts_to_publish = Post.objects.filter(
                status='scheduled',
                scheduled_for__lte=now
            )
            
            count = posts_to_publish.count()
            
            if count > 0:
                posts_to_publish.update(status='published')
                
                # Update the created_at field for each post separately
                for post in posts_to_publish:
                    Post.objects.filter(id=post.id).update(created_at=post.scheduled_for)
            
                
                self.stdout.write(self.style.SUCCESS(f'Published {count} scheduled posts'))
            else:
                self.stdout.write('No scheduled posts to publish at this time')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error publishing posts: {e}'))