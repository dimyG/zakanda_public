from __future__ import unicode_literals
import logging
import pytz
# from os.path import join, dirname, abspath
# from django.contrib.auth.models import User
from models import ReadTotalBet, ReadBetEvent
import utils
from gutils.utils import get_user

logger = logging.getLogger(__name__)


def create_read_objects(user, data, datemode, tz):
    """
    if at least one of date, bookmaker, stake, num_bevs exist then we assume that this is a new tb. If all are empty
    then we assume that these rows contain events that belong to the last read_tb.

    :param data: is a list of lists. Each list corresponds to one column and contains column's values
    :return:
    """
    logger.info('creating read objects...')
    if not user:
        logger.error('no user was give, read objects will not be created')
        return
    date_column_headers = ['bet date', 'event date']
    read_tbs = []
    read_bet_events = []
    for row in data:  # row is a list with the values of the excel row
        if row[0] in date_column_headers:
            # skip the headers row
            continue

        bet_date = row[0]
        stake = row[1]
        bookmaker = row[2]
        num_bevs = row[3]
        description = row[4]
        bet_url = row[5]
        bet_group = row[6]
        total_odd = row[7]
        total_return = row[8]

        event_date = row[9]
        home_team = row[10]
        away_team = row[11]
        market = row[12]
        try:
            choice = str(int(row[13]))
        except ValueError:
            choice = str(row[13])
        odd = row[14]
        competition = row[15]
        season = row[16]
        event_round = row[17]
        result = row[18]
        status = row[19]

        if bet_date or stake or bookmaker or num_bevs:
            # or instead of and so that if one is missing the tb will be created and will be invalid.
            # we want to track the invalid tbs
            read_tb = ReadTotalBet(
                # empty strings will be converted to None by a ReadTotalBet method
                user=user, date=bet_date, stake=stake, bookmaker=bookmaker, bet_group=bet_group, num_bevs=num_bevs,
                description=description, bet_url=bet_url, odd=total_odd, total_return=total_return,
                datemode=datemode, tz=tz
            )
            read_tbs.append(read_tb)

        if event_date and home_team and away_team and market and choice and odd:
            read_bet_event = ReadBetEvent(
                date=event_date, home_team=home_team, away_team=away_team, market=market, choice=choice, odd=odd,
                competition=competition, season=season, event_round=event_round, result=result, status=status,
                datemode=datemode, tz=tz
            )
            read_bet_events.append(read_bet_event)

            try:
                read_tb
            except NameError:
                # This case might happen if the first tb is empty
                # We want to track the invalid tbs so orphan read_bet_evens must be avoided.
                # An invalid tb is created and the read bev is added to it.
                read_tb = ReadTotalBet(user=user, date=None, stake=None, bookmaker=None, num_bevs=None,
                                       datemode=datemode, tz=tz)
                read_tbs.append(read_tb)
                logger.error('invalid read_tb was created to adopt orphan read_bet_event %s', read_bet_event)

            read_tb.read_bet_events.append(read_bet_event)

            bet_slip_event = read_bet_event.to_bet_slip_event()
            read_tb.bet_slip_events.append(bet_slip_event)

    logger.info('%s read total bets were created from the raw excel data', len(read_tbs))
    logger.info('%s read bet events were created from the raw excel data', len(read_bet_events))
    return read_tbs


def register_history_bets(s3_bucket_name, filename, user_id, tz_string, commit):
    """ Notice that it can register total bets both for open events and for events with results. In case
    of events with results, you can have existing closed bet events or new bet events will be created """
    # s3_bucket_name = 'zakanda-static-01'
    # filename = 'past_bets.xlsx'
    # user_id = 29
    # tz_string = 'Europe/Athens'
    user = get_user(user_id=user_id)  # 10:c, 26:p, 23:t2, 27:p1, 25:bob, 28:liono, 29:yahdim
    try:
        tz = pytz.timezone(tz_string)
    except Exception as e:
        logger.error(e)
        tz = None
    if not s3_bucket_name or not filename or not user or not tz:
        logger.error('arguments error!')
        return

    s3_obj = utils.get_s3_obj(bucket=s3_bucket_name, filename=filename)
    # s3_obj = join(dirname(dirname(abspath(__file__))), 'fixtures', filename)  # read file from local disk

    work_book, data = utils.read_data(s3_obj)
    utils.remove_empty_rows(data)
    # datemode: Which date system was in force when this file was last saved.<br />
    #    0 => 1900 system (the Excel for Windows default).<br />
    #    1 => 1904 system (the Excel for Macintosh default).<br />
    datemode = work_book.datemode
    read_tbs = create_read_objects(user, data, datemode, tz=tz)
    if not commit:
        utils.check_validity(read_tbs)
    else:
        trees_created = utils.create_zakanda_bet_trees(read_tbs)
        if trees_created:
            user.profile.settle_total_bets(call_api=True)