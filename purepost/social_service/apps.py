from django.apps import AppConfig

class SocialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purepost.social_service'

    def ready(self):
        import purepost.social_service.signals  # noqa Import signals