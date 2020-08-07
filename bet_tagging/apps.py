from django.apps import AppConfig


class BetTaggingAppConfig(AppConfig):
    name = 'bet_tagging'

    def ready(self):
        from actstream import registry
        from models import BetTag
        # registry.register(self.get_model('BetTag'))
        registry.register(BetTag)
        import bet_tagging.signals
