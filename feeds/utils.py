from __future__ import unicode_literals
import logging
import pandas as pd
from collections import defaultdict
# from stream_django.client import stream_client
# from zakanda.settings import FeedNames
import feeds.models
from games.models import TotalBet


logger = logging.getLogger(__name__)


def empty_dataframe():
    return pd.DataFrame(columns=["C"])


def print_enriched_aggr_activities(enriched_activities):
    logger.debug('enriched activities %s', len(enriched_activities))
    for aggr_activity in enriched_activities:
        logger.debug('--- aggregated activity ---')
        for key in aggr_activity:
            # aggr_activity dict has these keys:
            # activities, group, activity_count, created_at, updated_at, actor_count, verb, id
            if key == 'activities':
                # these are the activities which the aggregated info (the aggr activity) is created from
                logger.debug("consists of %s activities", len(aggr_activity[key]))
                for activity in aggr_activity[key]:
                    logger.debug(" - activity -")
                    logger.debug("activity's actor: %s", activity.activity_data['actor'])
            else:
                logger.debug("%s: %s", key, aggr_activity[key])


def total_bet_stream_activity_data(actor_id, verb, object_id, foreign_id, num_bet_events, time):
    activity_data = {
        'actor': 'auth.User:{}'.format(actor_id),
        'verb': verb,
        'object': 'games.TotalBet:{0}'.format(object_id),
        'foreign_id': 'feeds.TotalBetActivity:{0}'.format(foreign_id),
        'time': time,
        'num_bet_events': num_bet_events,
        # 'to': ['notification:chris', 'tag:amsterdam'],
        # 'message': 'Hi @chris, the coldplay concert was totally amazing #amsterdam'
    }
    return activity_data


def users_to_notify(total_bet):
    bet_group = total_bet.bet_tag
    recipients = bet_group.get_recipients(in_app=True)
    return recipients


def create_to_list(users):
    """ creates the recipients list in the form that the getstream api expects it ( notification + user_id ) """
    if not users:
        return
    to_list = []
    for user in users:
        user_id = user.id
        slug = 'notification:'+str(user_id)
        to_list.append(slug)
    logger.debug('to list: %s', to_list)
    return to_list


def bet_event_stream_activity_data(actor_id, verb, object_id, foreign_id, bet_event_id, total_bet_id, event_id, num_bet_events, time):
    activity_data = {
        'actor': 'auth.User:{}'.format(actor_id),
        'verb': verb,
        'object': 'feeds.RawBetEvent:{0}'.format(object_id),
        'foreign_id': 'feeds.BetEventActivity:{0}'.format(foreign_id),
        'bet_event': 'games.BetEvent:{0}'.format(bet_event_id),
        'total_bet': 'games.TotalBet:{0}'.format(total_bet_id),
        'event': 'games.Event:{0}'.format(event_id),
        'num_bet_events': num_bet_events,
        'time': time,
        # 'to': ['notification:chris', 'tag:amsterdam'],
        # message is a custom field.add as many custom fields as you'd like
        # 'message': 'Hi @chris, the coldplay concert was totally amazing #amsterdam'
    }
    return activity_data


def add_notifications(activity_data, total_bet):
    if not activity_data or not total_bet:
        return activity_data
    recipients = users_to_notify(total_bet)
    recipients_list = create_to_list(recipients)
    if recipients_list:
        activity_data['to'] = recipients_list
    return activity_data


def batch_add_activities(activities_data_per_tb):
    """
    :param activities_data_per_tb: Dictionary. Key is the actor_id and value is a list of activity_data items.
    An activity_data item is a dictionary with the values that the Stream activity will be created with.
    There can be many different activity_data types
    :return: the add_activities response is a dictionary {'duration':5ms, 'activities':[ {}, {}, ... {} ]}
    """
    if not activities_data_per_tb:
        logger.error("No activities_data to sync!")
        return
    stream_activities = []
    for total_bet_id, activities_data in activities_data_per_tb.iteritems():
        logger.debug("batch adding activities for total bet %s...", total_bet_id)

        total_bet = TotalBet.get(total_bet_id)
        if not total_bet:
            logger.error("Activities not synced! Can't extract total bet for id %s", total_bet_id)
            continue
        # actor_id = total_bet.user.id
        bet_group = total_bet.bet_tag
        selected_feed = bet_group.get_feed()
        if not selected_feed:
            logger.error("Activities not synced! Can't extract feed for bet group %s", bet_group)
            continue
        response = selected_feed.add_activities(activities_data)
        user_stream_activities = response.get("activities", None)
        # logger.debug("user_activity_ids: %s [%s]", len(user_stream_activities), user_stream_activities)
        if user_stream_activities:
            stream_activities.extend(user_stream_activities)
    return stream_activities


def sync_activities_to_stream(activities, batch=True):
    """
    It syncs (adds) activities that exist in our db, to Stream.
    :param activities: List of our db activity instances. The activities can be of many
    types (BetEventActivity, TotalBetActivity etc.) and from many users
    :param batch: You can control if the activities will be synced in batch (all with one call) or not
    :return:
    """
    logger.info("syncing zakanda activities to Stream...")
    if not activities:
        logger.error("No activities to sync!")
        return
    stream_activities = []
    activities_data_per_tb = defaultdict(list)
    for activity in activities:
        if isinstance(activity, feeds.models.BetEventActivity):
            actor_id = activity.actor.id
            verb = activity.verb
            object_id = activity.object.id
            foreign_id = activity.id
            bet_event_id = activity.bet_event.id
            total_bet_id = activity.total_bet.id
            event_id = activity.event.id
            num_bet_events = activity.num_bet_events
            time = activity.created_at
            activity_data = bet_event_stream_activity_data(actor_id, verb, object_id, foreign_id,
                                                           bet_event_id, total_bet_id, event_id, num_bet_events, time)
            total_bet = TotalBet.get(total_bet_id)
            activity_data = add_notifications(activity_data, total_bet)
            if batch:
                activities_data_per_tb[total_bet_id].append(activity_data)
            else:
                bet_group = total_bet.bet_tag
                selected_feed = bet_group.get_feed()
                if not selected_feed:
                    logger.error("Activities not synced! Can't extract feed for bet group %s", bet_group)
                    continue
                stream_activity = selected_feed.add_activity(activity_data)
                stream_activities.append(stream_activity)
        # elif isinstance(activity, feeds.models.TotalBetActivity):
        #     actor_id = activity.actor.id
        #     verb = activity.verb
        #     object_id = activity.object.id
        #     foreign_id = activity.id
        #     num_bet_events = activity.num_bet_events
        #     time = activity.time
        #     activity_data = total_bet_stream_activity_data(actor_id, verb, object_id, foreign_id, num_bet_events, time)
        #     if batch:
        #         activities_data_per_actor[actor_id].append(activity_data)
        #     else:
        #         user_feed = stream_client.feed(FeedNames.user, actor_id)
        #         stream_activity = user_feed.add_activity(activity_data)
        #         stream_activities.append(stream_activity)
        else:
            logger.error("Unknown activity %s, no Stream activity will be created for it!", activity)
    if batch:
        stream_activities = batch_add_activities(activities_data_per_tb)
    logger.debug("%s stream activities were created successfully", len(stream_activities))
    return stream_activities


def df_from_bev_activities(bev_activities):
    if not bev_activities:
        logger.debug("0 bev_activities")
        return empty_dataframe(), None
    bev_activities_values = bev_activities.values('id', 'bet_event__id', 'object__id', 'bet_event__selection__selected_odd')
    bev_activities_df = pd.DataFrame.from_records(bev_activities_values)
    bev_activities_df.rename(columns={'id': 'bev_activity_id', 'bet_event__id': 'bet_event_id',
                              'object__id': 'raw_bev_id', 'bet_event__selection__selected_odd': 'selected_odd'}, inplace=True)
    # logger.debug("%s bev_activities were selected", len(bev_activities_values))
    return bev_activities_df, bev_activities_values


def popular_raw_bet_events(bet_events, number, bet_group_type):
    """ The Popular raw bet events from given bet events that belong to bet groups of the given bet_group_type """
    logger.debug("Getting Popular raw bet events from given bet events...")
    bev_activities = feeds.models.BetEventActivity.objects.filter(
        bet_event__in=bet_events, total_bet__bet_tag__type=bet_group_type)
    bev_activities_df, bev_activities_values = df_from_bev_activities(bev_activities)

    if bev_activities_df.empty:
        return
    value_counts = bev_activities_df['raw_bev_id'].value_counts()
    frequent_raw_bet_event_ids = value_counts.head(number).index
    raw_bev_id_list = frequent_raw_bet_event_ids.values.tolist()
    frequent_raw_bet_events = feeds.models.RawBetEvent.objects.filter(id__in=raw_bev_id_list)

    # logger.debug('bet id - frequency: %s', value_counts.head())

    for raw_bet_event in frequent_raw_bet_events:
        raw_id = raw_bet_event.id
        bev_frequency = value_counts.loc[raw_id]
        raw_bet_event.frequency = bev_frequency
        # logger.debug('bev %s is used in %s bets', raw_id, bev_frequency)
        # the odd of one of the bevs of a specific raw bev
        try:
            avg_selected_odd = bev_activities_df.loc[bev_activities_df['raw_bev_id'] == raw_id]['selected_odd'].mean()
        except Exception as e:
            logger.error("%s", e)
            avg_selected_odd = bev_activities_df.loc[bev_activities_df['raw_bev_id'] == raw_id]['selected_odd'].iloc[0]
        # logger.debug('sel: %s', selected_odd)
        raw_bet_event.selected_odd = avg_selected_odd
    return frequent_raw_bet_events
