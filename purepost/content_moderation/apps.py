from django.apps import AppConfig

class ContentModerationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purepost.content_moderation'

    def ready(self):
        import purepost.content_moderation.signals  # noqa Import signals