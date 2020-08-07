import logging
from django.core.cache import cache     # this is the default cache
from django_rq import job
import gutils.views
from bet_statistics.views import abs_profile_stats_data, norm_profile_stats_data, calc_user_total_bets_df, \
    calculate_total_bets_stats, norm_events_table_data, abs_events_table_data, percent_events_table_data
import bet_statistics.utils
from gutils.utils import get_user
from user_accounts.models import BasicStats

logger = logging.getLogger(__name__)


@job("default", result_ttl=0)
def update_abs_and_norm_profile_data(user_id):
    """ updates the cached abs and norm profile stats """

    logger.debug('updating cached user profile stats...')
    args = (user_id,)
    kwargs = {'start_date': None, 'end_date': None}
    abs_func_key = gutils.views.build_cache_key(abs_profile_stats_data, args, kwargs)
    norm_func_key = gutils.views.build_cache_key(norm_profile_stats_data, args, kwargs)

    # logger.debug("abs_func_key: %s", abs_func_key)
    # logger.debug("norm_func_key: %s", norm_func_key)

    # delete = cache.delete_many([abs_func_key, norm_func_key])
    # logger.debug("del user profile abs and norm %s", delete)
    del_abs = cache.delete(abs_func_key)
    del_norm = cache.delete(norm_func_key)
    logger.debug('deleting abs and norm keys: %s %s', del_abs, del_norm)

    # recalculate stats and set them in cache
    abs_profile_stats_data(user_id, start_date=None, end_date=None)
    norm_profile_stats_data(user_id, start_date=None, end_date=None)


def update_bev_dfs(user_id):
    """
    Important: The abs and norm functions use the calc_user_total_bets_df function (including open tbs) to collect
    the total_bets of the user, so the cache update of the bet events df must be done AFTER the update of the
    total bet df with open tbs. So it can't be a separate job since we can't be sure what job will be executed first
    """
    logger.debug("updating cached bevs df of user %s...", user_id)
    args = (user_id,)
    kwargs = {'start_date': None, 'end_date': None}

    abs_func_key = gutils.views.build_cache_key(abs_events_table_data, args, kwargs)
    norm_func_key = gutils.views.build_cache_key(norm_events_table_data, args, kwargs)
    percent_func_key = gutils.views.build_cache_key(percent_events_table_data, args, kwargs)

    del_abs = cache.delete(abs_func_key)
    del_norm = cache.delete(norm_func_key)
    del_percent = cache.delete(percent_func_key)
    logger.debug("delete abs bevs: %s, delete norm bevs: %s, delete percent bevs: %s", del_abs, del_norm, del_percent)

    # delete = cache.delete_many([abs_func_key, norm_func_key, percent_func_key])
    # logger.debug("abs, normalized and percentized bevs df deleted: %s", delete)

    abs_events_table_data(*args, **kwargs)
    norm_events_table_data(*args, **kwargs)
    percent_events_table_data(*args, **kwargs)


def update_tbs_df_with_open(user_id):
    """
    Called on tb closed and tb transaction on commit signals
    * On total bet closed signal it is not called as background job since it is already in a job
    (Maybe this is not a reason not to add it a new job. There are no ordering constraints for this function execution)
    * On tb transaction it is called as a job
    """
    logger.debug("updating cached tbs df with open tbs for user %s...", user_id)
    if not user_id:
        return
    args = (user_id,)
    kwargs = {'exclude_open': False, 'start_date': None, 'end_date': None}
    func_key = gutils.views.build_cache_key(calc_user_total_bets_df, args, kwargs)
    delete = cache.delete(func_key)
    logger.debug("tbs df with open delete: %s", delete)
    new_user_open_tbs, new_user_open_tbs_df = calc_user_total_bets_df(*args, **kwargs)
    # logger.debug("new_user_open_tbs: %s", new_user_open_tbs)
    # logger.debug("new_user_open_tbs_df: %s", new_user_open_tbs_df)
    return new_user_open_tbs_df


def cache_all_stats(tbs_df, user_id):
    """ currently no abs stats are calculated in the first place? Check it """
    # todo no abs stats are calculated in the first place?
    calculate_total_bets_stats(tbs_df, user_id)  # calc the abs stats
    bet_statistics.utils.normalize_tbs_df(tbs_df)
    calculate_total_bets_stats(tbs_df, user_id)  # calc the norm stats


def delete_all_cached_stats(user_id):
    """ The stats are always calculated from the tbs_df with open bets """
    args = (user_id,)
    kwargs = {'exclude_open': False, 'start_date': None, 'end_date': None}
    cached_user_tbs, cached_user_tbs_df = calc_user_total_bets_df(*args, **kwargs)  # get the cached version
    delete_cached_stats(cached_user_tbs_df, user_id)  # delete the abs cached stats
    bet_statistics.utils.normalize_tbs_df(cached_user_tbs_df)
    delete_cached_stats(cached_user_tbs_df, user_id)  # delete the norm cached stats


def delete_cached_stats(tbs_df, user_id):
    args = (tbs_df, user_id)
    kwargs = {}
    func_key = gutils.views.build_cache_key(calculate_total_bets_stats, args, kwargs)
    delete = cache.delete(func_key)
    logger.debug("del tbs stats %s", delete)


@job("default", result_ttl=0, timeout=60*60*1)
def update_tbs_df_without_open(user_id):
    logger.debug("updating cached closed tbs df for user %s...", user_id)
    if not user_id:
        return
    args = (user_id,)
    kwargs = {'exclude_open': True, 'start_date': None, 'end_date': None}
    func_key = gutils.views.build_cache_key(calc_user_total_bets_df, args, kwargs)
    delete = cache.delete(func_key)     # delete the cached tbs df
    logger.debug("tbs df with open delete %s", delete)
    new_user_tbs, new_user_tbs_df = calc_user_total_bets_df(*args, **kwargs)


def update_stored_stats(user_id):
    """ it updates the basic stats stored in db with the result of the stats calculation which is cached
    so the cached stats must be updated first """
    if not user_id:
        return
    user = get_user(user_id)
    if not user:
        return
    try:
        user.basic_stats.update()
    except Exception as e:
        # if basic stats doesn't exist for this user
        basic_stats, created = BasicStats.objects.get_or_create(user=user)
        basic_stats.update()
    return


@job("default", result_ttl=0, timeout=2*60*60)
def update_user_cache(user_id):
    # todo rename it to upd_cache_and_stats and create 2 function for each action
    """
    Profile stats abs and norm calculations, use the total_bets_df which is also cached. So if we want to calculate
    the new profile stats we must first update the cached total_bets_df so the abs and norm calculations will use
    the new value.
    """
    logger.debug('updating user %s cache...', user_id)
    update_tbs_df_without_open(user_id)
    delete_all_cached_stats(user_id)  # must be before tbs df with open update
    tbs_df = update_tbs_df_with_open(user_id)
    cache_all_stats(tbs_df, user_id)  # it must be after tbs df with open update
    update_bev_dfs(user_id)  # it must be after tbs df with open update (see description)
    update_abs_and_norm_profile_data(user_id)
    update_stored_stats(user_id)  # it must be after cache_all_stats
