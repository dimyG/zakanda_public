__author__ = 'xene'

from django.apps import AppConfig


class FeedsAppConfig(AppConfig):
    name = 'feeds'

    def ready(self):
        import feeds.signals
