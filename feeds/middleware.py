__author__ = 'xene'
from stream_django.client import stream_client
from zakanda.settings import FeedNames
from zakanda.settings import SessionKeys


class StreamTokenMiddleware():
    """
    It calls Stream to create a token for the user's notification feed. The token is stored in the session.
    It is used to connect to Stream from the client side using javascript.
    """
    def process_request(self, request):
        if request.user.is_authenticated():
            stream_token = request.session.get(SessionKeys.stream_notification_token, None)
            if not stream_token:
                user_notification_feed = stream_client.feed(FeedNames.notification, request.user.id)
                token = user_notification_feed.token
                request.session[SessionKeys.stream_notification_token] = token
