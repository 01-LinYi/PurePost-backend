from django.apps import AppConfig


class UserServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purepost.user_service'

    def ready(self):
        import purepost.user_service.signals  # noqa Required for signal registration
