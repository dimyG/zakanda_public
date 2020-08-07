__author__ = 'xene'

from django.apps import AppConfig
from django.contrib.auth.models import User


class GamesConfig(AppConfig):
    # Have in mind that the User can be accessed from games.models.User. Why?
    name = 'games'

    def ready(self):
        from actstream import registry
        # registry.register(self.get_model('User'))
        registry.register(User)
        import games.signals
