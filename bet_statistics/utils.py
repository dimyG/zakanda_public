# -*- coding: utf-8 -*-
from __future__ import unicode_literals
__author__ = 'xene'

import logging
import pytz
import pandas as pd
import bet_statistics.views
from bet_tagging.utils import BetTagTemp
import bet_tagging.models

logger = logging.getLogger(__name__)


def empty_dataframe():
    return pd.DataFrame(columns=["C"])


def df_from_bet_events(bet_events_queryset):
    if not bet_events_queryset:
        logger.debug("0 bet_events are selected from the distinct bet_events")
        return empty_dataframe(), None
    bet_events_values = bet_events_queryset.values(
        'id', 'market_type__name', 'event__id', 'event__date', 'event__competition_season__competition__generic_name',
        'event__competition_season__season__name', 'event__competition_season__competition__country__name',
        'event__home_team__generic_name', 'event__away_team__generic_name',
        'event__round', 'selection__selected_odd', 'selection__choice', 'selection__status',
        'bet__totalbet__amount', 'bet__totalbet__id', 'bet__totalbet__bet_tag_balance_snapshot', 'bet__totalbet__bookmaker__name',
        'bet__totalbet__user__id', 'bet__id',
        # 'event__results__home_goals', 'event__results__away_goals', 'event__results__final',
    )
    bet_events_df = pd.DataFrame.from_records(bet_events_values, index='event__date')
    bet_events_df.rename(columns={
        'id': 'bet_event_id', 'market_type__name': 'market_type', 'event__id': 'event_id',
        'event__competition_season__competition__generic_name': 'competition_generic_name',
        'event__competition_season__season__name': 'season', 'event__competition_season__competition__country__name': 'country',
        'event__home_team__generic_name': 'home_team', 'event__away_team__generic_name': 'away_team', 'event__round': 'round',
        'selection__selected_odd': 'selected_odd', 'selection__choice': 'choice', 'selection__status': 'selection_status',
        'bet__totalbet__amount': 'total_bet_amount', 'bet__totalbet__id': 'total_bet_id', 'bet__totalbet__bookmaker__name': 'bookmaker_name',
        'bet__totalbet__bet_tag_balance_snapshot': 'bet_tag_balance_snapshot', 'bet__totalbet__user__id': 'user_id', 'bet__id': 'bet_id',
    }, inplace=True)
    logger.debug("%s bet_events were selected from the distinct bet_events", len(bet_events_values))
    return bet_events_df, bet_events_values


# commented out since tbs no longer have MtM with bet_tags (no tb.bet_tags). Not deleted for future reference
# def tbs_bet_tags(dict):
#     """
#     :param dict: {'tbs': user_tbs_queryset, 'bevs': user_bevs_queryset}
#     :return: {tb_1_id: [bet_tag_1_name, bet_tag_2_name], ... }
#     """
#     tbs = dict.get('tbs')
#     bet_tags_dict = {}
#     if not tbs:
#         return bet_tags_dict
#     for tb in tbs:
#         # they are not prefetched because if it were, I had to update also the cached calc_tb_df
#         bet_tags = tb.bet_tags.all()
#         names = [bet_tag.name for bet_tag in bet_tags if bet_tags] or []
#         bet_tags_dict[tb.id] = names
#     return bet_tags_dict


def add_data_to_tbs(tbs_df, bet_tags_dict):
    """
    * This function is used to add additional data (like bet_tags) to the total bets data. Since a total bet
    can have many bet_tags this would create additional rows to the dataframe if we included the bet_tags in the
    values() method during the dataframe creation. To avoid that, we transform
    the dataframe to a list of dicts, we add one more key-value pair to each dict. key is "bet_tags" and
    value is the list of the bet_tag names. The function returns the list of dicts (that will be transformed
    to json.)

    * We add bet_tags information to the tbs. This must be done just before the dataframe serializaion to json,
    when all pandas calculations are done, because the dataframe will be transformed to a python list and
    the list will be serialized to json. So all of its data must be ready to be sent to the client.

    :return: [ {tb_id: id, tb_amount: amount, bet_tags: [names_list], ...}, {..tb_2..}, etc. ]
    """
    if not bet_tags_dict or tbs_df.empty:
        # user has no filtered total bets and an empty list will be returned (to be transformed to json)
        return []
    tbs_list = tbs_df.reset_index().to_bet_slip_event('records')
    for tb_dict in tbs_list:
        tb_id = tb_dict.get("total_bet_id", None)
        # the to_dict() method keeps the datetimes to pandas Timestamp type. So we need
        # to transform Timestamp to aware datetimes in order to serialize them later in json.
        # the datetimes are in UTC (as they have been read from the database)
        tb_dict["decision_date"] = tb_dict["decision_date"].to_datetime().replace(tzinfo=pytz.UTC)
        tb_dict["date"] = tb_dict["date"].to_datetime().replace(tzinfo=pytz.UTC)
        if tb_id:
            bet_tag_names_list = bet_tags_dict.get(tb_id, None)
            if bet_tag_names_list is None:
                logger.error('Total bet id %s does not exist in the bet_tags_dict!', tb_id)
                bet_tag_names_list = []
            tb_dict['bet_tags'] = bet_tag_names_list
    return tbs_list


def tbs_df_money_columns(tbs_df):
    # TODO norm in %: bank growth must be normalized from -1 to 1 when "%" is asked
    money_columns = ['amount', 'total_return', 'bank_growth']  # investment col was removed since it is noy used
    # TODO IMPORTANT NOTE: How the df values are used in javascript:
    # *  investment value doesn't used by js anymore. It was used to calculate the bet_deposits which
    #    are no more supported
    # *  bank growth is used by the bank growth linechart and barchart
    #    (numbers and bubble_season uses the js calculated bank growth values)
    # *  bet_tag deposit values are used by the stats_reduce_function to calculate the investment value
    #    from which other values are calculated
    bet_tag_names = tbs_df['bet_tag_name'].unique().tolist()
    # tbs_df has tag deposit columns with the names of its tags. They need to be normalized too.
    bet_tag_deposits = [bet_tag_name + '_deposit_cumsum' for bet_tag_name in bet_tag_names]
    money_columns.extend(bet_tag_deposits)
    # logger.debug('bet_tag_deposit columns: %s', bet_tag_deposits)
    bet_tag_withdrawals = [bet_tag_name + '_withdrawal_cumsum' for bet_tag_name in bet_tag_names]
    money_columns.extend(bet_tag_withdrawals)
    # logger.debug("norm moeny col: %s", money_columns)
    return money_columns


def tbs_by_date_df_money_columns():
    return ['amount', 'total_return', 'bank_growth']


def bevs_df_money_columns():
    return ['total_bet_amount']


# if cached must be updated when calc_user_total_bets_df is updated
def calc_user_unit(user, exclude_open=False, start_date=None, end_date=None):
    """
    Notice that if the open tbs are excluded and a target user has only open bets then no unit will be
    calculated and the request user will be able to see target user's data no matter the settings of the target user
    """
    user_tbs, user_tbs_df = bet_statistics.views.calc_user_total_bets_df(
        user.id, exclude_open=exclude_open, start_date=start_date, end_date=end_date)
    if not user_tbs:
        # user has no total bets
        return None
    unit = unit_from_df(user_tbs_df)
    # logger.debug("unit for user %s is: %s", user, unit)
    return unit


def unit_from_df(df):
    if df.empty:
        return None
    median_amount = df['amount'].median()
    return median_amount


def percent_unit_column():
    return 'bet_tag_balance_snapshot'


def normalize_df(df, columns, unit):
    """
    The given columns of the given df are normalized. They are divided by the given unit
    Notice: the normalized values are normalized based on the latest unit (not the unit at the time they were created)
    """
    if df.empty:
        return
    for column in columns:
        try:
            df[column] = df[column]/unit
        except KeyError:
            # user has made no deposit or withdrawal
            logger.debug("Column with name %s doesn't exist in the datframe %s", column, df)


def percentize_df(df, columns):
    percent_column = percent_unit_column()
    if df.empty:
        return
    for column in columns:
        try:
            df[column] = df[column]/df[percent_column] * 100
        except KeyError:
            logger.debug("Column with name %s doesn't exist in the dataframe %s", column, df)


def percentize_bevs_df(user_bevs_df, round_decimals=None):
    if user_bevs_df.empty:
        return
    money_columns = bevs_df_money_columns()
    percentize_df(user_bevs_df, money_columns)
    if round_decimals:
        round_df_columns(user_bevs_df, money_columns, round_decimals)


def round_df_columns(df, columns, decimals):
    if df.empty:
        return
    df[columns] = df[columns].apply(lambda x: pd.Series.round(x, decimals))


def normalize_tbs_df(user_tbs_df, unit=None, round_decimals=None):
    # TODO have in mind that normalization of all dfs is done inplace
    if user_tbs_df.empty:
        return
    if not unit:
        unit = unit_from_df(user_tbs_df)
    money_columns = tbs_df_money_columns(user_tbs_df)
    normalize_df(user_tbs_df, money_columns, unit)
    if round_decimals:
        round_df_columns(user_tbs_df, money_columns, round_decimals)


def normalize_bevs_df(user_bevs_df, unit, round_decimals=None):
    if user_bevs_df.empty:
        return
    if not unit:
        logger.warning("There is no unit, df will not be normalized")
        return
    money_columns = bevs_df_money_columns()
    normalize_df(user_bevs_df, money_columns, unit)
    if round_decimals:
        round_df_columns(user_bevs_df, money_columns, round_decimals)


def normalize_tbs_by_date_df(user_tbs_by_date_df, unit, round_decimals=None):
    if user_tbs_by_date_df.empty:
        return
    if not unit:
        logger.warning("There is no unit, df will not be normalized")
        return
    money_columns = tbs_by_date_df_money_columns()
    normalize_df(user_tbs_by_date_df, money_columns, unit)
    if round_decimals:
        round_df_columns(user_tbs_by_date_df, money_columns, round_decimals)


def normalize_dataframes(tbs_df, tbs_by_date_df, bevs_df):
    """ All money values are "normalized" to units. 1 unit is equal to the median amount """

    if tbs_df.empty:
        return

    unit = unit_from_df(tbs_df)
    normalize_tbs_df(tbs_df, unit=unit)
    normalize_tbs_by_date_df(tbs_by_date_df, unit)
    normalize_bevs_df(bevs_df, unit)

    # logger.debug("tbs %s: ", tbs_df)
    # logger.debug("tbs by date %s: ", tbs_by_date_df)
    # logger.debug("bevs %s: ", bevs_df)


def normalize_values(unit, *values):
    if not unit:
        # if there is no unit, the values returned as they are
        return values
    norm_values = []
    for value in values:
        value = value/unit
        norm_values.append(value)
    return norm_values


def tbs_df_exclude_by_status(tbs_df, exclude_status_list):
    """
    :param exclude_status_list: a list of statuses to be excluded from the dataframe

    what i think is happening. There is obj1 (tbs_df) referenced by tbs_df name. You create another reference
    named sliced_tbs_df for the same object. Then when you slice obj_1 a copy of the slice of obj1
    is created automatically. So now you also have obj2. Then I assign this object to the
    existing sliced_tbs_df reference.
    """
    if tbs_df.empty:
        return tbs_df
    # sliced_tbs_df = tbs_df.copy(deep=True)  # With deep=False neither the indices or the data are copied
    sliced_tbs_df = tbs_df
    for exclude_status in exclude_status_list:
        sliced_tbs_df = sliced_tbs_df[~(sliced_tbs_df['status'] == exclude_status)]
    return sliced_tbs_df


def calc_bet_deposits_value(tbs_tag_df):
    """ handles open-closed, open, closed """
    # There is a distinction between closed deposits which are deposits indeed and open bet_amounts (not deposits).
    tag_investment_series = bet_statistics.views.calc_investment_column(tbs_tag_df)
    try:
        tag_closed_bet_deposits = tag_investment_series.max()
    except AttributeError:
        # there are only open bets (AttributeError: 'NoneType' object has no attribute 'max')
        tag_closed_bet_deposits = 0
    return tag_closed_bet_deposits


def calc_manual_deposits_value(user_id, bet_tag_name):
    """
    There are two values of manual_deposits:
    * deposits before last closed bets (used to calc the closed bets balance)
    * total_deposits (used to calc the total balance)
    """
    # All user deposits must be taken into account to calculate correctly the % of the balance put as bet.
    # Imagine the case that you have some closed bets. You make a deposit after them. This doesn't appear
    # in the tbs_df so it wouldn't be taken into account if we calculated the manual_deposits form the tbs_df.
    # Then he makes some other bets. The amount of these bets must be calculated as % of the balance
    # that includes the deposit after the closed tbs.
    # TODO it is better to add all the deposit values in the tag_column of the tbs_df when it is created. All
    # other columns will be NaN for the deposits made after the last tb. This way I avoid the db hits here

    # The user deposits made during the period of closed bets
    # tag_closed_tbs_manual_deposits = tbs_tag_df[bet_tag_name].max()

    tag_manual_deposit_entries = bet_tagging.models.Deposit.objects.filter(user=user_id).filter(bet_tag__name=bet_tag_name, is_calculated=False)
    tag_total_manual_deposits = 0
    for deposit in tag_manual_deposit_entries:
        tag_total_manual_deposits += deposit.amount
    return tag_total_manual_deposits


def calc_total_deposits_value(tag_total_manual_deposits, tag_closed_tbs_deposits, tag_open_bets_amount_value):
    # It's the total real deposits max(all user deposits, calculated closed bet deposits). If the user has made no
    # deposits for example, the real deposits would be the calculated value
    tag_total_deposits = max(tag_total_manual_deposits, tag_closed_tbs_deposits)
    if tag_total_deposits == 0:
        # no manual deposits and no closed bets then your deposits are your open bets amount
        tag_total_deposits = tag_open_bets_amount_value
    elif tag_closed_tbs_deposits == 0 and tag_open_bets_amount_value > tag_total_manual_deposits:
        # there are no closed bets, you have deposits but your have bet more
        tag_total_deposits = tag_open_bets_amount_value
    return tag_total_deposits


def calc_bank_growth_value(tbs_tag_df):
    """ handles closed-open, open, closed """
    tag_bank_growth_series = bet_statistics.views.calc_bank_growth_column(tbs_tag_df)
    tag_bank_growth_series_dropna = tag_bank_growth_series.dropna()
    if tag_bank_growth_series_dropna.empty:
        # tag has no closed bets
        tag_bank_growth = None
    else:
        # the last entry from entries with values is the tag's total bank growth
        tag_bank_growth = tag_bank_growth_series.dropna().iloc[-1]
    return tag_bank_growth


def calc_balance_value(bet_tag_name, tag_total_deposits, tag_bank_growth, tag_open_bets_amount_value):
    """
    There can be 2 values of balance:
    * balance of closed bets
    * total balance of all bets
    - in profile stats when you see the closed bets the balance is the balance of the closed bets. Of course you
    can filter bets and the balance changes. No need to calculate this value in the server
    - in the emails when you want to calculate the % of the balance, the balance is the balance of all bets including
    open tbs
    :param tag_total_deposits: is the total real deposits max(all user deposits, calculated closed bet deposits)
    """
    if tag_bank_growth == None:
        tag_bank_growth = 0
    tag_total_balance = tag_total_deposits + tag_bank_growth - tag_open_bets_amount_value
    if tag_total_balance < 0:
        # total amounts of open bets is bigger than the balance was, before placing these bets. This means that the user
        # has placed bets without making a deposit. This means that he has made some calculated bet_deposits (that aren't
        # calculated yet since they belong to open bets) and he has bet all of this amount. So his balance is 0.
        logger.debug('Total balance for tag %s is %s!', bet_tag_name, tag_total_balance)
        tag_total_balance = 0
    return tag_total_balance


def calc_balance_per_tags(user_tbs_df):
    """
    It MUST contain OPEN bets too, in order to calculate the correct total balance values
    * NOTICE: If there are no open bets then it will calculate the total balance correctly. But this number would
    not necessarily be the same with the closed_bets_balance that we see in the profile stats page. Because the
    calculation in django, contains also any manual deposits made after the last total bet that isn't contained
    in the tbs_df (at the moment) that the profile stats uses to calculate its values.
    """
    logger.debug("calculating balance per tags...")
    # logger.debug("for tbs_df: %s", user_tbs_df)
    if user_tbs_df.empty:
        return None, None
    renaming_dict = bet_statistics.views.get_renaming_dict()
    user_id_column = renaming_dict.get('user__id', None)
    bet_tag_column = renaming_dict.get('bet_tag__name', None)
    # by_bet_tag = user_tbs_df.groupby(bet_tag_column)  # DataFrameGroupBy object
    # total_bet_amount_df = by_bet_tag['amount'].sum()  # the group name (bet tag name) is the index
    # total_total_return_df = by_bet_tag['total_return'].sum()
    # mean_odd_df = by_bet_tag['odd'].mean()
    # first_total_bets_df = by_bet_tag['date'].first()  # the first bet of the tag
    # df = by_bet_tag.aggregate(np.sum)
    user_id = user_tbs_df[user_id_column].iloc[0]
    bet_tag_names = user_tbs_df[bet_tag_column].unique()
    total_balance = 0
    temp_bet_tag_per_tag = {}
    for bet_tag_name in bet_tag_names:
        """
        bank growth and investment columns are recalculated for each tbs_tag_df
        This because their value depends on the specific tbs from which they are calculated
        """
        logger.debug('calculating tag: %s', bet_tag_name)
        # if we don't use copy tbs_tag_df is a copy of a slice of tbs_df and you get a warning if you modify the
        # values of it.
        tbs_tag_df = user_tbs_df.loc[user_tbs_df[bet_tag_column] == bet_tag_name].copy()
        # logger.debug("%s", tbs_tag_df)

        tag_bank_growth = calc_bank_growth_value(tbs_tag_df)
        tag_closed_tbs_deposits = calc_bet_deposits_value(tbs_tag_df)
        tag_open_bets_amount_value = tbs_tag_df.loc[tbs_tag_df['status'] == 'Open']['amount'].sum()  # if no open is 0
        tag_total_manual_deposits = calc_manual_deposits_value(user_id, bet_tag_name)
        tag_total_deposits = calc_total_deposits_value(tag_total_manual_deposits, tag_closed_tbs_deposits, tag_open_bets_amount_value)
        tag_total_balance = calc_balance_value(bet_tag_name, tag_total_deposits, tag_bank_growth, tag_open_bets_amount_value)

        logger.debug('--- | tag %s | --- : tag_total_manual_deposits: %s, tag_closed_tbs_deposits: %s, '
                     'tag_total_deposits: %s, tag_open_bets_amount_value: %s, tag_bank_growth: %s, tag_balance: %s',
                     bet_tag_name, tag_total_manual_deposits, tag_closed_tbs_deposits, tag_total_deposits,
                     tag_open_bets_amount_value, tag_bank_growth, tag_total_balance)

        temp_bet_tag = BetTagTemp(
            user_id, bet_tag_name, tag_bank_growth, tag_total_balance, tag_closed_tbs_deposits,
            tag_total_manual_deposits, tag_total_deposits, tag_open_bets_amount_value
        )
        temp_bet_tag_per_tag[bet_tag_name] = temp_bet_tag
        total_balance += tag_total_balance
    # logger.debug("%s, %s", temp_bet_tag_per_tag, total_balance)
    return temp_bet_tag_per_tag, total_balance
