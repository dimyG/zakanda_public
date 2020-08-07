from __future__ import unicode_literals
import logging
import games.models
import bet_tagging.models
import games.signals
from bet_slip.views import create_bet_tree
from bet_tagging.utils import get_default_bet_tag
import register_history.exceptions as exceptions
from utils import parse_excel_date

logger = logging.getLogger(__name__)


class ReadTotalBet():
    # todo use schematics for these read "models"
    """
    ReadTotalBet attributes contain the raw excel data
    with the exception of the user attribute which is an actual User object

    Have in mind that there can be 2 tbs with exactly the same date, stake and bookmaker. You can distinguish
    them by comparing their read_bet_events. But if they have no read_bet_events yet then there is no way
    to distinguish them by their attributes.
    """
    def __init__(self, user, date, stake, bookmaker, num_bevs, datemode, tz, bet_group=None, description=None,
                 bet_url=None, odd=None, total_return=None, read_bet_events=None, bet_slip_events=None):
        if read_bet_events is None:
            read_bet_events = []
        if bet_slip_events is None:
            bet_slip_events = []
        self.user = user
        self.date = date
        self.stake = stake
        self.bookmaker = bookmaker
        self.bet_group = bet_group
        self.num_bevs = num_bevs
        self.description = description
        self.url = bet_url
        self.odd = odd
        self.total_return = total_return
        # list with dicts. Dict keys are event_id, market_type_id, choice, original_odd, selected_odd)
        self.read_bet_events = read_bet_events
        self.bet_slip_events = bet_slip_events
        self.datemode = datemode
        self.tz = tz

    def handle_empty_strings(self):
        if self.description == "":
            self.description = None
        if self.url == "":
            self.url = None

    def get_description(self):
        if not self.description:
            return None
        return self.description

    def get_url(self):
        if not self.url:
            return None
        return self.url

    # use @property
    def get_utc_date(self):
        utc_bet_date = parse_excel_date(self.date, self.datemode, self.tz)
        return utc_bet_date

    # todo use the @property here, rename it to bookmaker and use a bookmaker_name argument for the name
    def get_bookmaker(self):
        if not self.bookmaker:
            return
        try:
            bookmaker = games.models.Bookmaker.objects.get(name=self.bookmaker)
        except:
            bookmaker = None
        return bookmaker

    # use @property
    def get_bet_group(self):
        if not self.bet_group:
            bet_group = get_default_bet_tag(self.user)
            return bet_group
        try:
            bet_group = bet_tagging.models.BetTag.objects.get(name=self.bet_group, owner=self.user)
        except:
            bet_group = None
        return bet_group

    def is_valid(self):
        logger.info(' ------- validating data for read_total_bet: %s', self)
        return_value = True

        # todo del the user check is just for testing
        # user = zakanda.generic_functions.get_user(username=self.user.username)
        # if not user:
        #     return_value = False

        if not self.date or not self.stake or not self.bookmaker or not self.num_bevs:
            logger.error("argument must have value but it doesn't")
            return_value = False

        utc_date = self.get_utc_date()
        if not utc_date:
            logger.error('excel date %s can not be transformed to utc', self.date)
            return_value = False

        bet_group = self.get_bet_group()
        if not bet_group:
            logger.error('user %s has no bet_group with name %s', self.user, self.bet_group)
            return_value = False

        bookmaker = self.get_bookmaker()
        if not bookmaker:
            logger.error('there is no bookmaker with name %s', self.bookmaker)
            return_value = False

        # todo check valid url
        # todo check description length etc

        if not len(self.read_bet_events) == self.num_bevs:
            logger.error("user defined number of events is different from the read_tb's events")
            return_value = False

        if not self.read_bet_events:
            logger.error('read_tb has no associated read_bet_events')
            return_value = False

        read_bet_events = self.read_bet_events
        for read_bet_event in read_bet_events:
            if not read_bet_event.is_valid():
                return_value = False

        if not return_value:
            logger.warning('read_total_bet %s is INVALID', self)

        return return_value

    # in case of reading bet history and deposit/withdrawal history then I must create an Action queue.
    # Bet tree creation is one action. Deposit creation another one, withdrawal creation another one.
    # These actions must be executed one by one in the correct order.
    def create_zakanda_bet_tree(self, validate=True):
        if validate:
            if not self.is_valid():
                return None
        bet_group = self.get_bet_group()
        bookmaker = self.get_bookmaker()
        description = self.get_description()
        bet_url = self.get_url()
        date = self.get_utc_date()
        # have in mind that the create_bet_tree function doesn't check the bet_group's balance.
        # So even if it is 0 the bet can be saved. This is the intended behaviour since this way
        # we can handle past bets history without deposit/withdrawal history
        total_bet, bets, bet_events = create_bet_tree(
            user=self.user, bet_slip_events_list=self.bet_slip_events, bookmaker=bookmaker,
            bet_amount=self.stake, bet_tag=bet_group, bet_description=description,
            bet_description_url=bet_url, date=date, is_past=True
        )
        signal_result = games.signals.total_bet_tree_done.send_robust(sender=games.models.TotalBet, total_bet=total_bet)
        return total_bet, bets, bet_events

    def __unicode__(self):
        return '{} {} {} {}'.format(self.date, self.stake, self.bookmaker, self.bet_group)


class ReadBetEvent():
    """
    ReadBetEvent attributes contain the raw excel data
    """
    choices = []
    choices_tuples = games.models.Selection.market_results_combined_choices
    for choice_tuple in choices_tuples:
        choices.append(choice_tuple[0])

    def __init__(self, date, home_team, away_team, market, choice, odd, datemode, tz,
                 competition=None, season=None, status=None, result=None, event_round=None):
        self.date = date
        self.home_team = home_team
        self.away_team = away_team
        self.market = market
        self.choice = choice
        self.odd = odd
        self.competition = competition
        self.season = season
        self.status = status
        self.result = result
        self.round = event_round
        self.datemode = datemode
        self.tz = tz

    def handle_empty_strings(self):
        if self.competition == "":
            self.competition = None
        if self.season == "":
            self.season = None
        if self.status == "":
            self.status = None
        if self.result == "":
            self.result = None
        if self.round == "":
            self.round = None

    def is_valid(self):
        logger.info('validating data for read_bet_event %s', self)
        return_value = True

        if not self.date or not self.home_team or not self.away_team or not self.market or not self.choice or not self.odd:
            logger.error('required argument is missing')
            return_value = False

        try:
            self.odd = self.odd
            if self.odd <= 1:
                raise exceptions.PastBetsDataFormatError('odd {} is lower than 1'.format(self.odd))
        except Exception as e:
            logger.error("%s", e)
            return_value = False

        try:
            if self.choice not in self.choices:
                raise exceptions.PastBetsDataFormatError('Choice {} of type {} is not currently supported'.format(self.choice, type(self.choice)))
        except Exception as e:
            logger.error("%s", e)
            return_value = False

        teams = self.get_teams()
        if None in teams:
            return_value = False

        market_type = self.get_market()
        if not market_type:
            return_value = False

        event = self.get_event()
        if not event:
            return_value = False

        utc_date = self.get_utc_date()
        if not utc_date:
            return_value = False

        if not return_value:
            logger.warning('read_bet_event %s - %s is not valid', self.home_team, self.away_team)

        return return_value

    def get_utc_date(self):
        utc_bet_date = parse_excel_date(self.date, self.datemode, self.tz)
        return utc_bet_date

    def get_teams(self):
        team_names = [self.home_team, self.away_team]
        teams = []
        for team_name in team_names:
            team = None
            try:
                team = games.models.Team.objects.get(generic_name=team_name)
            except games.models.Team.DoesNotExist:
                logger.warning('Team %s is not currently supported', team_name)
            except games.models.Team.MultipleObjectsReturned:
                logger.error('More than one Teams with name %s found', team_name)
            teams.append(team)
        return teams  # home and away

    def get_event(self):
        date = self.get_utc_date()
        event = None
        try:
            event = games.models.Event.objects.get(home_team__generic_name=self.home_team,
                                                   away_team__generic_name=self.away_team, date=date)
        except games.models.Event.DoesNotExist:
            logger.warning("event %s - %s [%s] doesn't exist", self.home_team, self.away_team, date)
        except games.models.Event.MultipleObjectsReturned:
            logger.warning('more than one events for %s - %s [%s] were found!', self.home_team, self.away_team, date)
        return event

    def get_market(self):
        market_type = None
        try:
            market_type = games.models.MarketType.objects.get(name=self.market)
        except games.models.MarketType.DoesNotExist:
            logger.warning('MarketType %s is not currently supported', self.market)
        except games.models.MarketType.MultipleObjectsReturned:
            logger.error('Multiple market types with name %s were found!', self.market)
        return market_type

    def to_bet_slip_event(self):
        """
        creates a dictionary similar with the one that is created when we read the bet slip from the session
        in a normal bet submitting process.
        """
        event = self.get_event()
        if not event:
            return
        market_type = self.get_market()
        if not market_type:
            return
        event_id = event.id
        market_type_id = market_type.id
        selected_odd = self.odd
        original_odd = selected_odd
        choice = self.choice
        bet_slip_item = {'event_id': event_id, 'market_type_id': market_type_id,
                         'original_odd': original_odd, 'selected_odd': selected_odd, 'choice': choice}
        return bet_slip_item

    def __unicode__(self):
        return 'date: {} {} - {} market: {} choice: {} odd: {}'.format(
            self.date, self.home_team, self.away_team, self.market, self.choice, self.odd)

