from django.apps import AppConfig

class ContentModerationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purepost.content_moderation'

    def ready(self):
        # Prevent scheduler from running twice or during migrations
        if 'runserver' in sys.argv:
            # Only import and start scheduler when the runserver command is used
            from . import scheduler
            scheduler.start()