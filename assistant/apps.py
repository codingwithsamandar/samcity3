from django.apps import AppConfig


class AssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'assistant'
    verbose_name = 'AI yordamchi'

    def ready(self):
        # Tool modullarini reyestrga yig'amiz (registry). Django ishga tushganda
        # bir marta chaqiriladi. Xatoga chidamli — birortasi buzilsa ham sayt
        # ishlayveradi (agent shunchaki o'sha tool'siz qoladi).
        try:
            from .tools import load_all
            load_all()
        except Exception:
            import logging
            logging.getLogger('assistant').exception('tool reyestri yuklanmadi')
