import itertools
import django_rq
import pandas as pd
import logging
from functools import wraps
import requests
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.dispatch import Signal
from django.utils import timezone
from zakanda.settings import SessionKeys
import games.naming
import datetime
import pytz

logger = logging.getLogger(__name__)
total_bet_closed = Signal(providing_args=["total_bet"])


class DummyObject(object):
    pass


def empty_dataframe():
    return pd.DataFrame(columns=["C"])


def create_df(queryset, values, index, datetime_cols=None):
    """
    :param queryset:
    :param values:
    :param index:
    :param datetime_cols: list of columns that must be handled as datetime objects in pandas
    :return:
    """
    if not queryset.exists():
        return empty_dataframe()
    queryset_values = queryset.values(*values)
    df = pd.DataFrame.from_records(queryset_values, index=index)
    df.index = pd.to_datetime(df.index, utc=True)
    if datetime_cols:
        for datetime_col in datetime_cols:
            df[datetime_col] = pd.to_datetime(df[datetime_col], utc=True)
    df.sort_index(inplace=True)
    return df


def list_from_dict(related_calculated_bet_events_per_market):
    if not related_calculated_bet_events_per_market:
        return []
    bet_events_list = []
    for market_type, bet_events_list_per_market in related_calculated_bet_events_per_market.iteritems():
        bet_events_list.extend(bet_events_list_per_market)
    return bet_events_list


def show_in_money_mode(request, target_user):
    """
    returns True if the real values can be sent to the client. Takes into consideration
    both the target user's setting and the request user session setting
    The user that makes the request, can see the real currency stats of the target user only if the
    target user has his public setting as public. If he has it then the user that made the request
    can see target user's stats either in currency or in units depending on his toggle button
    saved in the session
    """
    # return False is omitted since by default python functions return None if nothing is defined
    try:
        target_user_profile = target_user.profile
        is_public = target_user_profile.public
        # logger.debug("target user %s is public: %s", target_user, is_public)
        if is_public:
            request_money_mode = request.session.get(SessionKeys.money_mode, None)
            # logger.debug("request user %s has setting in session %s", request.user, request_money_mode)
            if request_money_mode:
                return True
        else:
            if request.user == target_user:
                request_money_mode = request.session.get(SessionKeys.money_mode, None)
                if request_money_mode:
                    return True
    except AttributeError:
        logger.error("user %s has no associated profile!", target_user)


def to_datetime(date_strings, string_format='%Y-%m-%d-%H:%M'):
    dates = []
    for date_string in date_strings:
        try:
            date = datetime.datetime.strptime(date_string, string_format)
            date = date.replace(tzinfo=pytz.UTC)
        except Exception as e:
            logger.debug("%s", repr(e))
            date = None
        dates.append(date)
    return dates


def get_command_competition_gids(ids_string):
    if not ids_string:
        return
    gids = []
    for id in ids_string.split(','):
        gids.append(id)
    return gids


def get_command_sources(*args, **kwargs):
    """ Extracts the given source names of the command, checks if it is a valid source name
    and returns a list of valid source names. In case of invalid names the default source
    is used """

    default_source = games.naming.default_source_name

    source_str = kwargs.get('source', None)
    if source_str:
        logger.debug('source str: %s', source_str)
        original_source_names = source_str.split(',')
        source_names = []  # since strings are immutable
        for source_name in original_source_names:
            source_name = source_name.strip(' ')
            source_names.append(source_name)
    else:
        source_names = [default_source, ]

    # logger.debug('given source names: %s', source_names)

    valid_source_names = []
    for source_name in source_names:
        try:
            source_name_idx = games.naming.source_names.index(source_name)
            valid_source_names.append(games.naming.source_names[source_name_idx])
        except ValueError:
            valid_source_names.append(default_source)
    valid_source_names = set(valid_source_names)  # return only one default name in case of many invalid names
    valid_source_names = list(valid_source_names)
    # logger.debug('valid source names to be used: %s', valid_source_names)
    return valid_source_names


def get_command_dates(*args, **kwargs):
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    dates = [start_date, end_date]
    dates = to_datetime(dates)
    if None in dates:
        start_date, end_date = None, None
    else:
        start_date = dates[0]
        end_date = dates[1]

    if not start_date or not end_date:
        default_time_period = 3
        start_date = timezone.now()
        time_period = kwargs.get("days", default_time_period)
        try:
            time_period = int(time_period)
        except Exception:
            time_period = default_time_period
        delta = timezone.timedelta(days=time_period)
        end_date = start_date + delta
    return start_date, end_date


def ids(objects):
    """ It handles the case in which an object is None """
    object_ids = []
    for obj in objects:
        try:
            object_ids.append(obj.id)
        except Exception as e:
            logger.debug('%s', e)
            # object_ids.append(None)
    return object_ids


def cache_leader_board_data():
    """ It makes a get request to the leader board data url (it's view caches the data) """
    # I couldn't use the request.get_absolute_uri method in a dummy (test) request since the domain in this case
    # is "testserver"
    leader_board_url = reverse('user_accounts:leader_board')
    # custom_url = ''.join(['http://', Site.objects.get_current().domain, leader_board_url])  # for dev
    custom_url = ''.join([Site.objects.get_current().domain, leader_board_url])
    logger.debug('leaderboard url: %s, full url: %s', leader_board_url, custom_url)
    r = requests.get(custom_url)  # Does this update the cache if it is there already?
    status_code = r.status_code
    if status_code != 200:
        logger.error("leader board data wasn't stored in cache. Response Status code: %s" % str(status_code))


def to_chunks(entities, size):
    """ Splits the given entities to chunks of the given size. The last chunk
    contains the remaining entities """
    if len(entities) <= size:
        return [entities]
    entities = set(entities)
    chunks = []
    while entities:
        # Notice that the entities will not be in their original order
        chunk = set(itertools.islice(entities, size))
        entities = entities - chunk
        chunks.append(list(chunk))
    return chunks


def schedule_chunks(chunks, interval, func, **kwargs):
    # A source usually has a limit on the number of calls that you can make
    # for a specific endpoint within a time period. So we split the entities
    # in chunks of allowed size and schedule a call for each one of them.
    if not chunks:
        return
    scheduler = django_rq.get_scheduler('default')
    scheduled_time = timezone.now()
    counter = 0
    for chunk in chunks:
        counter += 1
        # scheduled_time += timezone.timedelta(minutes=1)
        scheduled_time += timezone.timedelta(hours=interval, minutes=5)
        logger.info("scheduling execution of %s on %s [%s of %s chunks]", func, scheduled_time,
                    counter, len(chunks))
        scheduler.schedule(
            scheduled_time=scheduled_time,
            func=func,
            args=[chunk],
            kwargs=kwargs,
            timeout=60 * 60 * 2,
            result_ttl=0,
            queue_name='default'
        )


def add_logging_level(level_name, level_num, method_name=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `level_name` becomes an attribute of the `logging` module with the value
    `level_num`. `method_name` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError('{} already defined in logging module'.format(level_name))
    if hasattr(logging, method_name):
        raise AttributeError('{} already defined in logging module'.format(method_name))
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError('{} already defined in logger class'.format(method_name))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)


add_logging_level("DATA_ERROR", 35, method_name=None)  # warning = 30, error = 40


def disable_for_loaddata(signal_handler):
    """
    Decorator that turns off signal handlers when loading fixture data.
    """
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        if kwargs['raw']:
            logger.info("Skipping signal for %s %s", args, kwargs)
            return
        signal_handler(*args, **kwargs)
    return wrapper


def get_user(user_id=None, username=None):
    """
    get a user either by a user id or by a username. The id is stronger than the username and will be preferred
    if both are given
    """
    # TODO low replace all raw get user calls with utils.get_user
    if not user_id and not username:
        logger.warning('No id or username were given. No user can be found')
        return

    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except Exception as e:
            logger.error("%s, user_id: %s", e, user_id)
            user = None
        return user

    # in this case only the username was given
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        logger.warning("User with username %s doesn't exist", username)
        user = None
    return user


def get_object(content_type, target_obj_id):
    model = content_type.model_class()
    try:
        obj = model.objects.get(pk=target_obj_id)
    except Exception as e:
        logger.error('%s', e)
        obj = None
    return obj


def extract_args(arg_string, default_value="All", delimiter=","):
    arg_list = []
    if arg_string:
        try:
            split = arg_string.split(delimiter)
            for arg in split:
                arg_list.append(arg)
        except Exception as e:
            arg_list = default_value
    else:
        arg_list = default_value
    return arg_list
