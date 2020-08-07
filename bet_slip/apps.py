__author__ = 'xene'

from django.apps import AppConfig


class BetSlipAppConfig(AppConfig):
    name = 'bet_slip'

    def ready(self):
        import bet_slip.signals
