from django.apps import AppConfig


class SkrillConfig(AppConfig):
    name = 'skrill'

    def ready(self):
        import skrill.signals
