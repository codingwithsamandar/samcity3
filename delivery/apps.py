from django.apps import AppConfig


class DeliveryConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'delivery'
    verbose_name = 'Yetkazib berish'

    def ready(self):
        from . import signals  # noqa: F401
