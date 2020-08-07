from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import login as django_login
from django.http import Http404


class NoNewUsersAccountAdapter(DefaultAccountAdapter):
    """
    Adapter to disable allauth new signups
    Used at equilang/settings.py with key ACCOUNT_ADAPTER

    https://django-allauth.readthedocs.io/en/latest/advanced.html#custom-redirects """

    def is_open_for_signup(self, request):
        """
        Checks whether or not the site is open for signups.

        Next to simply returning True/False you can also intervene the
        regular flow by raising an ImmediateHttpResponse
        """
        return False

    def login(self, request, user):
        allowed_usernames = ['user1', 'lui', 'yeolo', 'zakanda_support']
        allowed_ids = [1, 3, 271]
        if user.username not in allowed_usernames:
            raise Http404

        # HACK: This is not nice. The proper Django way is to use an
        # authentication backend
        if not hasattr(user, 'backend'):
            user.backend \
                = "allauth.account.auth_backends.AuthenticationBackend"
        django_login(request, user)

