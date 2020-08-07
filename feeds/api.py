__author__ = 'xene'

import logging
import feeds.models

logger = logging.getLogger(__name__)


def get_raw_from_bet_event(bet_event):
    event = bet_event.event
    market_type = bet_event.market_type
    choice = bet_event.selection.choice
    try:
        raw_bet_event = feeds.models.RawBetEvent.objects.get(
            event=event, market_type=market_type, choice=choice
        )
    except feeds.models.RawBetEvent.DoesNotExist:
        logger.error("raw_bet_event for bet_event %s doesn't exist in the db", bet_event)
        raw_bet_event = None
    except feeds.models.RawBetEvent.MultipleObjectsReturned:
        logger.error("identical raw_bet_events for bet_event %s exist in the db", bet_event)
        raw_bet_event = None
    return raw_bet_event


def create_bet_event_zakanda_activities(user_id, total_bet, bet_events, num_bet_events):
    logger.debug("creating bet_event zakanda activities...")
    zakanda_activities = []
    for bet_event in bet_events:
        event = bet_event.event
        raw_bet_event, created = feeds.models.RawBetEvent.objects.get_or_create(
            event=event, market_type=bet_event.market_type, choice=bet_event.selection.choice
        )
        if not raw_bet_event:
            logger.error("raw_bet_event for %s doesn't exist, bet_event zakanda activity wasn't created!", bet_event)
            return
        try:
            zakanda_activity, created = feeds.models.BetEventActivity.objects.get_or_create(
                actor_id=user_id, object=raw_bet_event, bet_event=bet_event,
                total_bet=total_bet, event=event, num_bet_events=num_bet_events)
            if created:
                zakanda_activities.append(zakanda_activity)
        except:
            logger.error("bet event zakanda activity for %s wasn't created!", bet_event)
    return zakanda_activities


def create_total_bet_zakanda_activity(user_id, total_bet, num_bet_events):
    logger.debug("creating total_bet zakanda activity...")
    tb_activity, created = feeds.models.TotalBetActivity.objects.get_or_create(
        actor_id=user_id, object_id=total_bet.id, num_bet_events=num_bet_events
    )
    if not created:
        return
    return tb_activity