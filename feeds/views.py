import logging
import json
from django.template.response import TemplateResponse
from django.views.generic import DetailView
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from stream_django.feed_manager import feed_manager
from stream_django.enrich import Enrich
from stream_django.client import stream_client
from djpjax import pjaxtend
from zakanda.utils import cbv_pjaxtend
import feeds.models
import feeds.utils
import games.models
import zakanda.db
import zakanda.utils
from zakanda.settings import SessionKeys, FeedNames


logger = logging.getLogger(__name__)


def stream_user_data(request):
    user = request.user
    user_data = []
    if user.is_authenticated():
        stream_token = request.session.get(SessionKeys.stream_notification_token, None)
        if not stream_token:
            logger.error("stream token for logged in user doesn't exist in the session!")
        user_data = [user.id, stream_token]
    else:
        logger.debug("user is not logged in")
    return HttpResponse(json.dumps(user_data), content_type="application/json")


@never_cache    # You had a new notification but chrome returned the cached page which didn't contained the new message
@pjaxtend()
def user_notification_timeline(request, user_id):
    # todo high don't allow others to see the notifications of another user by changing the url (same with tips)
    # TODO high more button to load the next activities
    # I use the low level client (stream_client) instead of the high level feedmanager of the stream django app
    # without specific reason so I can use the feedmanager instead
    get_activities_num = 80
    per_page = 12
    user_notification_feed = stream_client.feed(FeedNames.notification, user_id)
    # it seems that first the activities are collected and then they are marked as seen. This way I can
    # check if an activity is currently seen or not
    activities = user_notification_feed.get(limit=get_activities_num, mark_seen=True, mark_read=True)['results']
    # next_activities = user_notification_feed.get(limit=get_activities_num, id_lt=activities[-1]['id'])['results']
    enricher = Enrich(fields=['actor', 'object', 'bet_event', 'total_bet', 'event'])
    enriched_activities = enricher.enrich_aggregated_activities(activities)
    paginator = Paginator(enriched_activities, per_page)
    enriched_activities = zakanda.utils.paginate(request, paginator, enriched_activities)
    context = {'enriched_activities': enriched_activities, 'not_started': games.models.Event.not_started}
    return TemplateResponse(request, 'feeds/timeline.html', context)


@never_cache
@pjaxtend()
def user_aggregated_timeline(request, user_pk):
    get_activities_num = 80
    per_page = 15
    user_aggr_timeline = stream_client.feed(FeedNames.timeline_aggregated, user_pk)
    activities = user_aggr_timeline.get(limit=get_activities_num)['results']
    # logger.debug("activities: %s", activities['activities'])
    enricher = Enrich(fields=['actor', 'object', 'bet_event', 'total_bet', 'event'])
    enriched_activities = enricher.enrich_aggregated_activities(activities)
    paginator = Paginator(enriched_activities, per_page)
    enriched_activities = zakanda.utils.paginate(request, paginator, enriched_activities)
    feeds.utils.print_enriched_aggr_activities(enriched_activities)
    context = {'enriched_activities': enriched_activities, 'not_started': games.models.Event.not_started}
    return TemplateResponse(request, 'feeds/timeline.html', context)


def add_isopen_to_tb_enriched_activities(enriched_activities):
    """
    It processes the enriched activity objects the verb of which is the one used for total_bet activities.
    It creates a "is_open" key in the enriched activities. This is done in order to show in the timeline only
    the total_bet_activities that involve open total_bets
    (The bet_event activities are checked in the template (if its open or not))
    """
    for activity in enriched_activities:
        if activity.get("verb", None) == feeds.models.TotalBetActivity.default_verb:
            total_bet = activity.get("object", None)
            if total_bet:
                logger.debug("total bet id %s", total_bet.id)
                if total_bet.status == games.models.TotalBet.open:
                    activity.__setitem__("is_open", True)
                else:
                    activity.__setitem__("is_open", False)


@never_cache
@pjaxtend()
def user_timeline(request, user_pk):
    get_activities_num = 80
    per_page = 15
    enricher = Enrich(fields=['actor', 'object', 'bet_event', 'total_bet', 'event'])
    logger.debug("getting timeline feed...")
    user_timeline = stream_client.feed(FeedNames.timeline, user_pk)
    # we collect a number of activities and then we can filter or paginate them as we want
    activities = user_timeline.get(limit=get_activities_num)['results']
    # next_activities = user_timeline.get(limit=50, id_lt=activities[-1]['id'])['results']
    # enriched activities is a list of stream_django.enrich.EnrichedActivity instances (they have __getitem__, __iter__)
    enriched_activities = enricher.enrich_activities(activities)
    # # add_isopen_to_tb_enriched_activities(enriched_activities)
    paginator = Paginator(enriched_activities, per_page)
    enriched_activities = zakanda.utils.paginate(request, paginator, enriched_activities)
    # enriched_activities_2 = enricher.enrich_activities(next_activities)
    enriched_activities_2 = None
    # # add_isopen_to_tb_enriched_activities(enriched_activities_2)

    context = {'enriched_activities': enriched_activities, 'enriched_activities_2': enriched_activities_2, 'not_started': games.models.Event.not_started}
    return TemplateResponse(request, 'feeds/timeline.html', context)


def user_activities(user):
    user_id = user.id
    feed_manager.get_user_feed(user_id)
    timeline_aggregated = feed_manager.get_news_feed(user_id)[FeedNames.timeline_aggregated]
    # feed_manager.follow_user(request.user.id, target_user)


class RawBetEventDetailView(DetailView):
    template_name = 'feeds/raw_bet_event_detail.html'
    model = feeds.models.RawBetEvent
    context_object_name = 'raw_bet_event'

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(RawBetEventDetailView, self).get(request, *args, **kwargs)
        return resp