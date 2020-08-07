# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# from games.models import get_bet_events, get_bet_events_from
from zakanda.db import get_bet_events, get_bet_events_from
import logging
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.http import Http404
from django.views.generic import ListView, DetailView
from django.template.response import TemplateResponse
from django.contrib.auth.models import User
from django.views.decorators.cache import cache_page
from djpjax import pjaxtend
from zakanda.settings import cache_time, NormalizationMethods
from zakanda.utils import cbv_pjaxtend  # DatetimeEncoder
from gutils.utils import get_user
import games.models
from feeds.models import RawBetEvent
import user_accounts.utils
import utils
import gutils.utils
from gutils.views import try_cache_first
import bet_tagging.models
import json
import pandas as pd
import numpy as np
from actstream.models import followers
# from itertools import izip
# import redis
# import django_rq
# from django_rq import job
# import requests

pd.options.display.width = 180
logger = logging.getLogger(__name__)


def market_types_from_total_bets(total_bets):
    pass


def calc_total_tbs_df_deposits(tbs_df):
    """
    # total_tag_deposits
    # it's the deposits made in this bet tag, until the time of the last closed bet. Any deposit made after that are not
    # taken into account. This might be convenient actually, since it shows what has happened.
    # Not what is about to happen. you can extract the stats for the deposits made for
    # the bets that are closed. If there are deposits for open bets, they must not be taken account into roi etc.
    # they affect the result.
    :return: total_tbs_deposits
        It is the sum of deposits made in the tags of the tbs that are processed. If the tbs_df contains only one tag
        then it is the deposits of that tag. (So you can make calculations on each tag)
    """
    if tbs_df.empty:
        return 0
    bet_tag_names = tbs_df['bet_tag_name'].unique()  # ndarrays
    # num_bet_tags = bet_tag_names.size
    total_tbs_deposits = 0
    for bet_tag_name in bet_tag_names:
        key = bet_tag_name + '_deposit_cumsum'
        total_tag_deposits = tbs_df[key].max()
        total_tbs_deposits += total_tag_deposits
    return total_tbs_deposits


def calculate_frequency(start_date, num_total_bets, num_days=7):
    """ Number of bets per week. The timeframe is between the first bet and now."""
    # logger.debug('df: %s, now: %s, %s', user_total_bets_df.index, timezone.now(), timezone.now().replace(tzinfo=None))
    num_of_secs = (timezone.now().replace(tzinfo=None) - start_date).total_seconds()
    num_of_weeks = num_of_secs / (num_days * 24 * 60 * 60)
    # logger.debug('num_secs: %s num weeks: %s', num_of_secs, num_of_weeks)
    frequency = num_total_bets / num_of_weeks
    # logger.debug('frequency: %s', frequency)
    return frequency


def linear_interpolation(x0, y0, x1, y1, x):
    return (y0*(x1-x) + y1*(x-x0)) / (x1-x0)


def linear_interpolation_constant(x0, y0, x1, y1, x):
    """ Outside of the limits the function is constant """
    if x > x1:
        return y1
    elif x < x0:
        return y0
    return linear_interpolation(x0, y0, x1, y1, x)


def calculate_tbs_score(player_yield, num_total_bets, bet_days, no_bet_days, frequency, days_since_last_bet):
    """
    All values are normalized linearly between 0 and 1. Normalized values are called factors.
    Value 1 means perfect.
    There will be 2 scales: One from 0 to 0.9, and one from 0.9 to 1
    For each value there is a value that is considered perfect. For example any yield above 35%
    is considered perfect and the yield for such a value will be normalized to 1.
    A perfect player (all values 1) has score 100.
    A weighted factor is calculated from the weighted product of num, freq, bet and no bet days and is multiplied
    by the yield factor to extract the score which is then reduced based on the days_since_last_bet factor.
    This is a universal way to grade tipsters and can be used for other website's tipsters too.

    :param bet_days: Despite the fact that the calculation also uses frequency and num bets,
    (which means that the bet days could be calculated based on them)
    this parameter has a meaning. If a user makes 500 bets in one day then it must not have as high
    score as one that made 500 bets in a year.
    """

    # todo create the second scale:
    # perfect values to infinity corresponds to score from 0.9 to 1. No one can achieve exactly score 100.
    # This is for grading the highest masters. For first scale the max factor values must be 0.95 since
    # the avg factor is multiplied by the yield factor to extract the score, in order to have score of 0.9
    # then the 2 multipliers must be 0.95. So the perfect values for the factors are 0.95.
    # Current perfect score is 90.2

    if not num_total_bets or not player_yield or not bet_days:
        return 0
    if not frequency:
        frequency = 7.
    if player_yield < 0:
        return 0

    yield_perfect = 35.
    num_bets_perfect = 500.
    frequency_perfect = 7.  # per week
    bet_days_perfect = 121  # 1/3 of a year

    # if your no bet days are less than 5 times your bet days then there is no score penalty. Maximum
    # penalty factor is 0.1 achieved on 20 times your bet days.
    no_bet_days_lower = 5 * bet_days
    no_bet_days_upper = 4 * no_bet_days_lower
    no_bet_days_max_penalty = 0.1
    if not no_bet_days:
        no_bet_days = no_bet_days_lower

    # if you are inactive for less than 21 days there is no score penalty. If you are inactive
    # for more than 120 days then you have reached the maximum penalty factor
    inactivity_upper = 120.
    inactivity_lower = 21.
    inactivity_max_penalty = 0.5

    num_factor = linear_interpolation_constant(0., 0., num_bets_perfect, 0.95, num_total_bets)
    frequency_factor = linear_interpolation_constant(0., 0., frequency_perfect, 0.95, frequency)
    bet_days_factor = linear_interpolation_constant(0., 0., bet_days_perfect, 0.95, bet_days)
    yield_factor = linear_interpolation_constant(0., 0., yield_perfect, 0.95, player_yield)

    no_bet_days_factor = linear_interpolation_constant(
        no_bet_days_lower, 0.95, no_bet_days_upper, no_bet_days_max_penalty, no_bet_days)
    inactivity_factor = linear_interpolation_constant(
        inactivity_lower, 1.0, inactivity_upper, inactivity_max_penalty, days_since_last_bet)
    # activity_frequency = num_total_bets / (activity_timespan/7)  # num of bets per week

    num_factor = round(num_factor, 4)
    frequency_factor = round(frequency_factor, 4)
    inactivity_factor = round(inactivity_factor, 4)
    yield_factor = round(yield_factor, 4)
    bet_days_factor = round(bet_days_factor, 4)
    no_bet_days_factor = round(no_bet_days_factor, 4)

    # weights
    wnum = 1.
    wfreq = 1.
    wbd = 2.
    wnbd = 1
    # weighted product
    avg_main_factor = (num_factor**wnum * frequency_factor**wfreq * bet_days_factor**wbd * no_bet_days_factor**wnbd)**(
        1/(wnum + wfreq + wbd + wnbd))

    score_neutral = yield_factor * avg_main_factor
    score = score_neutral * inactivity_factor
    # logger.debug('score_neutral: %s, inactivity factor: %s, updated score: %s', score_neutral, inactivity_factor, score)
    score = round(score, 3) * 100

    logger.info('num: %s, freq: %s, yield: %s, bet_days: %s, no_bet_days: %s, inact: %s',
                 num_factor, frequency_factor, yield_factor, bet_days_factor, no_bet_days_factor, inactivity_factor)
    logger.info("avg_main_factor: %s, score_neutral: %s, score: %s", avg_main_factor, score_neutral, score)

    # all values have the same weight
    # wy = 1
    # sc1 = (num_factor**wnum * frequency_factor**wfreq * timespan_factor**wtime * yield_factor**wy) ** (1/(wnum + wfreq + wtime+ wy))
    # sc1 = round(sc1, 3) * 100
    # logger.debug("sc1 [all equal]: %s", sc1)
    # logger.debug("score [yield * factor]: %s", score)

    # logger.debug('num: %s, fr: %s, yield: %s, score: %s', num_total_bets, frequency, player_yield, score)
    return score


def calc_pure_wins(df):
    pure_wins_calculation = lambda row: row['total_return'] - row['amount']
    # sr for series
    pure_wins_sr = df.loc[df['status'] == games.models.TotalBet.won].apply(
        pure_wins_calculation, axis=1)
    # logger.debug('pure_wins_sr: %s', pure_wins_sr)
    if pure_wins_sr.empty:
        # if there are no won tbs
        positive_pure_wins_sr = pd.Series([0])
    else:
        positive_pure_wins_sr = pure_wins_sr[pure_wins_sr > 0]
    # logger.debug('positive_pure_wins_sr: %s', positive_pure_wins_sr)
    pure_wins = positive_pure_wins_sr.sum()
    return pure_wins, positive_pure_wins_sr


def calc_no_outliers_yield(df, std_range=5):
    """ It calculates the yield rejecting outliers (keeping values within +-5 standard deviations)
    The value of concern is the possible returns (amount*odd) and not the net_result
    Have in mind that you could use MAD and MEDIAN instead of STD and MEAN """
    lost = games.models.TotalBet.lost
    # df['to_win'] = df['total_return'] - df['amount']
    df.loc[:, 'to_win'] = df['odd'] * df['amount']
    # logger.debug('to_win: %s', to_win)
    # mad = to_win.mad()
    std = df['to_win'].std()
    # median = to_win.median()
    # mean = to_win.mean()
    # limit = 12 * mad
    limit = std_range * std
    # logger.debug('std: %s, mad: %s, mean: %s, median: %s limit: %s', std, mad, mean, median, limit)
    if np.isnan(limit):
        df.pop('to_win')  # remove the temp column
        return
    no_outliers_df = df[np.abs(df['to_win']-df['to_win'].mean()) <= limit]

    if 165 in df['bet_tag_id'].values:
        # manually remove a bet with invalid odds from score calculation (bet group 165 is of user 157 larissinos)
        # removing it here will not affect any the other stats (shown yield etc. will contain it)
        # todo high: replace this temporary solution with a generic one for zombie bets
        no_outliers_df = df[df['total_bet_id'] != 626]

    if no_outliers_df.size == df.size:
        # there is no outlier
        df.pop('to_win')
        return
    # outliers_df = df[np.abs(df['to_win'] - df['to_win'].mean()) > limit]
    # logger.debug('outliers: %s', outliers_df)
    clipped_pure_wins, clipped_positive_pure_wins_sr = calc_pure_wins(no_outliers_df)
    stakes_lost = no_outliers_df.loc[no_outliers_df['status'] == lost]['amount'].sum()
    money_staked = no_outliers_df['amount'].sum()  # sum returns 0 if series is empty
    clipped_bank_growth = clipped_pure_wins - stakes_lost
    clipped_yield = (clipped_bank_growth / money_staked) * 100
    df.pop('to_win')
    # logger.debug('%s outliers', df['amount'].size - no_outliers_df['amount'].size)
    return clipped_yield


def activity_timespan_calculation(start_date, end_date):
    try:
        timespan = (end_date - start_date).total_seconds() / 60 / 60 / 24  # number of days
    except Exception as e:
        logger.debug("%s", e)
        return
    return timespan


def days_since(start_date):
    try:
        timespan = (timezone.now().replace(tzinfo=None) - start_date).total_seconds() / 60 / 60 / 24  # number of days
    except Exception as e:
        logger.debug("%s", e)
        return
    return timespan


def get_no_bet_days(date_df, bet_days=None):
    if date_df.empty:
        return
    try:
        start_date = date_df.index[0]
        tipsters_lifespan = days_since(start_date)
        if not bet_days:
            bet_days = get_bet_days(date_df)
        no_bet_days = tipsters_lifespan - bet_days
    except Exception as e:
        logger.debug("%s", e)
        return
    return no_bet_days


def get_bet_days(date_df):
    if date_df.empty:
        return
    try:
        return date_df.index.unique().size
    except Exception as e:
        logger.debug("%s", e)
        return


@try_cache_first(timeout=60*60*24*7)
def calculate_total_bets_stats(user_total_bets_df, user_id):
    """
    calculates the total bet df stats from the closed total bets of the given df
    It is cached. Notice that since the argument can be either the abs df or the norm df, this function caches both
    """
    # Currently used for the users list templates (for example leaderboard)

    # Have in mind that I can filter the df before passing it to the function and calculate stats for a
    # subset of all the tbs. For example for a specific competition
    # TODO split df to closed, open and combined and return stats for each "group".
    # The correct value for some attributes is extracted from the combined group.
    # For example bet_deposits, balance (function of bet_deposits)
    # Eventually I can eliminate the need for this function and leave it only for checking and emergencies
    logger.debug("calculating total bets stats...")
    # todo add followers/following (mind to update user cache on new follow/unfollow)
    data = {
        'num_bet_tags': 0,
        'num_total_bets': 0,
        'money_staked': 0,
        'stakes_lost': 0,
        'pure_wins': 0,
        'bank_growth': 0,
        'total_yield': 0,
        'investment': 0,
        'roi': 0,
        'won_total_bets': 0,
        'lost_total_bets': 0,
        'open_total_bets': 0,
        'mean_profit': 0,
        'returns_sum': 0,
        'biggest_win': 0,
        'smallest_win': 0,
        'mean_win': 0,
        'median_win': 0,
        'score': 0,
        # 'temp_tag_per_tag_names': temp_tag_per_tag_names,
        # 'total_balance': total_balance,
    }

    if user_total_bets_df.empty:
        # if there are no tbs then the tbs_df is empty. But the user might have some bet tags. So this
        # info is added manually here
        logger.debug("No total bets in df")
        try:
            logger.debug("getting bet tags of user: %s", user_id)
            user = User.objects.get(id=user_id)
            logger.debug('user: %s', user)
            num_bet_tags = user.bet_tags.all().count()
            logger.debug("num bet tags: %s", num_bet_tags)
            data['num_bet_tags'] = num_bet_tags
            logger.debug("data: %s", data)
        except Exception as e:
            logger.debug("%s", repr(e))
            return data
        return data

    num_total_bets = user_total_bets_df.shape[0]
    open_total_bets = user_total_bets_df.loc[user_total_bets_df['status'] == games.models.TotalBet.open].shape[0]
    # have in mind that if a bet group has no total bets yet, then it doesn't appear in the df so it is not counted
    bet_tag_names = user_total_bets_df['bet_tag_name'].unique()  # ndarrays
    num_bet_tags = bet_tag_names.size

    user_total_bets_df = utils.tbs_df_exclude_by_status(user_total_bets_df, ['Open'])
    if user_total_bets_df.empty:
        logger.debug("No closed total bets in df. total bet stats are: None")
        data['num_total_bets'] = num_total_bets
        data['open_total_bets'] = open_total_bets
        data['num_bet_tags'] = num_bet_tags
        return data

    money_staked = user_total_bets_df['amount'].sum()  # sum returns 0 if series is empty
    stakes_lost = user_total_bets_df.loc[user_total_bets_df['status'] == games.models.TotalBet.lost]['amount'].sum()
    pure_wins, positive_pure_wins_sr = calc_pure_wins(user_total_bets_df)
    bank_growth = pure_wins-stakes_lost
    # todo bank growth faster and more robust calculation, check it
    # (it doesn’t depend on the correctness of the characterization of a bet as won or lost)
    # Bank_growth[i] = Total_return_cumsum – amount_cumsum
    total_yield = (bank_growth/money_staked) * 100

    no_outliers_yield = calc_no_outliers_yield(user_total_bets_df, 5)
    # logger.debug('yield: %s, no_outliers_yield: %s', total_yield, no_outliers_yield)
    if not no_outliers_yield:
        no_outliers_yield = total_yield
    # else:
    #     logger.debug('user_id: %s has outliers', user_id)

    investment = calc_total_tbs_df_deposits(user_total_bets_df)
    # investment = user_total_bets_df['investment'].max()  # this is the bet calculated deposits
    # logger.debug('cum bets: %s', user_total_bets_df['amount'].cumsum())
    # logger.debug('cum_return: %s',  user_total_bets_df['total_return'].shift(1).fillna(0).cumsum())
    # logger.debug('investment column: %s', investment_sr)
    roi = bank_growth/investment*100 if investment else 0
    num_of_closed_total_bets = user_total_bets_df.shape[0]
    won_total_bets = user_total_bets_df.loc[user_total_bets_df['status'] == games.models.TotalBet.won].shape[0]
    lost_total_bets = user_total_bets_df.loc[user_total_bets_df['status'] == games.models.TotalBet.lost].shape[0]

    mean_profit = pure_wins/num_of_closed_total_bets
    # median profit can't be compared with mean profit. The mean takes into consideration all bets. The median can't do
    # this since if most are lost you can have a median of 0. It is more like the median pure wins when you win.
    returns_sum_sr = user_total_bets_df['total_return'].cumsum()
    returns_sum = returns_sum_sr.max()

    biggest_win = positive_pure_wins_sr.max()
    smallest_win = positive_pure_wins_sr.min()
    mean_win = positive_pure_wins_sr.mean()
    median_win = positive_pure_wins_sr.median()

    total_return_sr = user_total_bets_df['total_return']
    positive_total_return_sr = total_return_sr[total_return_sr > 0]
    # logger.debug('positive_total_return_sr: %s', positive_total_return_sr)

    first_tb_date = user_total_bets_df.index[0]
    last_tb_date = user_total_bets_df.index[-1]
    days_since_last_bet = days_since(last_tb_date)
    bet_days = get_bet_days(user_total_bets_df)
    no_bet_days = get_no_bet_days(user_total_bets_df, bet_days=bet_days)
    frequency = calculate_frequency(first_tb_date, num_total_bets)
    # The score must be periodically calculated (every week) so that the time related values are updated.
    # No need for a scheduled job since on leaderboard call uncalculated user stats are calculated and cached.
    score = calculate_tbs_score(no_outliers_yield, num_total_bets, bet_days, no_bet_days, frequency, days_since_last_bet)

    # temp_tag_per_tag_names, total_balance = utils.calc_balance_per_tags(user_total_bets_df)
    data = {
        'num_bet_tags': num_bet_tags,
        'num_total_bets': num_total_bets,
        'money_staked': money_staked,
        'stakes_lost': stakes_lost,
        'pure_wins': pure_wins,
        'bank_growth': bank_growth,
        'total_yield': total_yield,
        'investment': investment,
        'roi': roi,
        'won_total_bets': won_total_bets,
        'lost_total_bets': lost_total_bets,
        'open_total_bets': open_total_bets,
        'mean_profit': mean_profit,
        'returns_sum': returns_sum,
        'biggest_win': biggest_win,
        'smallest_win': smallest_win,
        'mean_win': mean_win,
        'median_win': median_win,
        'score': score
        # 'temp_tag_per_tag_names': temp_tag_per_tag_names,
        # 'total_balance': total_balance,
    }
    logger.debug("total bet stats: %s", data)
    return data


def create_by_date_df(tbs_df, group_by_col):
    """
    It creates a dataframe by grouping the values based on the given column which must be a date column.
    The given column will also be the index column.
    The index of the given tbs_df is reset in order to be bale to work independently of it (this way the function
    can handle both cases: the tbs_df has the date or the decision_date columns as index)
    It clears the tbs_df removing the empty total_bets (the total return of which is NaN)
    """
    logger.debug("creating by date dataframe...")

    reset_tbs_df = tbs_df.reset_index()
    closed_tbs_df = utils.tbs_df_exclude_by_status(reset_tbs_df, ['Open'])

    if closed_tbs_df.empty:
        return utils.empty_dataframe()

    by_date_df = closed_tbs_df[['amount', 'total_return']].groupby(
        closed_tbs_df[group_by_col].map(lambda t: timezone.datetime(t.year, t.month, t.day))
    ).sum()
    bank_growth_by_date = closed_tbs_df[['bank_growth']].groupby(
        closed_tbs_df[group_by_col].map(lambda t: timezone.datetime(t.year, t.month, t.day))
    ).last()
    by_date_df['bank_growth'] = bank_growth_by_date['bank_growth']
    by_date_df.index.names = [group_by_col]
    # logger.debug("by_date_df %s", by_date_df)
    return by_date_df


def calculate_goal_lists(user_bet_events_col):
    """
    :param user_bet_events_col: pandas dataframe column
    :return:
    """
    # TODO make it in pandas (use values and clean it up)
    # TODO get the full_time result instead of final result. The optimum is to get both
    home_goals = []
    away_goals = []
    for bev_id in user_bet_events_col:
        final_res = games.models.BetEvent.objects.get(id=bev_id).event.results.filter(final=True)
        if final_res:
            home_goals.append(final_res[0].home_goals)
            away_goals.append(final_res[0].away_goals)
        else:
            home_goals.append('None')
            away_goals.append('None')
    return home_goals, away_goals


def create_bet_events_df(user_id, user_bet_events):
    """
    :param user_id:
    :param user_bet_events: queryset
    :return:
    """
    logger.debug('creating bet_events dataframe...')
    user_bet_events_df, bet_events_values = utils.df_from_bet_events(user_bet_events)
    if not user_bet_events_df.empty:
        user_bet_events_df = user_bet_events_df[user_bet_events_df['user_id'] == user_id]
        user_bet_events_df.index = pd.to_datetime(user_bet_events_df.index, utc=True)
        user_bet_events_df.index.names = ['event_date']
        user_bet_events_df = user_bet_events_df[~user_bet_events_df.index.to_series().isnull()]
        user_bet_events_df.sort_index(inplace=True)

        home_goals, away_goals = calculate_goal_lists(user_bet_events_df['bet_event_id'])
        user_bet_events_df.loc[:, 'home_goals'] = pd.Series(home_goals, index=user_bet_events_df.index)
        user_bet_events_df.loc[:, 'away_goals'] = pd.Series(away_goals, index=user_bet_events_df.index)

    # logger.debug('USER BET_EVENTS len:%d %s', len(user_bet_events), user_bet_events)
    # for bet_event in user_bet_events:
    #     logger.debug("---bet_event: ", bet_event.id, bet_event.event.home_team.generic_name,
    #                  bet_event.event.away_team.generic_name)
    # logger.debug("bet events df shape: %s", user_bet_events_df.shape)
    return user_bet_events_df


def calc_bank_growth_column(tbs_df):
    """
    Bank growth column is the cumsum bank_growth, that is the total bank growth at the time of the total bet, not the
    change on the bank growth that the current total bet brings. This change is the total_return - amount for each tb
    the bank growth is the (total_return - amount).cumsum
    If the given tbs_df has open bets then the bank growth value for these tbs will be NaN because total_return is NaN
    """
    logger.debug("calculating bank growth column...")
    if tbs_df.empty:
        return
    delta = tbs_df['total_return'] - tbs_df['amount']
    delta[0] = 0
    if tbs_df['total_return'][0]:
        # tb status is won. Notice that in case of bet systems the amount might be bigger then the return
        initial_bank_growth = tbs_df['total_return'][0]-tbs_df['amount'][0]
    elif tbs_df['total_return'][0] == 0:
        initial_bank_growth = -tbs_df['amount'][0]
    else:
        # tbs_df['total_return'][0] is NaN because the tb is open
        initial_bank_growth = np.NaN

    if not initial_bank_growth or np.isnan(initial_bank_growth):
        # (open tbs support, if first tb is open)
        # because if its nan then the whole bank_growth_series will be nan (nan + delta)
        initial_bank_growth = 0
    bank_growth_series = pd.Series(initial_bank_growth + delta.cumsum(), index=tbs_df.index)
    return bank_growth_series


def calc_investment_column(tbs_df):
    # It isn't used anymore
    """
    Investment value i is calculated based on i-1 value of total_return. So if its NaN the calculation is wrong.
    So, the open bets (and so the nan total return values) are removed. A new df is created with the closed bets.
    The investment is calculated from it. Then it is added to the original tbs df and in place of open bets the
    investment value is Nan.
    """
    logger.debug("calculating investment column...")
    if tbs_df.empty:
        return

    closed_tbs_df = utils.tbs_df_exclude_by_status(tbs_df, ['Open'])

    if closed_tbs_df.empty:
        investment_sr = pd.Series(np.nan, index=tbs_df.index)
        investment_sr[0] = tbs_df['amount'][0]
        tbs_df.loc[:, 'investment'] = investment_sr
        return
    investment_sr = closed_tbs_df['amount'].cumsum() - closed_tbs_df['total_return'].shift(1).cumsum()
    investment_sr[0] = closed_tbs_df['amount'][0]
    # logger.debug('before %s %s', investment_sr, investment_sr.size)
    # in case that tbs_df.index had duplicate values (tbs with the same date) there was an error:
    # ValueError: cannot reindex from a duplicate axis
    investment_sr = pd.Series(investment_sr, index=tbs_df.index)
    # tbs_df.loc[:, 'investment'] = investment_sr
    return investment_sr


def add_bet_deposit_column(tbs_df):
    """
    bet_deposits is the deposits of the user as calculated by his bet amounts and returns. If there is a
    value this means that the user made a deposit to fill the amount of that particular bet.
    This depends on the selected tbs so it must be calculated in js for js filters to work correctly
    """
    tbs_df['cummax_investment'] = tbs_df['investment'].cummax()  # calculates a column with the current max
    tbs_df['shifted_cummax_investment'] = tbs_df['cummax_investment'].shift(1).fillna(0)
    tbs_df['bet_deposit'] = tbs_df['cummax_investment'] - tbs_df['shifted_cummax_investment']
    tbs_df.drop('cummax_investment', axis=1, inplace=True)
    tbs_df.drop('shifted_cummax_investment', axis=1, inplace=True)


def create_tag_deposits_df(tag_deposits_queryset, deposit_col_name):
    if not tag_deposits_queryset:
        return utils.empty_dataframe()
    values = ['id', 'date', 'amount']
    user_deposits_df = pd.DataFrame.from_records(tag_deposits_queryset.values(*values), index='date')
    user_deposits_df.rename(columns={'id': 'deposit_id', 'amount': deposit_col_name}, inplace=True)
    user_deposits_df.index = pd.to_datetime(user_deposits_df.index, utc=True)
    # logger.debug('deposit df: %s', user_deposits_df)
    return user_deposits_df


def add_depo_withdr_col(queryset, bet_group_name, prefix, tbs_df):
    """
    :param queryset: deposits or withdrawals
    :param bet_group_name:
    :param prefix: The prefix is added to the bet_group_name and creates the new column name.
        Important: This name is used in js and in money columns of tbs_df
    :param tbs_df:
    :return:
    """
    new_col_name = bet_group_name + prefix
    if queryset:
        # we want 0s in a tag column for all tbs that have other tags. (for reduceRemove to work correctly)
        # To do so, we collect only the tbs of this tag, combine it with this tag deposits, calc the cumsum
        # and then add it to the original tbs_df filling the gaps with 0s
        entries_df = create_tag_deposits_df(queryset, bet_group_name)
        # logger.debug("user deposits df: %s", user_deposits_df)
        tag_filtered_tbs_df = tbs_df[tbs_df['bet_tag_name'] == bet_group_name]

        combined_df = pd.concat([tag_filtered_tbs_df, entries_df])
        combined_df.sort_index(inplace=True)
        # logger.debug("combined df after creating and sorting: %s", combined_df)
        combined_df[bet_group_name].fillna(0, inplace=True)
        # logger.debug('combined_df after fillna : %s', combined_df)
        combined_df[bet_group_name] = combined_df[bet_group_name].cumsum()
        # logger.debug('combined_df after cumsum deposits : %s', combined_df)
        # remove rows with tb_id = NaN. These are the rows that correspond to datetimes that the user made a deposit
        # In these dates there is no tb_id. We remove them in order to get back the original size of the tbs_df
        # that contains as many rows as tbs
        combined_df.dropna(subset=['total_bet_id'], inplace=True)
        # logger.debug('combined_df after dropna : %s', combined_df)
        tbs_df[new_col_name] = combined_df[bet_group_name]
        # logger.debug('tbs_df with deposit tag name column: %s', tbs_df)
        tbs_df[new_col_name].fillna(0, inplace=True)
        # logger.debug('tbs_df after fillna: %s', tbs_df)
    else:
        # there are no deposits to this tag so we create a tag column with 0s
        tbs_df[new_col_name] = 0
    return


def add_tag_deposit_columns(user, tbs_df):
    """
    bet_group_deposits are the deposits that are manually made by the user. They are indexed to the total bets date
    (tbs df index). They are cumsum values. User_deposits might have been made also in other dates but we don't keep
    the combined dates in the combined df because these dates will have NaN values for the original tbs_df columns
    and that would cause problems in the crossfilter calculations.
    This means that if we want to create an chart of the deposits per date,
    we have to create a dataframe with the combined dates (tbs_df + user_deposits_df) and use this one.

    * There is a difference between the bet_deposits and the bet_group_deposits calculations. The bet_deposits amount
    depends on which tbs is applied to. For this reason it is calculated in javascript. But it's WRONG to consider
    the same for the bet_group_deposits too. Tag deposits are made in specific dates and do not depend on tbs. Even if
    you filter only one bet (let's say the last one) the bet_group_deposits amount is the sum of all tag deposits until
    the selected bet. This means that we must use the cumsum of the bet_group_deposits and get the
    max entry of the filtered bets. This can be done in the server saving slow js calculations. This has
    some drawbacks. If you select a date range, from date1 to date2, the tags deposits will be all the deposits
    made until date2 including deposits before date1.
    TODO You could remove the deposits before date1 in javascript
    """

    # todo if we want to create an chart of the deposits per date we have to create a dataframe with
    # the combined dates (tbs_df + user_deposits_df) and use this one.

    logger.debug("adding bet tag deposit columns...")
    if tbs_df.empty:
        return
    bet_tag_names = tbs_df['bet_tag_name'].unique()  # ndarrays
    bet_tag_ids = tbs_df['bet_tag_id'].unique()
    i = 0
    for bet_tag_id in bet_tag_ids:
        deposit_col_name = bet_tag_names[i]  # names must be indexed the same with ids
        # bet_group_deposits = bet_tagging.models.Deposit.objects.filter(user=user, bet_tag=bet_tag_id, is_calculated=False)
        # TODO performance select_related deposits on user, find way to avoid db hits and for loops inside pandas calculations
        bet_group_deposits = user.profile.deposits().filter(bet_tag=bet_tag_id)
        add_depo_withdr_col(bet_group_deposits, deposit_col_name, '_deposit_cumsum', tbs_df)

        bet_group_withdrawals = user.profile.withdrawals().filter(bet_tag=bet_tag_id)
        add_depo_withdr_col(bet_group_withdrawals, deposit_col_name, '_withdrawal_cumsum', tbs_df)
        i += 1
    # logger.debug('complete tbs_df %s', tbs_df)


def get_renaming_dict():
    renaming_dict = {'id': 'total_bet_id', 'name': 'total_bet_name', 'bookmaker__name': 'bookmaker_name',
                     'bet_tag__name': 'bet_tag_name', 'bet_tag__id': 'bet_tag_id', 'user__id': 'user_id'}
    return renaming_dict


def rename_tbs_initial_df(tbs_df):
    if tbs_df.empty:
        return
    renaming_dict = get_renaming_dict()
    tbs_df.rename(columns=renaming_dict, inplace=True)


def create_tbs_initial_df(queryset, values, index):
    """
    Creates the initial df for queryset that can have open total bets too.
    * Notice that since open tbs can also be in the df, the index can't be the decision_date
    * If I want to calculate the df for open total bets too, null total_returns
    and null decision dates must not be removed from the df.
    If we calculate the df only for closed total bets, this cleaning has no effect.

    * Notice: I can disconnect the index from the tbs_df calculation. Leave it with the default integer
    index and change the index before sending it. This way it would be easier to change the index.
    But I must check of course if the rest of the coe especially the add investment column works fine
    with integer indexed tbs_df.
    """
    # logger.debug("creating total bets initial dataframe...")
    if not queryset:
        return utils.empty_dataframe()
    queryset_values = queryset.values(*values)
    df = pd.DataFrame.from_records(queryset_values, index=index)
    # df = remove_open_tbs(df)
    df.index = pd.to_datetime(df.index, utc=True)
    df['decision_date'] = pd.to_datetime(df['decision_date'], utc=True)
    df.sort_index(inplace=True)
    # logger.debug("initial tbs df: %s", df)
    return df


@try_cache_first(timeout=60*60*24*7)
def calc_user_total_bets_df(user_id, exclude_open=True, start_date=None, end_date=None):
    """
    Caching is needed since it used by more than one functions
    The cached value is updated on total bet closed signal
    """
    logger.debug("calculating total bet df for user %s", user_id)
    user = get_user(user_id)
    if not user:
        empty_df = utils.empty_dataframe()
        return None, empty_df
    user_total_bets = games.models.TotalBet.objects.filter(user=user)
    if exclude_open:
        # Notice that a closed total bet might have open bet_events.
        user_total_bets = user_total_bets.exclude(status=games.models.TotalBet.open)
    if start_date and end_date:
        user_total_bets = user_total_bets.filter(date__range=(start_date, end_date))
    logger.debug("%s total_bets were filtered, tbs_df will be calculated from them", len(user_total_bets))
    values = ('id', 'name', 'date', 'decision_date', 'status', 'odd', 'amount', 'total_return',
              'bookmaker__name', 'bet_tag__name', 'bet_tag__id', 'user__id')
    user_total_bets_df = create_tbs_initial_df(user_total_bets, values, index='date')
    rename_tbs_initial_df(user_total_bets_df)

    bank_growth_series = calc_bank_growth_column(user_total_bets_df)
    if not user_total_bets_df.empty:
        user_total_bets_df.loc[:, 'bank_growth'] = bank_growth_series

    # investment_sr = calc_investment_column(user_total_bets_df)
    # if not user_total_bets_df.empty:
    #     user_total_bets_df.loc[:, 'investment'] = investment_sr

    add_tag_deposit_columns(user, user_total_bets_df)
    # logger.debug("tbs: %s, tbs_df: %s", user_total_bets, user_total_bets_df)
    return user_total_bets, user_total_bets_df


def calc_user_profile_stats_dfs(user_id, start_date=None, end_date=None):
    """
    The collection process in a nutshell:
    getting the bets from the user total_bets. getting the bet_events from these bets. mutliplying them with the
    proper number of total_bets (through the values method). Filter the bet events for the specific user (again).
    If dates are None, all total_bets will be collected

    Notice regarding the charts: Even if we collect the open bet_events, they will not appear in the charts
    if we have collected only the  closed total_bets. This happens, since in js we join the
    total_bets array with the bet_events array. Since the total_bets_array contains only the closed total_bets the
    joined tb array contains only the bet_events of the closed total_bets. The bet_events_dimension is filtered
    based on the joined array (for markets chart) so only the closed bet_events appear. The same applies also to
    the other charts since the bet_event crossfilter is common for all bet_event charts

    user_bet_events = games.models.BetEvent.objects.filter(bet__in=user_bets) and user_bet_events.values(...)
    Collects the betevents from the bet_betevents intermediate table. So it collects the bets that are in the given
    list and takes the bet_events of these bets. So the bet_events are unique in the result.
    tb1 --> b1 --> be1, be2
    tb2 --> b2 --> be1, be2
    In this case the user_bet_events queryset contains 4 entries. 2 be1 and 2 be2. This is what we want.
    But if we add one more total_bet for an existing bet
    tb3 --> b1 --> be1, be2
    then the user_bet_events queryset contains still only the 4 entries. For statistics we want to have all the 6 entries.
    This is achieved with the values method on the queryset. If the fields span across relations like they do here
    (bet__totalbet__id) then it returns all the times that the bet_event appears. This because the b1 appears 2 times in
    the values result. One for tb1 and one for tb3. We create a dataframe from the result. But for the same reason we
    need to filter the dataframe for the user once more, since if b1 is used also by tb_4 of another user, it will also
    be returned from the values method.
    Notice: The values of [be1, be2, be1, be2] is the same with the values of [be1, be2]. So I can use the distinct
    bet_events. It is lighter and more clear to understand.
    """
    logger.debug("calculating profile stats dataframes for user %s...", user_id)
    exclude_open = False
    user_total_bets, user_total_bets_df = calc_user_total_bets_df(user_id, exclude_open=exclude_open, start_date=start_date, end_date=end_date)
    if not user_total_bets or user_total_bets_df.empty:
        logger.debug("no total bets were filtered")
        dfs_response = {'tbs': utils.empty_dataframe(), 'tbs_by_date': utils.empty_dataframe(), 'bevs': utils.empty_dataframe()}
        queryset_response = {'tbs': None, 'bevs': None}
        return dfs_response, queryset_response
    # total_bet_stats = calculate_total_bets_stats(user_total_bets_df)
    # by_date_df = create_by_date_df(user_total_bets_df, 'date')
    by_date_df = pd.DataFrame()  # just create an empty dataframe. This dataframe isn't used and it can be removed
    # Notice: in case a tb is closed but a bet_event isn't closed yet it will be excluded from the bevs_df
    user_bet_events = get_bet_events(total_bets=user_total_bets, distinct=True, exclude_open=exclude_open)
    logger.debug("%s distinct bet_events were filtered", len(user_bet_events))
    user_bet_events_df = create_bet_events_df(user_id, user_bet_events)
    dfs_response = {'tbs': user_total_bets_df, 'tbs_by_date': by_date_df, 'bevs': user_bet_events_df}
    queryset_response = {'tbs': user_total_bets, 'bevs': user_bet_events}
    return dfs_response, queryset_response


def profile_stats_dfs_to_json(user_total_bets_df, by_date_df, user_bet_events_df):
    """
    If either tbs or bevs is empty then there will be no data in the json dict. This check is also made in js
    where if one of these two is empty then no stats data is displayed
    """
    if user_total_bets_df.empty or user_bet_events_df.empty:
        return json.dumps({'tbs': None, 'tbs_by_date': None, 'bevs': None})

    # # This is the process for adding MtM entries to tbs dataframe
    # bet_tags_dict = utils.tbs_bet_tags(querysets_dict)
    # tbs_list = utils.add_data_to_tbs(user_total_bets_df, bet_tags_dict)
    # user_total_bets_json = json.dumps(tbs_list, cls=DatetimeEncoder)
    user_total_bets_json = user_total_bets_df.reset_index().to_json(date_format="iso", orient="records", date_unit='ms')

    by_date_json = by_date_df.reset_index().to_json(date_format="iso", orient="records", date_unit='ms')
    user_bet_events_json = user_bet_events_df.reset_index().to_json(date_format="iso", orient="records", date_unit='ms')
    # I convert the dfs to json, then I create a dict with them and json.dumps the dict. Maybe I could dumps a
    # dictionary with dataframes directly? No, they have to be converted to json with the pandas function
    json_dict = {'tbs': user_total_bets_json, 'tbs_by_date': by_date_json, 'bevs': user_bet_events_json}
    json_stats = json.dumps(json_dict)
    return json_stats


def df_filter_open(tbs_df, request_user, target_user):
    # todo maybe hide open bets from unauthenticated users
    open_status = games.models.TotalBet.open
    if request_user.is_anonymous():
        tbs_df = tbs_df.drop(tbs_df[tbs_df['status'] == open_status].index)
        return tbs_df
    return tbs_df


def bet_group_ids_from_tbs_df(tbs_df, status=None):
    """
    :param tbs_df: total bets dataframe
    :param status: total bet status
    :return: a list of the unique bet group ids of the given dataframe, optionally filtered for the given status
    """
    if tbs_df.empty:
        return
    if not status:
        return tbs_df['bet_tag_id'].unique().tolist
    filtered_tbs_df = tbs_df[tbs_df['status'] == status]
    if filtered_tbs_df.empty:
        return
    return filtered_tbs_df['bet_tag_id'].unique().tolist()


def df_exclude_private(tbs_df, bevs_df, request_user, target_user, bet_group_ids=None):
    """ Removes if necessary the total bets and bet events that belong to private bet groups
    :param tbs_df:
    :param bevs_df:
    :param request_user:
    :param target_user:
    :param bet_group_ids: The unique bet group ids of the given tbs_df. If not given they will
    be calculated. This argument was created to speed up the process of continuing filters
    where the bet_group_ids have already been calculated from a previous filter
    :return: the filtered dataframes. If there is no filtering the originals will be returned
    """
    if request_user == target_user:
        return tbs_df, bevs_df
    bet_group_type = bet_tagging.models.BetTag.private
    open_status = games.models.TotalBet.open

    if not bet_group_ids:
        bet_group_ids = bet_group_ids_from_tbs_df(tbs_df, open_status)
    if not bet_group_ids:
        return tbs_df, bevs_df

    bet_groups = bet_tagging.models.BetTag.objects.filter(id__in=bet_group_ids, type=bet_group_type)
    if not bet_groups:
        return tbs_df, bevs_df
    private_group_ids = bet_groups.values_list('id', flat=True)
    private_tbs_df = tbs_df[(tbs_df['bet_tag_id'].isin(private_group_ids)) & (tbs_df['status'] == open_status)]
    # combine the 2 dfs and remove the duplicates. This way you subtract one df from the other
    tbs_df = pd.concat([tbs_df, private_tbs_df]).drop_duplicates(keep=False)

    private_tb_ids = private_tbs_df['total_bet_id'].tolist()
    # open and closed bevs of open tbs are considered private
    private_bevs_df = bevs_df[bevs_df['total_bet_id'].isin(private_tb_ids)]
    bevs_df = pd.concat([bevs_df, private_bevs_df]).drop_duplicates(keep=False)

    return tbs_df, bevs_df


def df_exclude_premium(tbs_df, bevs_df, request_user, target_user, bet_group_ids=None):
    if request_user == target_user:
        return tbs_df, bevs_df
    bet_group_type = bet_tagging.models.BetTag.premium
    open_status = games.models.TotalBet.open

    if not bet_group_ids:
        bet_group_ids = bet_group_ids_from_tbs_df(tbs_df, open_status)
    if not bet_group_ids:
        return tbs_df, bevs_df

    bet_groups = bet_tagging.models.BetTag.objects.filter(id__in=bet_group_ids, type=bet_group_type)
    if not bet_groups:
        return tbs_df, bevs_df
    hidden_ids = []
    for bet_group in bet_groups:
        active_subscribers = bet_group.get_active_subscribers()
        if request_user not in active_subscribers:
            hidden_ids.append(bet_group.id)
    hidden_tbs_df = tbs_df[(tbs_df['bet_tag_id'].isin(hidden_ids)) & (tbs_df['status'] == open_status)]
    tbs_df = pd.concat([tbs_df, hidden_tbs_df]).drop_duplicates(keep=False)

    hidden_tb_ids = hidden_tbs_df['total_bet_id'].tolist()
    # open and closed bevs of open tbs are considered private
    hidden_bevs_df = bevs_df[bevs_df['total_bet_id'].isin(hidden_tb_ids)]
    bevs_df = pd.concat([bevs_df, hidden_bevs_df]).drop_duplicates(keep=False)

    return tbs_df, bevs_df


def df_exclude_open(tbs_df, bevs_df):
    open_status_tb = games.models.TotalBet.open
    open_status_selection = games.models.Selection.open
    tbs_df = tbs_df[tbs_df['status'] != open_status_tb]
    bevs_df = bevs_df[bevs_df['selection_status'] != open_status_selection]
    return tbs_df, bevs_df


def df_exclude_permissioned(tbs_df, bevs_df, request_user, target_user):
    bet_group_ids = bet_group_ids_from_tbs_df(tbs_df, status=games.models.TotalBet.open)
    if not request_user.is_authenticated():
        # unauthenticated users don't have see permission on open total bets
        tbs_df, bevs_df = df_exclude_open(tbs_df, bevs_df)
        return tbs_df, bevs_df
    tbs_df, bevs_df = df_exclude_private(tbs_df, bevs_df, request_user, target_user, bet_group_ids)
    tbs_df, bevs_df = df_exclude_premium(tbs_df, bevs_df, request_user, target_user, bet_group_ids)
    return tbs_df, bevs_df


@try_cache_first(timeout=60*60*48)
def abs_profile_stats_data(target_user_id, start_date=None, end_date=None):
    logger.debug("Profile dataframe with absolute values for user %s not in cache, calculating...", target_user_id)
    dataframes_dict, querysets_dict = calc_user_profile_stats_dfs(target_user_id, start_date=start_date, end_date=end_date)
    return dataframes_dict


@try_cache_first(timeout=60*60*48)
def norm_profile_stats_data(target_user_id, start_date=None, end_date=None):
    logger.debug("Profile dataframe with normalized values for user %s not in cache, calculating...", target_user_id)
    dataframes_dict, querysets_dict = calc_user_profile_stats_dfs(target_user_id, start_date=start_date, end_date=end_date)
    utils.normalize_dataframes(dataframes_dict["tbs"], dataframes_dict["tbs_by_date"], dataframes_dict["bevs"])
    return dataframes_dict


def profile_stats_data(request, user_pk, start_date=None, end_date=None):
    """
    Notice:
    The dataframes are created with all the total bets of the target user and are cached.
    Then they pass through the filters to remove any total bets to which the request user has no
    access permission. The filtered dfs are transformed to json and returned.

    This function can't be cached, since the info regarding abs or norm data, doesn't depend on an argument
    but it's calculated based on the request user and the target user. So the arguments in both cases are
    the same, which means that this function can be stored just one time for each user.
    """
    target_user = get_object_or_404(User, pk=user_pk)
    request_user = request.user
    if gutils.utils.show_in_money_mode(request, target_user):
        dfs_dict = abs_profile_stats_data(target_user.id, start_date=start_date, end_date=end_date)
    else:
        dfs_dict = norm_profile_stats_data(target_user.id, start_date=start_date, end_date=end_date)

    tbs_df = dfs_dict['tbs']
    tbs_by_date_df = dfs_dict['tbs_by_date']
    bevs_df = dfs_dict['bevs']
    if not tbs_df.empty:
        tbs_df, bevs_df = df_exclude_permissioned(tbs_df, bevs_df, request_user, target_user)

    json_stats = profile_stats_dfs_to_json(tbs_df, tbs_by_date_df, bevs_df)

    return HttpResponse(json_stats, content_type="application/json")


# from django.views.decorators.clickjacking import xframe_options_exempt
# @xframe_options_exempt
@pjaxtend(parent='base.html', pjax_parent='pjax.html')
def profile_stats_template(request, user_pk):
    """
    The template is returned separately from the data that is "rendered" with. This is done since the data are json and
    we need to handle it in javascript (without embedding js in the django template). When a user requests the profile
    stats the template is returned and immediately after it has been completely loaded, an ajax call is done through
    javascript requesting the json data
    """
    # url = reverse('bet_statistics:profile_stats_template', kwargs={'user_pk': user_pk})
    # target_user_pk = url.split("/")[-2]
    target_user_pk = user_pk
    target_user = get_object_or_404(User, pk=target_user_pk)

    normalization_method = None
    if not gutils.utils.show_in_money_mode(request, target_user):
        normalization_method = NormalizationMethods.unit
    following, followers = user_accounts.utils.follow_relations(target_user, User)
    bet_tags = bet_tagging.models.BetTag.objects.filter(owner=target_user)
    # logger.debug("user %s bet tags %s", target_user, bet_tags)
    context = {
        "target_user": target_user,
        "following": following,
        "followers": followers,
        "bet_tags": bet_tags,
        "normalization_method": normalization_method,
        "object": target_user,
    }
    return TemplateResponse(request, 'bet_statistics/profile.html', context=context)


# def calc_user_stats(users):
#     """
#     All Leader board data are normalized. Some users might have their data public some not. Currently we
#     show all users normalized
#     """
#     data_list = []  # list of dicts, each dict has one user's data
#     for user in users:
#         user_tbs, user_tbs_df = calc_user_total_bets_df(user.id, exclude_open=True, start_date=None, end_date=None)
#
#         if not user_tbs:
#             # user has no closed total bets, his data will not be returned
#             continue
#
#         utils.normalize_tbs_df(user_tbs_df, unit=None, round_decimals=None)  # data are always normalized.
#
#         stats = calculate_total_bets_stats(user_tbs_df, user.id)
#
#         if stats:
#             wins_losses = "{} / {}".format(stats["won_total_bets"], stats["lost_total_bets"])
#             row_data = {
#                 # "index": "",
#                 "user_info": {"user_id": user.id, "username": user.username},
#                 "yield": stats["total_yield"],
#                 "roi": stats["roi"],
#                 "bank_growth": stats["bank_growth"],
#                 "investment": stats["investment"],
#                 "wins_losses": wins_losses,
#             }
#             data_list.append(row_data)
#     return data_list


# @cache_control(max_age=60*5)    # by the browser
# @cache_page(60 * 60 * 1)
# def leader_board_data(request):
#     # Doesn't used since some commits. The leaderboard response is calculated by the UsersList CBV
#     users = User.objects.exclude(total_bets__isnull=True).distinct()
#     data_list = calc_user_stats(users)
#     return HttpResponse(json.dumps(data_list), content_type="application/json")


# @pjaxtend()
# def leader_board_template(request):
#     # Doesn't used since some commits. The leaderboard response is calculated by the UsersList CBV
#     return TemplateResponse(request, 'bet_statistics/leaderboard.html', context={})


def get_user_bet_events_df(user_id, start_date=None, end_date=None):
    target_user = get_object_or_404(User, id=user_id)
    user_total_bets, user_total_bets_df = calc_user_total_bets_df(target_user.id, exclude_open=False, start_date=start_date, end_date=end_date)
    user_bet_events = get_bet_events(user_total_bets, distinct=True, exclude_open=False)
    bet_events_df = create_bet_events_df(target_user.id, user_bet_events)
    return bet_events_df, target_user


@try_cache_first(60*60*48)
def abs_events_table_data(user_id, start_date=None, end_date=None):
    logger.debug("calculating absolute bet events df...")
    bet_events_df, target_user = get_user_bet_events_df(user_id, start_date=start_date, end_date=end_date)
    user_bet_events_json = bet_events_df.reset_index().to_json(date_format="iso", orient="records", date_unit='ms')
    json_dict = {'normalization_method': None, 'bevs': user_bet_events_json}
    json_response = json.dumps(json_dict)
    return json_response


@try_cache_first(60*60*48)
def norm_events_table_data(user_id, start_date=None, end_date=None):
    logger.debug("calculating normalized bet events df...")
    bet_events_df, target_user = get_user_bet_events_df(user_id, start_date=start_date, end_date=end_date)
    unit = utils.calc_user_unit(target_user)
    utils.normalize_bevs_df(bet_events_df, unit)
    user_bet_events_json = bet_events_df.reset_index().to_json(date_format="iso", orient="records", date_unit='ms')
    json_dict = {'normalization_method': NormalizationMethods.unit, 'bevs': user_bet_events_json}
    json_response = json.dumps(json_dict)
    return json_response


@try_cache_first(60*60*48)
def percent_events_table_data(user_id, start_date=None, end_date=None):
    logger.debug("calculating percentized bet events df...")
    bet_events_df, target_user = get_user_bet_events_df(user_id, start_date=start_date, end_date=end_date)
    utils.percentize_bevs_df(bet_events_df)
    user_bet_events_json = bet_events_df.reset_index().to_json(date_format="iso", orient="records", date_unit='ms')
    json_dict = {'normalization_method': NormalizationMethods.percent, 'bevs': user_bet_events_json}
    json_response = json.dumps(json_dict)
    return json_response


def bet_events_table_data(request, user_id, start_date=None, end_date=None):
    target_user = get_object_or_404(User, id=user_id)

    if gutils.utils.show_in_money_mode(request, target_user):
        logger.debug("showing absolute data")
        json_response = abs_events_table_data(user_id, start_date=start_date, end_date=end_date)
    else:
        logger.debug("showing percentized data")
        json_response = percent_events_table_data(user_id, start_date=start_date, end_date=end_date)

    return HttpResponse(json_response, content_type="application/json")


@pjaxtend()
def bet_events_table_template(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    context = {'normalization_method': None}
    if not gutils.utils.show_in_money_mode(request, target_user):
        context = {'normalization_method': NormalizationMethods.percent}
    # TODO html pages with json data
    # get cached data with django and send a rendered template instead of sending an empty template
    # that is populated with json data. To do so, you need to serialize the data and store them in cache.
    # The serialization must be done in such a way that you can easily deserialize them. The best option
    # is to serialize django querysets and deserialize them. Now I don't serialize querysets. I just
    # manually collect the data and serialize (First I create a df and serialize the df. I did this
    # because this was the easiest way at the time. I guess that the best way is to serialize a queryset.
    # For example user's closed tbs. (Then add a new closed tb to the existing cached queryset if possible)
    return TemplateResponse(request, 'entities/bet_events_json_table.html', context=context)


class BetEventList(ListView):
    template_name = 'bet_statistics/bet_event_list.html'
    model = games.models.BetEvent
    context_object_name = 'bet_events'
    paginate_by = 10

    def __init__(self, **kwargs):
        super(BetEventList, self).__init__(**kwargs)
        test_user = get_user(15)
        # self.frequency_dict = None

    def get_queryset(self):
        bet_events_pool = games.models.BetEvent.objects.all()
        # bet_events = utils.popular_raw_bet_events(bet_events_pool, 20)
        bet_events = bet_events_pool
        # self.frequency_dict = frequency_dict
        return bet_events

    def get_context_data(self, **kwargs):
        context = super(BetEventList, self).get_context_data(**kwargs)
        # context['frequency_dict'] = self.frequency_dict
        return context

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(BetEventList, self).get(request, *args, **kwargs)
        return resp


class BetEventDetailView(DetailView):
    """
    Doesn't currently used. In bev table if the bev is open I show the all markets page. Else I show it's tb page
    This can't be easily implemented in the bevs detail page since a bet event doesn't have a one to one with a tb
    I must also provide its tb.
    """
    template_name = 'bet_statistics/bet_event_detail.html'
    model = games.models.BetEvent
    context_object_name = 'bet_event'
    # import pdb
    # pdb.set_trace()

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(BetEventDetailView, self).get(request, *args, **kwargs)
        return resp


class TotalBetDetailView(DetailView):
    template_name = 'bet_statistics/total_bet_detail.html'
    model = games.models.TotalBet
    context_object_name = 'total_bet'

    def get_context_data(self, **kwargs):
        context = super(TotalBetDetailView, self).get_context_data(**kwargs)
        total_bet = context[self.context_object_name]
        total_bet.enrich(self.request)
        if total_bet.label != bet_tagging.models.BetTag.free:
            # todo high create Not Allowed to access page
            raise Http404

        context['bet_events_per_bet'] = get_bet_events_from(total_bet)
        # context['decision_result_type'] = games.models.Result.ft_result
        context['status_list'] = {'Lost': games.models.TotalBet.lost, 'Open': games.models.TotalBet.open,
                                  'Won': games.models.TotalBet.won, 'Void': games.models.Selection.void}
        # normalization_method must be added in the template context level when the template is uniform
        # meaning that there is no possibility that some entities might be presented normalized and some not
        context['normalization_method'] = NormalizationMethods.percent
        return context

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(TotalBetDetailView, self).get(request, *args, **kwargs)
        return resp


def tb_open_closed(total_bet, open_tbs, closed_tbs):
    if total_bet.status == games.models.TotalBet.open:
        open_tbs.append(total_bet)
    else:
        closed_tbs.append(total_bet)


# @cache_page(cache_time/3)
@pjaxtend()
def total_bets_list(request, user_id):
    # TODO HIGH REGULAR CACHE the most visiting users (if not all)
    # TODO update CACHE on public setting change.
    # If money mode = true (currency) the response depends on the public setting of the target user
    # if mode is false response is always normalized. This means that in case I cache 2 responses (one for
    # true one for false) then in case the target user changes the public setting the response must be re-cached.
    # since previously private setting + currency returned normalized. Now it returns currency
    # But if the cache lives for a few minutes its not so big deal if I don't update the cache
    logger.debug('getting total bet list... (not using cached page)')
    target_user = get_user(user_id)
    if not target_user:
        raise Http404("User does not exist")

    total_bets = games.models.TotalBet.objects.filter(user=target_user).\
        select_related('user', 'bookmaker', 'bet_tag').\
        prefetch_related('bets__bet_events', 'bets__bet_events__selection', 'bets__bet_events__market_type',
                              'bets__bet_events__event__home_team', 'bets__bet_events__event__away_team',
                              'bets__bet_events__event__competition_season__competition',
                              'bets__bet_events__event__competition_season__season', 'bets__bet_events__event__results',
                              'bets__bet_events__event__competition_season__competition__country')

    open_tbs = total_bets.filter(status=games.models.TotalBet.open)
    closed_tbs = total_bets.exclude(status=games.models.TotalBet.open)

    games.models.TotalBet.batch_enrich(open_tbs, request)
    games.models.TotalBet.batch_enrich(closed_tbs, request)

    context = dict()
    context['open_tbs'] = open_tbs
    context['closed_tbs'] = closed_tbs
    context['open_table_id'] = 'open_user_total_bets'
    context['closed_table_id'] = 'closed_user_total_bets'
    context['title'] = 'Bets'

    logger.debug('rendering template...')
    return TemplateResponse(request, 'bet_statistics/total_bet_list.html', context)


@pjaxtend()
def raw_bev_tbs(request, raw_bev_id):
    context = {'total_bets': [], 'title': 'Bets'}
    try:
        raw_bet_event = RawBetEvent.objects.get(id=raw_bev_id)
    except Exception as e:
        logger.warning('%s', e)
        return TemplateResponse(request, 'bet_statistics/simple_tbs_list.html', context)
    related_bet_events = raw_bet_event.get_bet_events()
    parent_tbs = games.models.BetEvent.get_total_bets(related_bet_events)
    # You don't want to show the tbs as Private or Premium. You want to exclude them completely
    allowed_tbs = games.models.TotalBet.exclude_permissioned(parent_tbs, request.user)
    games.models.TotalBet.batch_enrich(allowed_tbs, request, cash_mode=False, label_all_free=True)
    context['total_bets'] = allowed_tbs
    return TemplateResponse(request, 'bet_statistics/simple_tbs_list.html', context)

