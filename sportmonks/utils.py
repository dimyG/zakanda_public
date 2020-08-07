import logging
import games.models
import games.naming
import gutils.utils
import constants

logger = logging.getLogger(__name__)


not_started_fetched_statuses = [constants.fetched_status['NS'].name, constants.fetched_status['TBA'].name,
                                constants.fetched_status['DELAYED'].name]

in_play_fetched_statuses = [constants.fetched_status['LIVE'].name, constants.fetched_status['HT'].name,
                            constants.fetched_status['ET'].name, constants.fetched_status['PEN_LIVE'].name,
                            constants.fetched_status['BREAK'].name]

void_fetched_statuses = [constants.fetched_status['CANCL'].name, constants.fetched_status['POSTP'].name,
                         constants.fetched_status['INT'].name, constants.fetched_status['ABAN'].name,
                         constants.fetched_status['SUSP'].name, constants.fetched_status['Deleted'].name]


def map_fetched_status_to_result_type(fetched_status):
    if not fetched_status:
        return
    status_map = {
        constants.fetched_status['FT'].name: games.models.Result.ft_result,
        constants.fetched_status['AET'].name: games.models.Result.et_result,
        constants.fetched_status['FT_PEN'].name: games.models.Result.pen_result,

        constants.fetched_status['CANCL'].name: games.models.Result.cancelled,
        constants.fetched_status['POSTP'].name: games.models.Result.postponed,
        constants.fetched_status['INT'].name: games.models.Result.interrupted,
        constants.fetched_status['ABAN'].name: games.models.Result.abandoned,
        constants.fetched_status['SUSP'].name: games.models.Result.suspended,
        constants.fetched_status['Deleted'].name: games.models.Result.deleted,
    }
    result_type = status_map.get(fetched_status)
    if not result_type:
        logger.warning("Fetched event's status: %s can't be mapped to a Result type", fetched_status)
    return result_type


def get_native_source():
    source_name = games.naming.source_names[3]
    try:
        source = games.models.Source.objects.get(name=source_name)
    except Exception as e:
        logger.warning('%s Probably the database has no zakanda schema or no data yet', e)
        source = None
    return source


def get_and_create_odd_trees_wrapper_sids(event_sids, source_name):
    logger.info("executing scheduled call to odds for %s event sids...", len(event_sids))
    # sportmonks.views can't import data_source.utils so this function was created instead
    import data_sources.utils
    try:
        source = games.models.Source.objects.get(name=source_name)
        events = []
        for sid in event_sids:
            # an sid can be connected with more than one events. For example postponed matches (brothers).
            # the call to get odds has meaning only for open events so I filter only these events
            # this could be avoided since the get_and_create_odd_trees extracts the (distinct) sids
            # from the given ids, and since the sids of brothers are the same there is no need to filter
            # only the open events. Open or closed the sid is the same.
            sid_events = games.models.Event.events_from_sid(sid, source, statuses=games.models.Event.open_event_statuses)
            events.extend(sid_events)
        event_ids = gutils.utils.ids(events)
        odds, offers, offer_odds = data_sources.utils.get_and_create_odd_trees([source_name], event_ids)
    except Exception as e:
        logger.error("%s", e)


def get_and_create_results_wrapper(event_ids, source_name):
    logger.info("executing scheduled call to results for %s events...", len(event_ids))
    import data_sources.utils
    # events are filtered and sorted again so that if some scheduled events have already been correctly settled
    # they are not called again.
    events = games.models.Event.objects.filter(id__in=event_ids)
    to_call_event_ids_sorted, ingredients = games.models.Event.order_for_result_call(events)
    data_sources.utils.get_and_create_results([source_name], to_call_event_ids_sorted)


bet365_name = 'bet365'