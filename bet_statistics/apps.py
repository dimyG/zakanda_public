__author__ = 'xene'

from django.apps import AppConfig


class BetStatisticsAppConfig(AppConfig):
    name = 'bet_statistics'

    def ready(self):
        import bet_statistics.signals