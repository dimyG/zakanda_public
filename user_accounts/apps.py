__author__ = 'xene'

from django.apps import AppConfig


class UserAccountsAppConfig(AppConfig):
    name = 'user_accounts'

    def ready(self):
        import user_accounts.signals
