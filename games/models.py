# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from collections import defaultdict
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q
from django_rq import job
# from stream_django.activity import Activity
from django_comments_xtd.moderation import moderator, SpamModerator, XtdCommentModerator
import bet_tagging.models
import bet_tagging.utils
import gutils.utils
from games.naming import mainstream_bookmakers
from zakanda.settings import forbidden_words
from actstream.models import followers

# sources field:
# Many models have a "sources" field that maps the id and name that the source uses for
# an entity, with the actual entity in our database. There is the possibility that a source
# doesn't support an id and name for a specific model. For example sportmonks doesn't support the concept
# of distinct seasons, so there is no id and name for distinct seasons. In cases like this, no source will
# be added to the sources field. Which means than no SeasonInfo entities will be created for that
# particular source.

logger = logging.getLogger(__name__)
global_team_name_max_length = 50
global_competition_name_max_length = 50

not_started = 'Not Started'
finished = 'Finished'  # finished FT (finished in full time)
finished_aet = 'Finished AET'
finished_ap = 'Finished AP'
in_play = 'in_play'
# waiting_for_p = 'Waiting for Penalty'
cancelled = 'Cancelled'
postponed = 'Postponed'
abandoned = 'Abandoned'
interrupted = 'Interrupted'
suspended = 'Suspended'
deleted = 'Deleted'


def update_bets_related_total_bets_odd(bets):
    related_total_bets = TotalBet.objects.filter(bet__in=bets).distinct()
    for total_bet in related_total_bets:
        total_bet.update_odd()
    return related_total_bets


def update_bet_event_related_bets_odd(bet_event):
    related_bets = bet_event.bet_set.all()
    for related_bet in related_bets:
        related_bet.update_odd()
    return related_bets


def update_bet_events_with_status(event, market_type, selection_status):
    """
    collect all the bet_events that are related to this specific offer (which is defined by the event and market_type)
    and update their status to given selection_status
    """
    bet_events = BetEvent.objects.filter(event=event, market_type=market_type)
    if bet_events:
        for bet_event in bet_events:
            selection = bet_event.selection
            if selection.status == Selection.void:
                # if the bet_event the result of which is being removed, has a void type result (postponed etc.)
                # then this means that this bet_event no more has odd 1, so the bet has to be updated with its
                # initial odd (that is in the new open selection entry which was passed from the void selection
                # entry within which was kept). It's related total bets odds must also be updated
                related_bets = update_bet_event_related_bets_odd(bet_event)
                related_total_bets = update_bets_related_total_bets_odd(related_bets)
            new_selection, new_created = Selection.objects.get_or_create(
                original_odd=selection.original_odd,
                selected_odd=selection.selected_odd,
                choice=selection.choice,
                status=selection_status
            )
            bet_event.selection = new_selection
            bet_event.save()
            logger.debug("Bet event %s was updated with selection %s", bet_event, new_selection)
    else:
        logger.debug("there are no bet_events for this event and market_type")
    return bet_events


def update_offer_with_result(event, market_type, market_result_type):
    market_specific_offer, market_type_order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(event)
    market_result, mr_created = MarketResult.objects.get_or_create(result=market_result_type)
    market_specific_offer.market_result = market_result
    market_specific_offer.save()
    logger.debug('%s offer was updated with market_result %s', market_specific_offer, market_result_type)
    return market_specific_offer


def remove_results(event):
    # TODO NOW SOS if you use this, you must include bet group balance handling (when a tb is becomes open
    # the balance must be updated).
    # TODO NOW make this whole process a transaction, or small transactions
    # TODO signals maybe initiate the processing with signals (both for result save and delete)
    logger.info("removing results from event %s...", event)
    if event.results.all():
        event.results.clear()
        event.status = Event.not_started
        event.save()
    else:
        logger.info("event has no results")

    logger.info("updating the marketResult of related offers and the status of related bet_events...")
    affected_bet_events = []
    market_types = event.market_types.all()
    if market_types:
        # update all the offers that this event is related to, to open (open marketResult)
        for market_type in market_types:
            updated_offer = update_offer_with_result(event, market_type, MarketResult.open)
            offer_specific_bet_events = update_bet_events_with_status(event, market_type, Selection.open)
            affected_bet_events.extend(offer_specific_bet_events)
    else:
        logger.info("there are no market offers for this event")

    logger.info("updating related bets status...")
    related_bets = Bet.objects.filter(bet_events__in=affected_bet_events).distinct()
    lost_bets, won_bets, open_bets = Bet.resettle_bets(related_bets)

    logger.info("updating related total_bets status...")
    reprocessed_bets = lost_bets + won_bets + open_bets
    related_total_bets = TotalBet.objects.filter(bets__in=reprocessed_bets).distinct()
    closed_reprocessed_total_bets, open_reprocessed_total_bets, changed_total_bets = TotalBet.resettle_total_bets(related_total_bets)
    return None


# Have in mind that this result can be determined before the end of the event, if the goals are over
def calculate_over_under_market_result(result, threshold):
    home_goals = result.home_goals
    away_goals = result.away_goals
    if home_goals + away_goals > threshold:
        over_under_market_result, created = MarketResult.objects.get_or_create(result=MarketResult.over)
    elif home_goals + away_goals < threshold:
        over_under_market_result, created = MarketResult.objects.get_or_create(result=MarketResult.under)
    else:
        logger.error("OverUnder market result wasn't calculated. Something is wrong with the goals of the result")
        over_under_market_result = None
    return over_under_market_result


def calculate_1x2_market_result(home_goals, away_goals, market_type):
    if home_goals > away_goals:
        market_result, created = MarketResult.objects.get_or_create(result=MarketResult.home)
    elif home_goals == away_goals:
        market_result, created = MarketResult.objects.get_or_create(result=MarketResult.draw)
    elif home_goals < away_goals:
        market_result, created = MarketResult.objects.get_or_create(result=MarketResult.away)
    else:
        logger.error("%s result wasn't calculated. Something is wrong with the goals of the result", market_type.name)
        market_result = None
    return market_result

# TODO for all models with choices fields. Before an entry is saved I must check if the input is valid, if it is one of


class Source(models.Model):
    name = models.CharField(max_length=50, unique=True)
    # url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    # def get_results(self, events, source=games.naming.source_names[0]):
    #     if source == games.naming.source_names[0]:
    #         xmlSoccerParser.views.get_results(events)
    #     else:
    #         logger.error('Unknown Source %s', source)


class Sport(models.Model):
    name = models.CharField(max_length=30, unique=True)
    sources = models.ManyToManyField(Source, through='SportInfo', related_name='sports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    @classmethod
    def by_sid(cls, sid, source):
        if not sid or not source:
            logger.warning("Trying to get sport from source: %s and sid: %s", source, sid)
            return
        try:
            return SportInfo.objects.get(sid=sid, source=source).sport
        except Exception as e:
            logger.warning("%s", e)
        return


class SportInfo(models.Model):
    sport = models.ForeignKey(Sport)
    source = models.ForeignKey(Source)
    sid = models.IntegerField(null=True, default=None)
    sname = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('source', 'sid', 'sname')
        get_latest_by = "created_at"

    def __unicode__(self):
        return "{} [{}: {} {}]".format(self.sport, self.source, self.sname, self.sid)


# class Continent(models.Model):
#     name = models.CharField(max_length=40, unique=True)
#     sources = models.ManyToManyField(Source, through='ContinentInfo', related_name='continents')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     def __unicode__(self):
#         return self.name
#
#
# class ContinentInfo(models.Model):
#     continent = models.ForeignKey(Continent)
#     source = models.ForeignKey(Source)
#     sid = models.IntegerField(null=True, default=None)
#     sname = models.CharField(max_length=30)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         unique_together = ('source', 'sid', 'sname')
#         get_latest_by = "created_at"
#
#     def __unicode__(self):
#         return "{} [{}: {} {}]".format(self.continent, self.source, self.sname, self.sid)


class Country(models.Model):
    name = models.CharField(max_length=30, unique=True)
    fifa_code = models.CharField(max_length=30, null=True, default=None)  # it must be unique. I deactivated
    # because a source was having duplicate codes for some countries. They will be repaired manually
    #  notice that sportmonks fifa code for UK states is ENG,NIR,SCO,WAL
    sources = models.ManyToManyField(Source, through='CountryInfo', related_name='countries')
    # continent = models.ForeignKey(Continent, null=True, default=None, related_name='countries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "{}".format(self.name)

    @classmethod
    def get_competition_ids(cls, country_name):
        competitions = Competition.objects.filter(country__name=country_name)
        competition_ids = []
        for competition in competitions:
            # logger.debug("%s gid: %s %s", competition, competition.id, competition.competitioninfo_set.all())
            competition_ids.append(competition.id)
            # for team in Team.objects.filter(competition_seasons__competition=competition):
                # logger.debug("     > %s, %s", team, team.team_infos.all())
        return competition_ids

    @classmethod
    def by_sid(cls, sid, source):
        """ We support the case in which there is a name or id change for a specific source. In this case
        both infos are connected to the same source and whatever I choose, the entity will be the same.
        The latest info is selected just for convenience. """
        if not sid or not source:
            return
        entity = None
        try:
            entity = CountryInfo.objects.filter(sid=sid, source=source).latest().country
        except CountryInfo.DoesNotExist:
            logger.info("CountryInfo for country: [sid %s source %s] doesn't exist", sid, source)
        except CountryInfo.MultipleObjectsReturned as e:
            logger.warning("%s. Country: [sid %s source %s]", e, sid, source)
        return entity

    @classmethod
    def by_sname(cls, sname, source):
        if not sname or not source:
            return
        entity = None
        try:
            # normally only one country will be filtered, the latest is used for convenience
            entity = CountryInfo.objects.filter(sid=sname, source=source).latest().country
        except CountryInfo.DoesNotExist:
            logger.info("CountryInfo for country: [sname %s source %s] doesn't exist", sname, source)
        except CountryInfo.MultipleObjectsReturned as e:
            logger.warning("%s. Country: [sid %s source %s]", e, sname, source)
        return entity


class CountryInfo(models.Model):
    country = models.ForeignKey(Country)
    source = models.ForeignKey(Source)
    sid = models.IntegerField(null=True, default=None)
    sname = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('source', 'sid', 'sname')
        get_latest_by = "created_at"

    def __unicode__(self):
        return "{} [{}: {} {}]".format(self.country, self.source, self.sname, self.sid)


class Season(models.Model):
    # TODO low add start and end date fields in Season model
    # probably the single year seasons aren't necessary since I don't use them
    season_choices = (
        ('1983', '1983'),
        ('1984', '1984'),
        ('1985', '1985'),
        ('1986', '1986'),
        ('1987', '1987'),
        ('1988', '1988'),
        ('1989', '1989'),
        ('1990', '1990'),
        ('1991', '1991'),
        ('1992', '1992'),
        ('1993', '1993'),
        ('1994', '1994'),
        ('1995', '1995'),
        ('1996', '1996'),
        ('1997', '1997'),
        ('1998', '1998'),
        ('1999', '1999'),
        ('2000', '2000'),
        ('2001', '2001'),
        ('2002', '2002'),
        ('2003', '2003'),
        ('2004', '2004'),
        ('2005', '2005'),
        ('2006', '2006'),
        ('2007', '2007'),
        ('2008', '2008'),
        ('2009', '2009'),
        ('2010', '2010'),
        ('2011', '2011'),
        ('2012', '2012'),
        ('2013', '2013'),
        ('2014', '2014'),
        ('2015', '2015'),
        ('2016', '2016'),
        ('2017', '2017'),
        ('2018', '2018'),
        ('2019', '2019'),
        ('2020', '2020'),
        ('2021', '2021'),
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2024'),
        ('2025', '2025'),
        ('2026', '2026'),
        ('2027', '2027'),
        ('2028', '2028'),
        ('2029', '2029'),
        ('2030', '2030'),
        ('93/94', '93/94'),
        ('94/95', '94/95'),  # 50
        ('95/96', '95/96'),
        ('96/97', '96/97'),
        ('97/98', '97/98'),
        ('98/99', '98/99'),
        ('99/00', '99/00'),
        ('00/01', '00/01'),
        ('01/02', '01/02'),
        ('02/03', '02/03'),
        ('03/04', '03/04'),
        ('04/05', '04/05'),  # 60
        ('05/06', '05/06'),
        ('06/07', '06/07'),
        ('07/08', '07/08'),
        ('08/09', '08/09'),
        ('09/10', '09/10'),
        ('10/11', '10/11'),
        ('11/12', '11/12'),
        ('12/13', '12/13'),
        ('13/14', '13/14'),
        ('14/15', '14/15'),  # 70
        ('15/16', '15/16'),
        ('16/17', '16/17'),
        ('17/18', '17/18'),
        ('18/19', '18/19'),
        ('19/20', '19/20'),
        ('20/21', '20/21'),
        ('21/22', '21/22'),
        ('22/23', '22/23'),
        ('23/24', '23/24'),
        ('24/25', '24/25'),
        ('25/26', '25/26'),
        ('26/27', '26/27'),
        ('27/28', '27/28'),
        ('28/29', '28/29'),
        ('29/30', '29/30'),
    )
    sources = models.ManyToManyField(Source, through='SeasonInfo', related_name='seasons')
    name = models.CharField(max_length=5, choices=season_choices, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    @classmethod
    def zakandify_season_string(cls, season_string):
        """ It zakandifies the string. The string must be in the sportmonks format: 2016/2017 and 2017 """
        years = season_string.split('/')
        if len(years) == 1:
            # single year league like Swedish League 2017
            return season_string
        elif len(years) == 2:
            init_year = years[0][-2:]
            last_year = years[1][-2:]
            return '{}/{}'.format(init_year, last_year)

    @classmethod
    def latest_season_by_sid(cls, sid, source):
        if not sid or not source:
            return
        season = None
        try:
            season = SeasonInfo.objects.filter(sid=sid, source=source).latest().season
        except SeasonInfo.DoesNotExist:
            logger.warning("There is no SeasonInfo from source %s for season: [sid %s]", source, sid)
        except SeasonInfo.MultipleObjectsReturned as e:
            logger.warning("%s. Season: [sid %s source %s]", e, sid, source)
        return season

    @classmethod
    def current_season(self):
        # zakanda.utils.season_names_from_datetime(timezone.now())
        return


class SeasonInfo(models.Model):
    """ If a source doesn't support season specific sids and names then no sources are added to the seasons
    so no SeasonInfo entries will be created """
    season = models.ForeignKey(Season)
    source = models.ForeignKey(Source)
    sid = models.IntegerField()
    sname = models.CharField(max_length=10)

    class Meta():
        # We support the case in which a source changes the sname for a season and keeps the sid or vice versa
        unique_together = ('source', 'sid', 'sname')

    def __unicode__(self):
        return '{}: {} {}'.format(self.source, self.sname, self.sid)


# TODO add commissions and taxes. They would be some other interesting data to show statistics for
class Bookmaker(models.Model):
    name = models.CharField(max_length=30, unique=True)
    url = models.URLField(unique=True, default=None, null=True)
    # commission = models.FloatField(default=0.0)
    # commission_type = models.CharField(max_length=10)
    sources = models.ManyToManyField(Source, through='BookmakerInfo', related_name='bookmakers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name


class BookmakerInfo(models.Model):
    bookmaker = models.ForeignKey(Bookmaker)
    source = models.ForeignKey(Source)
    # Some sources might not use unique ids for the bookmakers. They are identified by their sname. A None sid doesn't
    # count in the unique together. You can have more than 1 books from the same source with the same sname and null sid
    sid = models.IntegerField(null=True, default=None)
    sname = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # a source might change the sid or the name of a bookmaker. This is allowed. You can have the same sid but
        # different sname, or the same sname but different sid. So you must always get the latest entry when you
        # get a bookmaker from a specific source
        unique_together = ('source', 'sid', 'sname')
        get_latest_by = "created_at"

    def __unicode__(self):
        return "{} [{}: {} {}]".format(self.bookmaker, self.source, self.sname, self.sid)


# TODO we need a way to match a competition (also team, event) that is stored in the database with the ones that come
# from the APIs. One way can be: Competition. If there are competitions for the specific country then check their names.
# If it is the same with the one of the API (the competition has the same name in the APIs) then save a new competition_
# info. Else (the competition has a different name from the stored ones, or it is a completely new one) then store this
# competition in a file in order to add it "manually". This way we save all the competitions that have the same name
# across APIs and then we need to manually add the rest ones.

class Competition(models.Model):
    country = models.ForeignKey(Country, related_name='competitions')  # country_competitions_set
    sport = models.ForeignKey(Sport, related_name='competitions')  # sport_competitions_set
    seasons = models.ManyToManyField(Season, through='CompetitionSeason', related_name='competitions')
    sources = models.ManyToManyField(Source, through='CompetitionInfo', related_name='competitions')
    # generic_name could be the same with the xmlSoccer names initially
    generic_name = models.CharField(max_length=global_competition_name_max_length)
    # type = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{}'.format(self.generic_name)

    class Meta:
        unique_together = ('country', 'sport', 'generic_name')

    # def get_type(self):
    #     """ When the competition trees are created the correct type is assigned to the competition seasons by
    #     using the competition to type mapping (which must exist) """
    #     competition_type = CompetitionSeason.winter
    #     if self.generic_name in naming.summer_leagues:
    #         # have in mind that the type of a competition might change with the season (switch from summer
    #         # to winter) So it is better to create a type per competition and season mapping in naming instead
    #         # of just competition to type mapping
    #         competition_type = CompetitionSeason.summer
    #     return competition_type

    def current_name(self):
        # todo
        return

    def current_competition_season(self):
        return

    def get_sids(self, source):
        return

    def get_current(self):
        # todo extracting current competition from current date (and season type)
        # existing function: competition_season_by_datetime_and_competition
        competition_season = None
        return competition_season

    @classmethod
    def filter_competition_seasons(cls, generic_name, season_name, source_name=None):
        gid = cls.objects.get(generic_name=generic_name).id
        competition_season = cls.objects.get(generic_name=generic_name).competition_seasons.get(season__name=season_name)
        if source_name:
            sids = competition_season.get_sids(source_name)
            logger.info("%s id: %s %s sids: %s", competition_season, gid, source_name, sids)
        return competition_season

    @classmethod
    def by_sid(cls, sid, source):
        if not sid or not source:
            return
        try:
            return CompetitionInfo.objects.get(sid=sid, source=source).competition
        except Exception as e:
            logger.warning("%s, for sid: %s and source: %s", e, sid, source)
        return

    @classmethod
    def by_season_specific_sid(cls, sid, source):
        if not sid or not source:
            return
        competition = None
        try:
            # you can use get instead of filter. filter would be needed in case I support change of an sname within
            # the same season. Same sid different sname. Now in this case I must update the CompSeasInfo and
            # lose the previous name
            competition_season_info = CompetitionSeasonInfo.objects.filter(sid=sid, source=source).latest()
            # the following does not filter the exact match. It is like "contains"
            competition_seasons = CompetitionSeason.objects.filter(infos=competition_season_info)
            # or: competition_seasons = competition_season_info.competition_seasons.all()
            competition = competition_seasons.latest().competition
        except Exception as e:
            logger.warning("%s, [sid %s source %s] ", e, sid, source)
        return competition

    @classmethod
    def ids_list(cls, competitions):
        ids = []
        for competition in competitions:
            ids.append(competition.id)
        return ids


class CompetitionInfo(models.Model):
    # a competition can be connected with more than one info from the same source (for example if the id (our sid)
    # of the competition has changed for the specific source). For this reason there should be a get_sids
    # Competition method.
    # What the unique together constraint enforces on the other hand, is that there will be no competition
    # with more than on sgnames. So the sgname must never change or it must be updated. Notice that most
    # sources will probably have an sgname convention instead of season specific names.
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE)
    source = models.ForeignKey(Source)
    sid = models.PositiveIntegerField()
    # sgname: It is the "generic" name that a source uses for a competition.
    # If a source doesn't use such a convention then it must be set to be the same with competition's gname for clarity.
    # Season specific names are stored in CompetitionSeasonInfo.
    sgname = models.CharField(null=True, default=None, max_length=global_competition_name_max_length)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{}: {} {}'.format(self.source, self.sgname, self.sid)

    class Meta:
        # have in mind that the unique together constraints are related with the PreModels internal mapping
        # the sgname by definition is not meant to change.
        unique_together = ('source', 'sid')
        get_latest_by = "created_at"

    @classmethod
    def get_competition_info(cls, source, sid):
        """ source and sid uniquely identify a competition_info object """
        try:
            return cls.objects.get(source=source, sid=sid)
        except Exception as e:
            logger.debug('%s', e)
            return


class CompetitionSeasonInfo(models.Model):
    # have in mind that there is the case that an API could change the id or the name of a league mid season.
    # In that case instead of having a new entry in the table, I must update the existing entry.
    source = models.ForeignKey(Source)
    sid = models.PositiveIntegerField(null=True, default=None)
    sname = models.CharField(max_length=global_competition_name_max_length)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # There is the need to use the sname field to get the league in which an event belongs to, when we use the
    # "GetFixturesByDateInterval" xmlSoccer API call, because the response doesn't contain the sid of the
    # league, just the name.

    def __unicode__(self):
        return '{}: {} {}'.format(self.source, self.sname, self.sid)

    class Meta:
        unique_together = ('source', 'sname', 'sid')
        get_latest_by = "created_at"


# Have these reverse relationships in mind:
# season.competitionseason_set.get(competition=competition)
class CompetitionSeason(models.Model):
    season = models.ForeignKey(Season, related_name='competition_seasons')
    competition = models.ForeignKey(Competition, related_name='competition_seasons')
    winter = 'Winter'
    summer = 'Summer'
    type_choices = (
        (winter, 'Winter'),
        (summer, 'Summer')
    )
    type = models.CharField(max_length=6, choices=type_choices, default=winter)
    # infos vs sources: the first points to the ModelInfos directly and uses an intermediate MtM table for it
    infos = models.ManyToManyField(CompetitionSeasonInfo, related_name='competition_seasons')
    # start_date = models.DateTimeField()
    # end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{} {}, {}'.format(self.competition, self.season, self.competition.country)

    class Meta:
        # TODO get the latest comp_season based on the season
        get_latest_by = "created_at"
        unique_together = ('competition', 'season')

    def get_sids(self, source_name):
        return [info.sid for info in self.infos.filter(source__name=source_name)]

    @classmethod
    def by_sid(cls, sid, source, season=None):
        """
        :param sid: the season specific sid.
        :param source:
        :param season:

        a. There is the possibility to have more than one competition_seasons for a specific competition_season_info.

        1st possibility:
        By source's mistake. It introduces a new comp_season with an sid of an existing comp_season,
        and it assigns a new sid for the existing comp_season. In this case the old comp_seas
        ends up with 2 competition_season_infos the old and the new one.
        For example: Egypt Cup 2017 and Egypt Cup 17/18

        2nd possibility:
        If a source doesn't support a competition_season specific sid then
        if we use the competition sid as the competition season sid then many competition seasons will be returned
        for a given sid. (not the case for sportmonks)

        In these cases you can get a specific competition_season by giving the season argument too.

        b. There is the possibility to have one comp_seas connected with more than one comp_seas_info.
        For example same sid but name changed. In this case the latest info is selected and that is used
        to select the competition_seasons.
        """
        if not sid or not source:
            return
        competition_seasons = None
        try:
            competition_season_info = CompetitionSeasonInfo.objects.filter(sid=sid, source=source).latest()
            competition_seasons = cls.objects.filter(infos=competition_season_info)
            # competition_seasons = competition_season_info.competition_seasons.all()
            if season:
                # it must be 1 entity (a sid can be connected with more than one names but I get the latest info
                # above (so a particular name). Returned as queryset for uniformity of return type
                competition_seasons = competition_seasons.filter(season=season)
        except Exception as e:
            logger.warning("Can't get a competition season by sid: %s [source: %s], %s", sid, source, e)
        return competition_seasons


class Team(models.Model):
    generic_name = models.CharField(max_length=global_team_name_max_length, unique=True)
    competition_seasons = models.ManyToManyField(CompetitionSeason)
    sources = models.ManyToManyField(Source, through='TeamInfo', related_name='teams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{}'.format(
            self.generic_name,
            # NOTICE: If you print a team instance with the following line active, then it will return a unicode error
            # for Turkish Super Lig. This is only when Super Lig is printed from in here. If you print Competitions
            # there is no problem! It has to do with the iterator from inside the class or something
            # [competition_season for competition_season in self.competition_seasons.all()],
            # ', '.join(competition_season.competition.generic_name+' '+competition_season.season.name for competition_season in self.competition_seasons.all())
        )

    def competitions_by_season(self, season):
        # get in which competitions the team participated in the given season
        # todo
        competition_seasons = []
        return competition_seasons

    def get_sids(self, source_name):
        return [info.sid for info in self.team_infos.filter(source__name=source_name)]

    def describe(self):
        logger.info("\n")
        logger.info("generic name: %s id: %s %s", self.generic_name, self.id,
                    [(info.source.name, info.sid, info.sname) for info in self.team_infos.all()])
        competition_season_dict = defaultdict(int)
        countries_dict = defaultdict(int)
        for competition_season in self.competition_seasons.all():
            country = competition_season.competition.country
            countries_dict[country] += 1
            competition_season_dict[competition_season] += 1
            logger.info('     %s id: %s %s country: %s id: %s %s', competition_season,
                        competition_season.id, [(info.source.name, info.sid) for info in competition_season.infos.all()],
                        country.name, country.id, [(info.source.name, info.sid) for info in country.countryinfo_set.all()])

    @classmethod
    def by_sid(cls, sid, source):
        """ We support the case in which there is a name or id change for a specific source. In this case
        both infos are connected to the same source and whatever I choose, the entity (team) will be the same.
        The latest info is selected just for convenience. """
        if not sid or not source:
            return
        team = None
        try:
            team = TeamInfo.objects.filter(sid=sid, source=source).latest().team
        except TeamInfo.DoesNotExist:
            logger.warning("TeamInfo for team: [sid %s source %s] doesn't exist", sid, source)
        except TeamInfo.MultipleObjectsReturned as e:
            logger.warning("%s. Team: [sid %s source %s]", e, sid, source)
        return team

    @classmethod
    def by_specific_sid(cls, sid, source):
        return

    @classmethod
    def teams_with_many_infos(cls, source_name):
        """ returns the teams that have more than one team info entries from the given source """
        teams = cls.objects.filter(team_infos__source__name=source_name).annotate(num_team_infos=Count('team_infos')).filter(num_team_infos__gt=1)
        logger.info("number of teams with more than one infos from the same source: %s", teams.count())
        for team in teams:
            logger.info("%s %s", team, [(team_info.sid, team_info.sname) for team_info in team.team_infos.filter(source__name=source_name)])
        return teams

    @classmethod
    def teams_with_many_countries(cls):
        """ :return: a list of teams that belong to more than one countries where countries are not in the
            international ones (Europe, International). This way we can identify possible duplicate teams
            teams that have the same sid and name but they should have been distinct teams """
        # teams = cls.objects.annotate(num_countries=Count('competition_seasons__competition__country')).\
        #     filter(num_countries__gt=1)
        all_teams = cls.objects.all()
        all_teams = all_teams.exclude(generic_name__contains="II")  # There are many 2nd teams that participated in an
        # England's friendly summer league
        teams = []
        internationals = Country.objects.filter(name__in=['Europe', 'International', 'World'])
        for team in all_teams:
            countries = defaultdict(int)
            for competition_season in team.competition_seasons.all():
                country = competition_season.competition.country
                if country not in internationals:
                    countries[competition_season.competition.country] += 1

            if len(countries.keys()) > 1:
                # logger.debug("%s %s", team, team.team_infos.all())
                # logger.debug("  > %s", countries)
                teams.append(team)
        return teams


class TeamInfo(models.Model):
    team = models.ForeignKey(Team, related_name='team_infos')
    source = models.ForeignKey(Source, related_name='team_infos')
    sid = models.PositiveIntegerField()
    sname = models.CharField(max_length=global_team_name_max_length)
    # timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # which sources support the specific "home_team"
    # Source.objects.filter(teams=home_team)

    # # which sources support the "home_team" and have an sid for it that is "sid"
    # Source.objects.filter(teams=home_team, team_infos__sid=sid)
    #
    # team = specific_source.team_infos.filter(sid=sid).latest().team
    # # same as
    # team = TeamInfo.objects.filter(sid=sid, source=source).latest().team
    
    class Meta:
        unique_together = ("source", "sid", "sname")
        get_latest_by = "created_at"

    def __unicode__(self):
        return '{}: {} {}'.format(self.source, self.sname, self.sid)


# A comment by the creator of xmlSoccer, for a way to request live scores.
# Hi Edwin, you retrieve the fixtures for all season, and every minute you query your database if there's any game
# that's starting within the prior 2 hours and the next 2 hours (4 hour timewindow). If there is, you request
# livescore, if not you don't.
class Result(models.Model):
    # todo high: Command to add manually results to events and then settle them with that. This
    # in order to deal with empty or wrong source results data
    """
    ht (half time), et_ht (extra time half time), ft (full time)
    1-0 62' (0' extra min), 1-1 90'(2'), 1-1 90' (0') ft final,
    1-0 62' (0'), 1-1 90'(2'), 1-1 90' (0') ft, 2-1 112' (0'), 2-1 120' (0') et final,
    """
    # not_started = 'Not_Started' # it is more efficient/faster to have no result for the not started events
    in_play_result = 'IN_PLAY'
    ht_result = 'HT'
    ft_result = 'FT'
    et_ht_result = 'ET_HT'
    et_result = 'ET'
    pen_result = 'PEN'
    # void = MarketResult.void

    postponed = postponed
    cancelled = cancelled
    abandoned = abandoned
    interrupted = interrupted
    suspended = suspended
    deleted = deleted

    void_types = [postponed, cancelled, abandoned, interrupted, suspended, deleted]
    decision_types = void_types + [ft_result]
    strongest_type = ft_result
    # decision_types = [ft_result, void]

    result_types = (
        (in_play_result, in_play_result),
        (ht_result, ht_result),
        (ft_result, ft_result),
        (et_ht_result, et_ht_result),
        (et_result, et_result),
        (pen_result, pen_result),
        (postponed, postponed),
        (cancelled, cancelled),
        (abandoned, abandoned),
        (interrupted, interrupted),
        (suspended, suspended),
        (deleted, deleted)
    )

    home_goals = models.PositiveIntegerField()
    away_goals = models.PositiveIntegerField()
    minute = models.PositiveIntegerField()
    extra_minute = models.PositiveIntegerField(default=0)  # it isn't used
    type = models.CharField(max_length=15, choices=result_types, default=in_play_result)
    final = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        final_str = " Final" if self.final else ""
        if self.type not in self.void_types:
            return '{}-{} {}{}'.format(self.home_goals, self.away_goals, self.type, final_str)
        return "{} {}".format(self.type, final_str)

    def map_to_status(self):
        """ Maps a result's type to event status. The result must be final. If not then a ft_result
        might not be the final result and so the status of the event must not be "finished" """
        if not self.final:
            logger.debug("result %s is not Final, corresponding event status is %s", self, Event.in_play)
            return Event.in_play
        result_type_to_event_status = {
            self.ft_result: Event.finished,
            self.et_result: Event.finished_aet,
            self.pen_result: Event.finished_ap,

            self.abandoned: Event.abandoned,
            self.postponed: Event.postponed,
            self.interrupted: Event.interrupted,
            self.cancelled: Event.cancelled,
            self.suspended: Event.suspended,
            self.deleted: Event.deleted,
        }
        status = result_type_to_event_status.get(self.type, Event.in_play)
        if status == Event.in_play:
            logger.warning("final result of type %s is not mapped to an Event status", self.type)
        logger.debug("result [%s] mapped to status [%s]", self, status)
        return status


class MarketType(models.Model):
    """
    have in mind that market specific thresholds are extracted by the markets name (for example in
    markets_creation.get_thresholds() function)
    """

    # generic types: threshold dependent market type names
    generic_goals_ovun = 'Goals Over Under'
    generic_handicap = 'Handicap'
    generic_asian_handicap = 'Asian Handicap'
    generic_types = [generic_asian_handicap, generic_goals_ovun, generic_handicap]

    winner_market_type = 'Full Time Result'
    over_under_25_market_type = 'Goals Over Under 2.5'
    double_chance_market_type = 'Double chance'

    handicap_plus1_market_type = 'Handicap 1-0'
    handicap_plus2_market_type = 'Handicap 2-0'
    handicap_plus3_market_type = 'Handicap 3-0'
    handicap_minus1_market_type = 'Handicap 0-1'
    handicap_minus2_market_type = 'Handicap 0-2'
    handicap_minus3_market_type = 'Handicap 0-3'

    asian_handicap_plus05_market_type = 'Asian Handicap +0.5'
    asian_handicap_plus15_market_type = 'Asian Handicap +1.5'
    asian_handicap_plus25_market_type = 'Asian Handicap +2.5'
    asian_handicap_0_market_type = 'Asian Handicap 0'
    asian_handicap_plus1_market_type = 'Asian Handicap +1'
    asian_handicap_plus2_market_type = 'Asian Handicap +2'
    asian_handicap_minus05_market_type = 'Asian Handicap -0.5'
    asian_handicap_minus15_market_type = 'Asian Handicap -1.5'
    asian_handicap_minus25_market_type = 'Asian Handicap -2.5'
    asian_handicap_minus1_market_type = 'Asian Handicap -1'
    asian_handicap_minus2_market_type = 'Asian Handicap -2'
    asian_handicap_0plus05_market_type = 'Asian Handicap 0,+0.5'
    asian_handicap_plus05plus1_market_type = 'Asian Handicap +0.5,+1'
    asian_handicap_plus1plus15_market_type = 'Asian Handicap +1,+1.5'
    asian_handicap_plus15plus2_market_type = 'Asian Handicap +1.5,+2'
    asian_handicap_plus2plus25_market_type = 'Asian Handicap +2,+2.5'
    asian_handicap_0minus05_market_type = 'Asian Handicap 0,-0.5'
    asian_handicap_minus05minus1_market_type = 'Asian Handicap -0.5,-1'
    asian_handicap_minus1minus15_market_type = 'Asian Handicap -1,-1.5'
    asian_handicap_minus15minus2_market_type = 'Asian Handicap -1.5,-2'
    asian_handicap_minus2minus25_market_type = 'Asian Handicap -2,-2.5'

    market_type_choices = (
        (winner_market_type, 'Full Time Result'),
        (over_under_25_market_type, 'Goals Over Under 2.5'),
        (double_chance_market_type, 'Double chance'),

        (handicap_plus1_market_type, 'Handicap 1-0'),
        (handicap_plus2_market_type, 'Handicap 2-0'),
        (handicap_plus3_market_type, 'Handicap 3-0'),
        (handicap_minus1_market_type, 'Handicap 0-1'),
        (handicap_minus2_market_type, 'Handicap 0-2'),
        (handicap_minus3_market_type, 'Handicap 0-3'),

        (asian_handicap_plus05_market_type, 'Asian Handicap +0.5'),
        (asian_handicap_plus15_market_type, 'Asian Handicap +1.5'),
        (asian_handicap_plus25_market_type, 'Asian Handicap +2.5'),
        (asian_handicap_0_market_type, 'Asian Handicap 0'),
        (asian_handicap_plus1_market_type, 'Asian Handicap +1'),
        (asian_handicap_plus2_market_type, 'Asian Handicap +2'),
        (asian_handicap_minus05_market_type, 'Asian Handicap -0.5'),
        (asian_handicap_minus15_market_type, 'Asian Handicap -1.5'),
        (asian_handicap_minus25_market_type, 'Asian Handicap -2.5'),
        (asian_handicap_minus1_market_type, 'Asian Handicap -1'),
        (asian_handicap_minus2_market_type, 'Asian Handicap -2'),
        (asian_handicap_0plus05_market_type, 'Asian Handicap 0,+0.5'),
        (asian_handicap_plus05plus1_market_type, 'Asian Handicap +0.5,+1'),
        (asian_handicap_plus1plus15_market_type, 'Asian Handicap +1,+1.5'),
        (asian_handicap_plus15plus2_market_type, 'Asian Handicap +1.5,+2'),
        (asian_handicap_plus2plus25_market_type, 'Asian Handicap +2,+2.5'),
        (asian_handicap_0minus05_market_type, 'Asian Handicap 0,-0.5'),
        (asian_handicap_minus05minus1_market_type, 'Asian Handicap -0.5,-1'),
        (asian_handicap_minus1minus15_market_type, 'Asian Handicap -1,-1.5'),
        (asian_handicap_minus15minus2_market_type, 'Asian Handicap -1.5,-2'),
        (asian_handicap_minus2minus25_market_type, 'Asian Handicap -2,-2.5'),
    )

    abbreviations = {
        winner_market_type: 'FTR',
        over_under_25_market_type: 'G O/U 2.5',
        double_chance_market_type: 'DC',

        handicap_plus1_market_type: 'HP 1-0',
        handicap_plus2_market_type: 'HP 2-0',
        handicap_plus3_market_type: 'HP 3-0',
        handicap_minus1_market_type: 'HP 0-1',
        handicap_minus2_market_type: 'HP 0-2',
        handicap_minus3_market_type: 'HP 0-3',

        asian_handicap_plus05_market_type: 'AHP +0.5',
        asian_handicap_plus15_market_type: 'AHP +1.5',
        asian_handicap_plus25_market_type: 'AHP +2.5',
        asian_handicap_0_market_type: 'AHP 0',
        asian_handicap_plus1_market_type: 'AHP +1',
        asian_handicap_plus2_market_type: 'AHP +2',
        asian_handicap_minus05_market_type: 'AHP -0.5',
        asian_handicap_minus15_market_type: 'AHP -1.5',
        asian_handicap_minus25_market_type: 'AHP -2.5',
        asian_handicap_minus1_market_type: 'AHP -1',
        asian_handicap_minus2_market_type: 'AHP -2',
        asian_handicap_0plus05_market_type: 'AHP 0:+0.5',
        asian_handicap_plus05plus1_market_type: 'AHP +0.5,+1',
        asian_handicap_plus1plus15_market_type: 'AHP +1,+1.5',
        asian_handicap_plus15plus2_market_type: 'AHP +1.5,+2',
        asian_handicap_plus2plus25_market_type: 'AHP +2,+2.5',
        asian_handicap_0minus05_market_type: 'AHP 0,-0.5',
        asian_handicap_minus05minus1_market_type: 'AHP -0.5,-1',
        asian_handicap_minus1minus15_market_type: 'AHP -1,-1.5',
        asian_handicap_minus15minus2_market_type: 'AHP -1.5,-2',
        asian_handicap_minus2minus25_market_type: 'AHP -2,-2.5',
    }

    name = models.CharField(max_length=30, choices=market_type_choices, unique=True)
    winner_offers = models.ManyToManyField('WinnerOffer')
    over_under_offers = models.ManyToManyField('OverUnderOffer')
    double_chance_offers = models.ManyToManyField('DoubleChanceOffer')
    handicap_offers = models.ManyToManyField('HandicapOffer')
    asian_handicap_offers = models.ManyToManyField('AsianHandicapOffer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def count_market_specific_offers(self):
        winner_offers = self.winner_offers.all().count()
        over_under_offers = self.over_under_offers.all().count(),
        double_chance_offers = self.double_chance_offers.all().count(),
        handicap_offers = self.handicap_offers.all().count(),
        asian_handicap_offers = self.asian_handicap_offers.all().count(),
        return winner_offers, over_under_offers, double_chance_offers, handicap_offers, asian_handicap_offers

    def abbreviation(self):
        return self.abbreviations.get(self.name, self.name)

    def __unicode__(self):
        return self.name

    def get_offers(self, event):
        """ Get all the offer objects for a market and an event """
        market_type = self.name
        if market_type == self.winner_market_type:
            return self.winner_offers.filter(event=event)
        elif market_type == self.double_chance_market_type:
            return self.double_chance_offers.filter(event=event)
        elif market_type.find('Goals Over Under') != -1:
            return self.over_under_offers.filter(event=event)
        elif market_type.find("Handicap") != -1 and market_type.find("Asian") == -1:
            return self.handicap_offers.filter(event=event)
        else:
            logger.error('an option is missing')
            return

    def get_thresholds(self):
        """
        Returns the thresholds for each market as they are extracted from market name. It could be used instead of
        manually controlling with elifs each individual market name as the get_offer_thresholds_and_order does
        """
        market_name = self.name

        if market_name == self.winner_market_type:
            return market_name, None, None

        elif market_name.find('Goals Over Under') != -1:
            threshold = float(market_name.split(" ")[3])
            return market_name, threshold, None

        elif market_name == self.double_chance_market_type:
            return market_name, None, None

        elif market_name.find("Handicap") != -1 and market_name.find("Asian") == -1:
            handicap_score = market_name.split(" ")[1].split("-")
            home_goals = float(handicap_score[0])
            threshold = home_goals
            if home_goals == 0:
                threshold = float(handicap_score[1]) * -1
            return market_name, threshold, None

        elif market_name.find("Asian Handicap") != -1:
            handicap_values = market_name.split(" ")[2].split(",")
            threshold_1 = float(handicap_values[0])
            threshold_2 = None
            if len(handicap_values) == 2:
                threshold_2 = float(handicap_values[1])
            return market_name, threshold_1, threshold_2

        else:
            logger.error('Unsupported market type %s', market_name)
            return None, None, None

    def get_offer_thresholds_and_order(self, event):
        """ A MarketType and an Event object uniquely identify a MarketOffer (that contains the odd objects) """
        # logger.debug("iter: getting the market specific offer (its thresholds and order) of given event and market
        # type...")
        threshold_2 = None
        threshold_1 = None

        if self.name == self.winner_market_type:
            market_specific_offer = self.winner_offers.filter(event=event).first()
            order = 1

        elif self.name == self.double_chance_market_type:
            market_specific_offer = self.double_chance_offers.filter(event=event).first()
            order = 2

        # OVER UNDER MARKETS
        elif self.name == self.over_under_25_market_type:
            threshold_1 = 2.5
            market_specific_offer = self.over_under_offers.filter(event=event, threshold=threshold_1).first()
            order = 3

        # HANDICAP MARKETS
        elif self.name == self.handicap_plus1_market_type:
            threshold_1 = 1
            market_specific_offer = self.handicap_offers.filter(event=event, threshold=threshold_1).first()
            order = 4
        elif self.name == self.handicap_plus2_market_type:
            threshold_1 = 2
            market_specific_offer = self.handicap_offers.filter(event=event, threshold=threshold_1).first()
            order = 5
        elif self.name == self.handicap_plus3_market_type:
            threshold_1 = 3
            market_specific_offer = self.handicap_offers.filter(event=event, threshold=threshold_1).first()
            order = 6
        elif self.name == self.handicap_minus1_market_type:
            threshold_1 = -1
            market_specific_offer = self.handicap_offers.filter(event=event, threshold=threshold_1).first()
            order = 7
        elif self.name == self.handicap_minus2_market_type:
            threshold_1 = -2
            market_specific_offer = self.handicap_offers.filter(event=event, threshold=threshold_1).first()
            order = 8
        elif self.name == self.handicap_minus3_market_type:
            threshold_1 = -3
            market_specific_offer = self.handicap_offers.filter(event=event, threshold=threshold_1).first()
            order = 9

        # ASIAN HANDICAP MARKETS
        elif self.name == self.asian_handicap_0_market_type:
            threshold_1 = 0
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 10
        elif self.name == self.asian_handicap_plus05_market_type:
            threshold_1 = 0.5
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 11
        elif self.name == self.asian_handicap_plus1_market_type:
            threshold_1 = 1
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 12
        elif self.name == self.asian_handicap_plus15_market_type:
            threshold_1 = 1.5
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 13
        elif self.name == self.asian_handicap_plus2_market_type:
            threshold_1 = 2
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 14
        elif self.name == self.asian_handicap_plus25_market_type:
            threshold_1 = 2.5
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 15

        elif self.name == self.asian_handicap_minus05_market_type:
            threshold_1 = -0.5
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 16
        elif self.name == self.asian_handicap_minus1_market_type:
            threshold_1 = -1
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 17
        elif self.name == self.asian_handicap_minus15_market_type:
            threshold_1 = -1.5
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 18
        elif self.name == self.asian_handicap_minus2_market_type:
            threshold_1 = -2
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 19
        elif self.name == self.asian_handicap_minus25_market_type:
            threshold_1 = -2.5
            threshold_2 = None
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 20

        elif self.name == self.asian_handicap_0plus05_market_type:
            threshold_1 = 0
            threshold_2 = 0.5
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 21
        elif self.name == self.asian_handicap_plus05plus1_market_type:
            threshold_1 = 0.5
            threshold_2 = 1
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 22
        elif self.name == self.asian_handicap_plus1plus15_market_type:
            threshold_1 = 1
            threshold_2 = 1.5
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 23
        elif self.name == self.asian_handicap_plus15plus2_market_type:
            threshold_1 = 1.5
            threshold_2 = 2
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 24
        elif self.name == self.asian_handicap_plus2plus25_market_type:
            threshold_1 = 2
            threshold_2 = 2.5
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 25
        elif self.name == self.asian_handicap_0minus05_market_type:
            threshold_1 = 0
            threshold_2 = -0.5
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 26
        elif self.name == self.asian_handicap_minus05minus1_market_type:
            threshold_1 = -0.5
            threshold_2 = -1
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 27
        elif self.name == self.asian_handicap_minus1minus15_market_type:
            threshold_1 = -1
            threshold_2 = -1.5
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 28
        elif self.name == self.asian_handicap_minus15minus2_market_type:
            threshold_1 = -1.5
            threshold_2 = -2
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 29
        elif self.name == self.asian_handicap_minus2minus25_market_type:
            threshold_1 = -2
            threshold_2 = -2.5
            market_specific_offer = self.asian_handicap_offers.filter(event=event, threshold_1=threshold_1, threshold_2=threshold_2).first()
            order = 30

        else:
            logger.error('Unknown market_type name')
            market_specific_offer = None
            order = None

        return market_specific_offer, order, threshold_1, threshold_2

    def get_market_odds(self, event, bookmaker=None):
        """ Get all the odd objects for a market and an event (and optionally per bookmaker)
        :param bookmaker: bookmaker object, string "mainstream" or None. get odds from the given bookmaker,
        from the mainstream ones or from any one.
        :param event:
        """
        # uses: check if odd in allowed odds, show odds development, compare odds etc.
        offer, order, threshold_1, threshold_2 = self.get_offer_thresholds_and_order(event)
        if not offer:
            return
        # offer_odds = WinnerOfferOdd.objects.filter(offer=offer, bookmaker=bookmaker)
        # odds = WinnerOdd.objects.filter(offer_odds__in=offer_odds)
        if bookmaker and bookmaker != 'mainstream':
            # .order_by('timestamp', 'created_at') so that odds are ordered too. It makes the query more expensive
            offer_odds = offer.offer_odds.filter(bookmaker=bookmaker).order_by('timestamp', 'created_at').select_related('odd')
        elif bookmaker == 'mainstream':
            offer_odds = offer.offer_odds.filter(bookmaker__name__in=mainstream_bookmakers).order_by(
                'timestamp', 'created_at').select_related('odd')
        else:
            offer_odds = offer.offer_odds.all().order_by(
                'timestamp', 'created_at').select_related('odd')
        odds = []
        for offer_odd in offer_odds:
            logger.debug('offer odd: [%s] %s', offer_odd.timestamp, offer_odd.odd)
            odds.append(offer_odd.odd)
        return odds

    @classmethod
    def get_name(cls, threshold_1, threshold_2, generic_type):
        if generic_type not in cls.generic_types:
            return

        market_name = None

        if generic_type == cls.generic_goals_ovun:
            threshold = threshold_1
            if threshold == 2.5:
                market_name = cls.over_under_25_market_type
            else:
                logger.debug('threshold %s (%s) for %s is not yet supported', threshold, type(threshold), generic_type)
            return market_name

        elif generic_type == cls.generic_handicap:
            threshold = threshold_1
            if threshold == 1:
                market_name = cls.handicap_plus1_market_type
            elif threshold == 2:
                market_name = cls.handicap_plus2_market_type
            elif threshold == 3:
                market_name = cls.handicap_plus3_market_type
            elif threshold == -1:
                market_name = cls.handicap_minus1_market_type
            elif threshold == -2:
                market_name = cls.handicap_minus2_market_type
            elif threshold == -3:
                market_name = cls.handicap_minus3_market_type
            else:
                logger.debug('threshold %s for %s is not yet supported', threshold, generic_type)
            return market_name

        elif generic_type == cls.generic_asian_handicap:
            if not threshold_1 or not threshold_2:
                logger.debug('threshold %s-%s for %s is not yet supported', threshold_1, threshold_2, generic_type)
                return market_name
            if threshold_1 == 0 and not threshold_2:
                market_name = cls.asian_handicap_0_market_type
            elif threshold_1 == 0.5 and not threshold_2:
                market_name = cls.asian_handicap_plus05_market_type
            elif threshold_1 == 1 and not threshold_2:
                market_name = cls.asian_handicap_plus1_market_type
            elif threshold_1 == 1.5 and not threshold_2:
                market_name = cls.asian_handicap_plus15_market_type
            elif threshold_1 == 2 and not threshold_2:
                market_name = cls.asian_handicap_plus2_market_type
            elif threshold_1 == 2.5 and not threshold_2:
                market_name = cls.asian_handicap_plus25_market_type

            elif threshold_1 == -0.5 and not threshold_2:
                market_name = cls.asian_handicap_minus05_market_type
            elif threshold_1 == -1 and not threshold_2:
                market_name = cls.asian_handicap_minus1_market_type
            elif threshold_1 == -1.5 and not threshold_2:
                market_name = cls.asian_handicap_minus15_market_type
            elif threshold_1 == -2 and not threshold_2:
                market_name = cls.asian_handicap_minus2_market_type
            elif threshold_1 == -2.5 and not threshold_2:
                market_name = cls.asian_handicap_minus25_market_type

            elif threshold_1 == 0 and threshold_2 == 0.5:
                market_name = cls.asian_handicap_0plus05_market_type
            elif threshold_1 == 0.5 and threshold_2 == 1:
                market_name = cls.asian_handicap_plus05plus1_market_type
            elif threshold_1 == 1 and threshold_2 == 1.5:
                market_name = cls.asian_handicap_plus1plus15_market_type
            elif threshold_1 == 1.5 and threshold_2 == 2:
                market_name = cls.asian_handicap_plus15plus2_market_type
            elif threshold_1 == 2 and threshold_2 == 2.5:
                market_name = cls.asian_handicap_plus2plus25_market_type

            elif threshold_1 == 0 and threshold_2 == -0.5:
                market_name = cls.asian_handicap_0minus05_market_type
            elif threshold_1 == -0.5 and threshold_2 == -1:
                market_name = cls.asian_handicap_minus05minus1_market_type
            elif threshold_1 == -1 and threshold_2 == -1.5:
                market_name = cls.asian_handicap_minus1minus15_market_type
            elif threshold_1 == -1.5 and threshold_2 == -2:
                market_name = cls.asian_handicap_minus15minus2_market_type
            elif threshold_1 == -2 and threshold_2 == -2.5:
                market_name = cls.asian_handicap_minus2minus25_market_type
            else:
                logger.debug('threshold %s-%s for %s is not yet supported', threshold_1, threshold_2, generic_type)
            return market_name

        return market_name


class Event(models.Model):
    date = models.DateTimeField('Event date')
    competition_season = models.ForeignKey(CompetitionSeason, related_name='competitionseason_events_set')
    home_team = models.ForeignKey(Team, related_name='as_home_team_events_set')
    away_team = models.ForeignKey(Team, related_name='as_away_team_events_set')
    round = models.PositiveIntegerField(null=True, blank=True, default=None)
    # public attribute is an easy and quick way to hide problematic events from users.
    public = models.BooleanField(default=True)

    # have in mind that an event that has started but has no results yet it still has a "not_started" status
    # I can update their status to in_play if they are checked for status. Whenever I call for get results
    # I call for the events that have no decision type result
    not_started = not_started
    finished = finished
    finished_aet = finished_aet
    finished_ap = finished_ap
    in_play = in_play
    # waiting_for_p = 'Waiting for Penalty'
    cancelled = cancelled
    postponed = postponed
    abandoned = abandoned
    interrupted = interrupted
    suspended = suspended
    deleted = deleted

    # todo have in mind: There can be void events with no void tbets
    # an event can have an ft_result and an interrupted result (interrupted in extra time)
    # in this case the status of the event (which is determined by the final result as of now) will be a void
    # status, but the tbets on it will not be void since they are settled with the ft_result.
    void_event_statuses = [cancelled, postponed, abandoned, interrupted, suspended, deleted]
    finished_event_statuses = [finished, finished_aet, finished_ap]
    open_event_statuses = [not_started, in_play]

    # have in mind local event xmlsoccer 350725 Hamilton St Johnstone. Probably it has been manually set to status void
    # but it has an FT result.

    status_choices = (
        (not_started, 'Not Started'),
        (finished, 'Finished'),
        (finished_aet, 'Finished AET (Added Extra Time)'),
        (finished_ap, 'Finished AP (Added Penalty)'),
        (cancelled, 'Cancelled'),
        (postponed, 'Postponed'),
        (abandoned, 'Abandoned'),
        (interrupted, interrupted),
        (suspended, suspended),
        (deleted, deleted),
        (in_play, 'in_play'),
    )

    # todo delete the status field. the status can be calculated from the event's results. I can make it a
    # property with @property so that I don't have to change the references.
    status = models.CharField(max_length=35, choices=status_choices, default=not_started)
    market_types = models.ManyToManyField(MarketType)
    results = models.ManyToManyField(Result, blank=True)    # allowed to be blank in forms including the admin
    sources = models.ManyToManyField(Source, through='EventInfo')
    live = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __repr__(self):
        return '{0}: {1} round {2} {3} {4} {5} {6}'.format(
            self.date.strftime('%Y-%m-%d %H:%M:%S %z'),
            self.competition_season,
            self.round,
            self.home_team,
            self.away_team,
            self.status,
            self.results.all()
        )

    def __unicode__(self):
        return '{} {} - {} {} {}'.format(
            self.date.strftime('%Y-%m-%d %H:%M:%S %z'),
            self.home_team,
            self.away_team,
            self.competition_season,
            self.status
        )

    class Meta:
        # TODO do we need it?
        ordering = ['date']
        get_latest_by = 'date'

    def settle_related_bet_events(self, market_type, market_result):
        logger.debug("settling bet_events for event %s market_type %s and market_result %s ...", self, market_type, market_result)
        bet_events = self.bet_events.filter(market_type=market_type)
        if bet_events:
            for bet_event in bet_events:
                # only open bet_events are settled
                bet_event.settle(market_result)
        else:
            logger.debug("there are no bet_events for this event and market_type")
        return bet_events

    def calculate_market_result(self, market_type, result='auto', strongest_type=Result.ft_result):
        # TODO GENERIC IF statement for market_types. Here we need to use again the if statement for all markets
        # as we do in get_market_specific_offer_thresholds_and_order function.
        # So we need to make it generic with function as argument.
        logger.debug("calculating market result for %s...", market_type)

        if result == 'auto':
            # get the decision type result and settle the event using that result
            result = self.get_decision_result()
            if not result:
                logger.debug('event %s has no decision_result_type', self)
                return

        if not result:
            return

        if result.type == strongest_type:
            home_goals = result.home_goals
            away_goals = result.away_goals

            if market_type.name == MarketType.winner_market_type:
                market_specific_result = calculate_1x2_market_result(home_goals, away_goals, market_type)

            elif market_type.name == MarketType.double_chance_market_type:
                # Just have in mind that for this market the bet_event choices are different from the result choices
                market_specific_result = calculate_1x2_market_result(home_goals, away_goals, market_type)

            elif market_type.name.find('Goals Over Under') != -1:
                market_specific_offer, order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(self)
                market_specific_result = calculate_over_under_market_result(result, threshold_1)

            elif market_type.name.find("Handicap") != -1 and market_type.name.find("Asian") == -1:
                market_specific_offer, order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(self)
                home_goals = home_goals + threshold_1
                market_specific_result = calculate_1x2_market_result(home_goals, away_goals, market_type)

            elif market_type.name == MarketType.asian_handicap_market_type:
                market_specific_offer, order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(self)
                # market_specific_result = calculate_asianhandicap_market_result(result, threshold_1, threshold_2)
                market_specific_result = None

            else:
                logger.error('Unknown market_type name')
                market_specific_result = None

        elif result.type in Result.void_types:
            market_specific_result, void_created = MarketResult.objects.get_or_create(result=MarketResult.void)

        else:
            market_specific_result = None
        logger.debug("market result for %s is %s", market_type, market_specific_result)
        return market_specific_result

    def execute_settlement(self, result):
        """
        "closed" market_types results are recalculated (this adds some delay if closed events are settled)
        "closed" bet_events are not recalculated. Have in mind that if closed bet_events were recalculated their
        related bets and tbets must be recalculated also
        """
        logger.debug("processing market offers of finished event...")
        bet_events_per_market = {}
        market_types = self.market_types.all()
        if market_types:
            for market_type in market_types:
                # return the market_result object for each market_type of the event.
                # We will use it to update the market_offer
                market_result = self.calculate_market_result(market_type, result)
                # print('market_type: ', market_type, 'market_result: ', market_result)
                if market_result:
                    # One market_type and one event, uniquely identify a market_specific_offer
                    market_specific_offer, market_type_order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(self)
                    if market_specific_offer:
                        old_market_result = market_specific_offer.market_result

                        # TODO have in mind OPEN CHECK
                        # if old_market_result.result == games.models.MarketResult.open:
                        # I don't make this check because in case of submitting past bets, there can be a new bet event
                        # with new selection (new odds) that is connected with this market_offer. So the market offer
                        # might be closed but the new bet events will be open. So this open check must not be done
                        # (at least for submitting past bets). After all only open bet_events are recalculated so
                        # this open check doesn't add serious delay
                        # I could make the check and move the bev settlement outside of here

                        market_specific_offer.market_result = market_result
                        market_specific_offer.save()
                        logger.debug('%s offer was updated with market_result %s', market_specific_offer, market_result)
                        calculated_bet_events = self.settle_related_bet_events(market_type, market_result)
                        bet_events_per_market[market_type] = calculated_bet_events
                        # else:
                        #     logger.warning("event %s has closed market_result. It won't be updated
                        #     with another market_result", event)
                    else:
                        logger.warning("event %s has no offer for %s market_type", self, market_type)
                else:
                    logger.debug("market result is None")
        else:
            logger.debug("there are no market offers for this event")
        return bet_events_per_market

    def settle_market_offers_and_bevs(self, result='auto', decision_types=Result.decision_types):
        """
        It processes an event based on a result and a given decision type result.
        :param result: a result object, None or its default value. default value is
        for searching the event's results automatically to find a decision type result
        """
        # todo fix issue with None and 'auto'. Have None instead of 'auto' and something else for void result
        related_bet_events = []
        if result == 'auto':
            # get the decision type result and settle the event using that result
            result = self.get_decision_result()
            if not result:
                logger.debug('event %s has no decision_result_type', self)
                return related_bet_events

        if not result:  # the result given is None
            return related_bet_events

        if result.type in decision_types:
            logger.debug("result is of decision type")
            related_calculated_bet_events_per_market = self.execute_settlement(result)
            related_bet_events = gutils.utils.list_from_dict(related_calculated_bet_events_per_market)
        else:
            logger.debug('result is not of decision type, event will not be processed')
            # TODO LIVE MATCHES handle live results (not only live, but any not decision result) The event might have
            # finished but the result in process might not be the final one

        return related_bet_events

    def settle(self, result='auto', decision_types=Result.decision_types, strongest_type=Result.ft_result):
        """ If no result is given, it tries to get the decision result of the event and settle it with it.
        You can run this function with any result. If the result is not of the decision type
        then no settlement will take place.
        :return related_bet_events: list (not queryset) of bet events that have passed their settlement process
        """
        if result == 'auto':
            # get the decision type result and settle the event using that result
            result = self.get_decision_result(decision_types=decision_types, strongest_type=strongest_type)
            if not result:
                logger.debug('event %s not settled since it has no decision_result_type', self)
                return []

        related_bet_events = self.settle_market_offers_and_bevs(result, decision_types)
        return related_bet_events

    def settle_tree(self, result='auto', decision_types=Result.decision_types, strongest_type=Result.ft_result, update_cache=True):
        """ The event's status will be recalculated. Market results will also be recalculated.
        But calculated (closed) bet_events, bets and total_bets will be not recalculated.
        If there is no result of the decision type, then empty lists are returned """
        logger.info("settling event tree for %s ...", self)
        self.update_status()
        related_bet_events = self.settle(result=result, decision_types=decision_types, strongest_type=strongest_type)
        cbs, wbs, obs, ctbs, otbs, changed_tbs = BetEvent.settle_bets_and_tbets(related_bet_events, update_cache)
        return related_bet_events, cbs, wbs, obs, ctbs, otbs, changed_tbs

    def get_sids(self, source_name):
        # an event can have more than one sids from the same source either due to an error or due to a change
        sids = []
        try:
            event_infos = self.event_infos.filter(source__name=source_name)
            numn_infos = event_infos.count()
            if numn_infos > 1:
                logger.warning('Event %s has %s infos from source %s', self, numn_infos, source_name)
            for event_info in event_infos:
                sids.append(event_info.sid)
        except Exception as e:
            logger.error('%s', e)
        return sids

    def get_brothers(self, source_name):
        """ it returns all the other events that have the same sid and source with the processed one """
        sids = self.get_sids(source_name)
        if not sids:
            return
        brothers = Event.objects.filter(event_infos__source__name=source_name).filter(
            event_infos__sid__in=sids).exclude(id=self.id).distinct()
        return brothers

    def add_result(self, result):
        """ adds the given result to the event. If given result is final, it will become the event's
        final result. (If the event has already a final result and the given result is also final,
        then the previous final results are marked as not finals (new not final results are created since
        result objects are used by many events. You don't update a result. You create a new one)) """
        if not result:
            return
        if result in self.results.all():
            return
        if result.final:
            current_final_results = self.results.filter(final=True)
            if current_final_results:
                # logger.info("Event %s has a new final result %s", self, result)
                logger.info("A new final result %s will be added to event %s which now has the following final "
                            "results: %s", result, self, current_final_results)
                for fin_res in current_final_results:
                    self.results.remove(fin_res)
                    new_res, created = Result.objects.get_or_create(
                        home_goals=fin_res.home_goals, away_goals=fin_res.away_goals, minute=fin_res.minute, type=fin_res.type, final=False)
                    self.results.add(new_res)
        self.results.add(result)

    def settle_brothers(self, source, result_type=Result.postponed):
        """ It checks if the event has brothers (events with the same sid from the same source) that represent
        the same match but with a different date due to the fact that it was postponed. If there are brothers
        this means that this event is the new valid event that represents the valid date and the previous ones
        must be settled as postponed or similar

        brothers: They are different events (different date) that have the same sid for a given source
        """
        brothers = self.get_brothers(source)
        if not brothers:
            return
        logger.info('event %s has %s brothers', self, len(brothers))
        result, created = Result.objects.get_or_create(home_goals=0, away_goals=0, minute=0, type=result_type, final=True)
        # result = Result.objects.filter(type=result_type, final=True).first()  # it might not exist
        for brother in brothers:
            logger.info('settling brother: %s', brother)
            if brother.results.filter(type__in=Result.void_types):
                # Add result and settle brother only if the brother has no void result already.
                # It is very possible that the brother has already been settled with a void result
                # when a call for its result was made and a Void result was returned.
                continue
            brother.add_result(result)
            bevs, cbs, wbs, obs, ctbs, otbs, changed_tbs = brother.settle_tree()

    def update_status(self):
        status = self.get_status()
        if self.status == status:
            return
        self.status = status
        self.save()

    def get_status(self):
        """ The status of an event is decided by the results and date of the event """
        results = self.results.all()
        if not results:
            # logger.debug("no results")
            if timezone.now() > self.date:
                # logger.debug("now > event date, so status becomes in_play")
                # todo status undetermined, have in mind that if by mistake no decision result is added to these
                # events they will remain as in_play. I can add an "undetermined" status. Add also a function
                # that checks all the in_play matched to determine which ones are actually inplay and which
                # ones are undetermined. Then handle undetermined
                return Event.in_play
            return Event.not_started
        if not self.has_final_result():
            logger.debug("event %s has no final result", self)
            # todo status undetermined, if by mistake no final result is taken from source they remain as inplay
            return Event.in_play
        else:
            try:
                final_res = self.results.get(final=True)
            except Result.MultipleObjectsReturned:
                logger.error("event %s has more than one final results!", self)
                final_res = self.results.filter(final=True).latest("created_at")
            return final_res.map_to_status()

    def has_final_result(self):
        try:
            self.results.get(final=True)
        except Result.DoesNotExist:
            return False
        except Result.MultipleObjectsReturned:
            logger.error("event %s has more than one final results", self)
        return True

    def get_decision_result(self, decision_types=Result.decision_types, strongest_type=Result.ft_result):
        """ If the event has more than one decision type results the strongest one will be returned """
        results = self.results.filter(type__in=decision_types)
        if not results:
            return
        logger.debug("decision results (of event %s): %s", self, results)
        if results.count() == 1:
            return results.first()
        else:
            # event has more than one decision type results.
            # For example ft and abandoned in extra time or Interrupted and continued
            try:
                result = results.get(type=strongest_type)
                return result
                # if strongest type deosn't exist, then no result must be returned since the returned result
                # is used for event settlement
            except Result.DoesNotExist as e:
                logger.debug("%s, event %s has no result of %s type", e, self, strongest_type)
                return
            except Result.MultipleObjectsReturned as e:
                logger.error("%s, event %s has more than one results of %s type", e, self, strongest_type)
                return

    def get_tbets(self):
        bet_events = BetEvent.objects.filter(event=self)
        if not bet_events:
            return []
        bets = Bet.objects.filter(bet_events__in=bet_events).distinct()
        if not bets:
            logger.error("bet_events %s are not connected with any bets", bet_events)
            return []
        tbets = TotalBet.objects.filter(bets__in=bets).distinct()
        return tbets

    def describe(self, describe_brothers=True):
        logger.info("describing event %s...", self)
        logger.info('home team: %s %s', self.home_team.generic_name, [team_info for team_info in self.home_team.team_infos.all()])
        logger.info('away team: %s %s', self.away_team.generic_name,
                    [team_info for team_info in self.away_team.team_infos.all()])
        logger.info(" > id: %s %s cr: %s, upd: %s", self.id, [(info.source.name, info.sid) for info in self.event_infos.all()],
                    self.created_at, self.updated_at)

        results = self.results.all()
        logger.info("it has %s results", len(results))
        for result in results:
            logger.info(" > %s id: %s (%s-%s %s) cr: %s, upd: %s", result, result.id, result.home_goals,
                        result.away_goals, result.minute, result.created_at, result.updated_at)

        bet_events = self.bet_events.all().distinct()
        logger.info("it has %s bet_events", len(bet_events))
        for bet_event in bet_events:
            logger.info(" > %s", bet_event)

        if not describe_brothers:
            return

        brothers = []
        for source in Source.objects.all():
            source_brothers = self.get_brothers(source.name)
            if not source_brothers:
                continue
            logger.info(" > it has %s brothers from source %s:", source_brothers.count(), source.name)
            for brother in source_brothers:
                logger.info("describing brother...")
                brother.describe(describe_brothers=False)
            brothers.extend(source_brothers)
        logger.info("it has %s brothers from all sources", len(brothers))

    # def has_been_settled(self, decision_types=Result.decision_types, strongest_type=Result.ft_result):
    #     """ Trying to decide if it is settled only from the event's fields. It doesn't check the
    #     status of it's bet_events. This is done to for performance reasons but will not correctly
    #     answer in case of errors (event field's conclude in different conclusion if we add the bet_events check)
    #
    #     Notice: When results are created they are added to the respective events first and after the addition
    #      for all events has been completed the events are being settled. So during the time that an event waits
    #      to be settled, it has decision type result but an "open" status.
    #     """
    #     results = self.results.filter(type__in=decision_types)
    #     status = self.status
    #     bet_events = self.bet_events.all()  # check if they have been settled
    #     if status not in Event.open_event_statuses and results:
    #         return True
    #     elif status not in Event.open_event_statuses and not results:
    #         logger.error("event %s has a 'settled' status but it has no result of these decision types: %s", self, decision_types)
    #     return False

    @classmethod
    def with_many_strongest_type_results(cls, decision_types=Result.decision_types, strongest_type=Result.ft_result):
        events = cls.objects.exclude(results__isnull=True)
        filtered_events = []
        for event in events:
            results = event.results.filter(type__in=decision_types)
            if not results:
                continue
            try:
                results.get(type=strongest_type)
            except Result.DoesNotExist as e:
                # logger.debug("%s, event %s has no result of %s type", e, event, strongest_type)
                continue
            except Result.MultipleObjectsReturned as e:
                filtered_events.append(event)
                # logger.error("%s, event %s has more than one results of %s type, [%s]",
                #              e, event, strongest_type, event.results.all())
        return filtered_events

    @classmethod
    def with_many_infos(cls, source_name):
        """ returns the entities that have more than one info entries from the given source """
        events = cls.objects.filter(event_infos__source__name=source_name).annotate(
            num_event_infos=Count('event_infos')).filter(num_event_infos__gt=1)
        logger.info("number of events with more than one infos from the same source: %s", events.count())
        for event in events:
            logger.info("%s %s", event, [event_info.sid for event_info in
                                         event.event_infos.filter(source__name=source_name)])
        return events

    @classmethod
    def settle_trees(cls, events, update_cache=True):
        logger.info("settling %s event trees...", len(events))
        c_bevs, c_cbs, c_wbs, c_obs, c_ctbs, c_otbs, c_changed_tbs = [], [], [], [], [], [], []
        if not events:
            return c_bevs, c_cbs, c_wbs, c_obs, c_ctbs, c_otbs, c_changed_tbs
        for event in events:
            # if event.status not in Event.open_event_statuses:
            #     # todo Open check I'm not sure if this check causes any problems so I don't activate it
            #     continue
            # update cache is False here so that no individual user's cache update will be made
            bevs, cbs, wbs, obs, ctbs, otbs, changed_tbs = event.settle_tree(update_cache=False)
            c_bevs.extend(bevs)
            c_cbs.extend(cbs)
            c_wbs.extend(wbs)
            c_obs.extend(obs)
            c_ctbs.extend(ctbs)
            c_otbs.extend(otbs)
            c_changed_tbs.extend(changed_tbs)
        if update_cache:
            # todo send bulk_tbs_settlement signal with update_cache as an argument and do these actions there
            # have in mind that settle_events is usually already executed as a task.
            # So can a task put another task in a queue?
            BetEvent.batch_upd_users_cache(c_bevs)
        return c_bevs, c_cbs, c_wbs, c_obs, c_ctbs, c_otbs, c_changed_tbs

    @classmethod
    def active_event_from_sid(cls, event_sid, source):
        # todo high get the active event for this sid (it is not certain that it will be the latest)
        # probably the uses of the get_latest function really want the get_active
        return

    @classmethod
    def latest_event_from_sid(cls, event_sid, source):
        """ It returns the latest event that corresponds to the given source and sid. If there
         are also other events with the same sid and source that are postponed they are not returned """
        try:
            event_info = EventInfo.objects.filter(sid=event_sid, source=source).latest()
            event = event_info.event
        except Exception as e:
            event = None
            logger.error("%s There is no event infos for source %s and sid %s", e, source, event_sid)
        return event

    @classmethod
    def events_from_sid(cls, event_sid, source, statuses=None):
        """ It returns all the events for the given sid and source. Events that are postponed etc. will
        also be returned """
        event_infos = EventInfo.objects.filter(sid=event_sid, source=source)
        if not event_infos:
            # logger.error("There is no event infos for source {} and sid {}".format(source, event_sid))
            return []
        events = []
        for event_info in event_infos:
            event = event_info.event
            if statuses:
                if event.status not in statuses:
                    continue
            events.append(event)
        return events

    @classmethod
    def filter_events(cls, events=None, competition_gname=None, competition_id=None, home_team_gname=None,
                      away_team_gname=None, season=None, start_date=None, end_date=None, status=None,
                      country_name=None, competition_seasons=None):
        """
        :param events: queryset
        :param competition_gname: string, optional
        :param home_team_gname: string, optional
        :param away_team_gname: string, optional
        :param season: string, optional
        :param competition_seasons: list or queryset
        :return: list, the filtered event instances
        """
        if not events:
            events = cls.objects.all()
        if competition_seasons:
            events = events.filter(competition_season__in=competition_seasons)
        if country_name:
            events = events.filter(competition_season__competition__country__name=country_name)
        if competition_gname:
            events = events.filter(competition_season__competition__generic_name=competition_gname)
        if competition_id:
            events = events.filter(competition_season__competition__id=competition_id)
        if season:
            events = events.filter(competition_season__season__name=season)
        if home_team_gname:
            events = events.filter(home_team__generic_name=home_team_gname)
        if away_team_gname:
            events = events.filter(away_team__generic_name=away_team_gname)
        if status:
            events = events.filter(status=status)
        if start_date and end_date:
            # Notice that a datetime with time info is used, the range will include also the end_date
            # events = events.filter(date__range=(start_date, end_date))
            events = events.filter(date__gte=start_date, date__lte=end_date)
        return events

    @classmethod
    def order_for_result_call(cls, events, strongest_type=Result.ft_result):
        """ Filters the given events queryset so that it contains only the events for which a call to get
        their result needs to be made. It sorts the events too so that the most betted events are listed first.
        The filtered events are the events without a final result and the events
        that have a final result that is a no void result but they don't have a full time result. """
        # todo make the querysets pandas dataframes and sort them the way you want

        if not events:
            return None, None

        void_results = Result.void_types

        no_final_events = events.exclude(results__final=True)
        final_events = events.filter(results__final=True)

        final_no_void_events = final_events.exclude(results__type__in=void_results)
        final_no_ft_events = final_no_void_events.exclude(results__type=strongest_type)
        # events that have a final result that is not of void result (for example it is AET result),
        # but don't have an ft_result (due to source's error)

        betted_no_final_events = no_final_events.exclude(bet_events__isnull=True).annotate(
            num_bet_events=Count('bet_events')).order_by('-num_bet_events')
        no_betted_no_final_events = no_final_events.filter(bet_events__isnull=True)

        betted_final_no_ft_events = final_no_ft_events.exclude(bet_events__isnull=True).annotate(
            num_bet_events=Count('bet_events')).order_by('-num_bet_events')
        no_betted_final_no_ft_events = final_no_ft_events.filter(bet_events__isnull=True)

        betted_no_final_ids = gutils.utils.ids(betted_no_final_events)
        betted_final_no_ft_ids = gutils.utils.ids(betted_final_no_ft_events)
        no_betted_no_final_ids = gutils.utils.ids(no_betted_no_final_events)
        no_betted_final_no_ft_ids = gutils.utils.ids(no_betted_final_no_ft_events)

        to_call_event_ids_sorted = betted_no_final_ids + betted_final_no_ft_ids + no_betted_no_final_ids + no_betted_final_no_ft_ids
        return to_call_event_ids_sorted, [betted_no_final_ids, betted_final_no_ft_ids,
                                          no_betted_no_final_ids, no_betted_final_no_ft_ids]


class EventInfo(models.Model):
    source = models.ForeignKey(Source, related_name='source_eventinfos_set')
    sid = models.PositiveIntegerField()
    # If the connected event is deleted, the event_info will be deleted also (default until django 1.9)
    event = models.ForeignKey(Event, related_name='event_infos', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __repr__(self):
        return '{}: {} {} {}'.format(self.source, self.event.home_team, self.event.away_team, self.sid)

    def __unicode__(self):
        return '{}: {} {} - {} {} {}'.format(self.source, self.sid, self.event.home_team, self.event.away_team, self.event.competition_season, self.event.status)

    class Meta:
        unique_together = ("source", "sid", "event")
        get_latest_by = 'created_at'


# TODO low create unique results for each submnarket? over25, over15 etc? No for now
class MarketResult(models.Model):
    # IMPORTANT: The choices must have "no white spaces" in their names since the html div has classes separated with
    # white spaces and we collect the 3rd class with javascript to extract the choice text and send it to the server
    open = 'Open'
    void = 'Void'
    # TODO NOW keep only home, instead of home_winner_choice
    home_winner_choice = '1'
    draw_winner_choice = 'X'
    away_winner_choice = '2'
    home = '1'
    draw = 'X'
    away = '2'
    home_draw = '1X'
    draw_away = 'X2'
    away_home = '12'
    over = 'Over'
    under = 'Under'

    market_choices = (
        (open, 'Open'),
        (void, 'Void'),
        (home_winner_choice, '1'),
        (draw_winner_choice, 'X'),
        (away_winner_choice, '2'),
        (home, '1'),
        (draw, 'X'),
        (away, '2'),
        (over, 'Over'),
        (under, 'Under'),
        (home_draw, '1X'),
        (draw_away, 'X2'),
        (away_home, '12'),
    )
    result = models.CharField(max_length=15, choices=market_choices, null=True, default=open, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{0}'.format(self.result)


class MarketOdd(models.Model):

    class Meta:
        abstract = True

    def get_odd_value(self, choice):
        odd = None
        try:
            if choice == MarketResult.home:
                odd = self.home
            elif choice == MarketResult.draw:
                odd = self.draw
            elif choice == MarketResult.away:
                odd = self.away
            elif choice == MarketResult.home_draw:
                odd = self.home_draw
            elif choice == MarketResult.draw_away:
                odd = self.draw_away
            elif choice == MarketResult.away_home:
                odd = self.away_home
            elif choice == MarketResult.over:
                odd = self.over
            elif choice == MarketResult.under:
                odd = self.under
            else:
                logger.error("The choice '%s' is not allowed", choice)
        except Exception as e:
            logger.error("%s, choice: '%s' is not valid for marketOdd: %s", e, choice, self)
            return
        return odd


# ------------- WINNER -------------
class WinnerOdd(MarketOdd):
    # todo replace with rangefloat fields django 1.9
    home = models.FloatField(validators=[MinValueValidator(1)])
    draw = models.FloatField(validators=[MinValueValidator(1)])
    away = models.FloatField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "Home: {} Draw: {} Away: {}".format(self.home, self.draw, self.away)

    class Meta:
        unique_together = ('home', 'draw', 'away')


class WinnerOffer(models.Model):
    # Notice that the reverse relation of a OneToOne field returns an object not a query set.
    # instead of event.winneroffer_set.all() you have event.winneroffer or any related_name
    event = models.OneToOneField(Event)
    # event = models.ForeignKey(Event, unique=True, related_name='event_winneroffers_set')
    market_result = models.ForeignKey(MarketResult, related_name='winner_offers')
    odds = models.ManyToManyField(WinnerOdd, through='WinnerOfferOdd')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "Winner Offer for: {}-{} [{}], market result: {}, num odds: {}".format(
            self.event.home_team,
            self.event.away_team,
            self.event.id,
            self.market_result,
            self.odds.all().count(),
        )

    # class Meta:
    #     unique_together = ('event', 'market_result')


class WinnerOfferOdd(models.Model):
    odd = models.ForeignKey(WinnerOdd, related_name='offer_odds')
    offer = models.ForeignKey(WinnerOffer, related_name='offer_odds')
    bookmaker = models.ForeignKey(Bookmaker, related_name='winner_offer_odds')
    source = models.ForeignKey(Source, related_name='winner_offer_odds')
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{} {} [{}] {} {}'.format(
            self.offer.event.home_team,
            self.offer.event.away_team,
            self.bookmaker,
            self.odd,
            self.timestamp,
        )

    class Meta:
        unique_together = ('odd', 'offer', 'bookmaker', 'source', 'timestamp')
        get_latest_by = 'timestamp'
# ------------- WINNER END -------------


# ------------- DOUBLE CHANCE -------------
class DoubleChanceOdd(MarketOdd):
    home_draw = models.FloatField(validators=[MinValueValidator(1)])
    draw_away = models.FloatField(validators=[MinValueValidator(1)])
    away_home = models.FloatField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "1X: {} X2: {} 12: {}".format(self.home_draw, self.draw_away, self.away_home)

    class Meta:
        unique_together = ('home_draw', 'draw_away', 'away_home')


class DoubleChanceOffer(models.Model):
    event = models.OneToOneField(Event)
    market_result = models.ForeignKey(MarketResult, related_name='double_chance_offers')
    odds = models.ManyToManyField(DoubleChanceOdd, through='DoubleChanceOfferOdd')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "DoubleChance Offer for {0}-{1}, result {2} with {3} odds".format(
            self.event.home_team,
            self.event.away_team,
            self.market_result,
            self.odds.all().count(),
        )

    # class Meta:
    #     unique_together = ('event', 'market_result')


class DoubleChanceOfferOdd(models.Model):
    odd = models.ForeignKey(DoubleChanceOdd, related_name='offer_odds')
    offer = models.ForeignKey(DoubleChanceOffer, related_name='offer_odds')
    bookmaker = models.ForeignKey(Bookmaker, related_name='dc_offer_odds')
    source = models.ForeignKey(Source, related_name='dc_offer_odds')
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{} {} [{}] {} {}'.format(
            self.offer.event.home_team,
            self.offer.event.away_team,
            self.bookmaker.name,
            self.odd,
            self.timestamp,
        )

    class Meta:
        unique_together = ('odd', 'offer', 'bookmaker', 'source', 'timestamp')
        get_latest_by = 'timestamp'
# ------------- DOUBLE CHANCE END -------------


# ------------- OVER UNDER -------------
class OverUnderOdd(MarketOdd):
    over = models.FloatField(validators=[MinValueValidator(1)])
    under = models.FloatField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "over: {}  under: {}".format(self.over, self.under)

    class Meta:
        unique_together = ('over', 'under')


class OverUnderOffer(models.Model):
    event = models.ForeignKey(Event, related_name='over_under_offers')
    market_result = models.ForeignKey(MarketResult, related_name='over_under_offers')
    threshold = models.FloatField()
    odds = models.ManyToManyField(OverUnderOdd, through='OverUnderOfferOdd')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "OverUnder {0} Offer for {1}-{2}, result {3}, has {4} odds".format(
            self.threshold,
            self.event.home_team,
            self.event.away_team,
            self.market_result,
            self.odds.all().count(),
        )

    class Meta:
        unique_together = ('event', 'threshold')


class OverUnderOfferOdd(models.Model):
    odd = models.ForeignKey(OverUnderOdd, related_name='offer_odds')
    offer = models.ForeignKey(OverUnderOffer, related_name='offer_odds')
    bookmaker = models.ForeignKey(Bookmaker, related_name='ovun_offer_odds')
    source = models.ForeignKey(Source, related_name='ovun_offer_odds')
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{} {} threshold {} [{}] {} {}'.format(
            self.offer.event.home_team,
            self.offer.event.away_team,
            self.offer.threshold,
            self.bookmaker.name,
            self.odd,
            self.timestamp,
            )

    class Meta:
        unique_together = ('odd', 'offer', 'bookmaker', 'source', 'timestamp')
        get_latest_by = 'timestamp'
# ------------- OVER UNDER END -------------


# ------------- HANDICAP -------------
class HandicapOdd(MarketOdd):
    home = models.FloatField(validators=[MinValueValidator(1)])
    draw = models.FloatField(validators=[MinValueValidator(1)])
    away = models.FloatField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "Home: {} Draw: {} Away: {}".format(self.home, self.draw, self.away)

    class Meta:
        unique_together = ('home', 'draw', 'away')


class HandicapOffer(models.Model):
    event = models.ForeignKey(Event, related_name='handicap_offers')
    market_result = models.ForeignKey(MarketResult, related_name='handicap_offers')
    threshold = models.FloatField()
    odds = models.ManyToManyField(HandicapOdd, through='HandicapOfferOdd')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "Handicap {0} Offer for {1}-{2}, result {3}, has {4} odds".format(
            self.threshold,
            self.event.home_team,
            self.event.away_team,
            self.market_result,
            self.odds.all().count(),
        )

    class Meta:
        unique_together = ('event', 'threshold')


class HandicapOfferOdd(models.Model):
    odd = models.ForeignKey(HandicapOdd, related_name='offer_odds')
    offer = models.ForeignKey(HandicapOffer, related_name='offer_odds')
    bookmaker = models.ForeignKey(Bookmaker, related_name='handicap_offer_odds')
    source = models.ForeignKey(Source, related_name='handicap_offer_odds')
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{} {} handicap: {} [{}] {} , {}'.format(
            self.offer.event.home_team,
            self.offer.event.away_team,
            self.offer.threshold,
            self.bookmaker.name,
            self.odd,
            self.timestamp,
        )

    class Meta:
        unique_together = ('odd', 'offer', 'bookmaker', 'source', 'timestamp')
        get_latest_by = 'timestamp'
# ------------- HANDICAP END -------------


# ------------- ASIAN HANDICAP -------------
class AsianHandicapOdd(MarketOdd):
    home = models.FloatField(validators=[MinValueValidator(1)])
    away = models.FloatField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "Home: {}, Away: {}".format(self.home, self.away)

    class Meta:
        unique_together = ('home', 'away')


class AsianHandicapOffer(models.Model):
    event = models.ForeignKey(Event, related_name='asian_handicap_offers')
    market_result = models.ForeignKey(MarketResult, related_name='asian_handicap_offers')
    threshold_1 = models.FloatField()
    threshold_2 = models.FloatField(blank=True, default=None)
    odds = models.ManyToManyField(AsianHandicapOdd, through='AsianHandicapOfferOdd')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "AsianHandicap {0},{1} Offer for {2}-{3}, result {4}, has {5} odds".format(
            self.threshold_1,
            self.threshold_2,
            self.event.home_team.generic_name,
            self.event.away_team.generic_name,
            self.market_result,
            self.odds.all().count(),
        )

    class Meta:
        unique_together = ('event', 'threshold_1', 'threshold_2')


class AsianHandicapOfferOdd(models.Model):
    odd = models.ForeignKey(AsianHandicapOdd, related_name='offer_odds')
    offer = models.ForeignKey(AsianHandicapOffer, related_name='offer_odds')
    bookmaker = models.ForeignKey(Bookmaker, related_name='as_handicap_offer_odds')
    source = models.ForeignKey(Source, related_name='as_handicap_offer_odds')
    # timestamp is the time the API has updated the odd (this is the time according to which we should order odds)
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # def __unicode__(self):
    #     return '{0}-{1} from {2} Home({3}[{7},{8}]), Away({5}[-{7},-{8}]) {6}'.format(
    #         self.asian_handicap_offer.event.home_team.generic_name,
    #         self.asian_handicap_offer.event.away_team.generic_name,
    #         self.bookmaker.name,
    #         self.asian_handicap_offer.home,
    #         self.asian_handicap_offer.away,
    #         self.timestamp,
    #         self.asian_handicap_offer.threshold_1,
    #         self.asian_handicap_offer.threshold_2,
    #     )

    class Meta:
        unique_together = ('odd', 'offer', 'bookmaker', 'source', 'timestamp')
        get_latest_by = 'timestamp'
# ------------- ASIAN HANDICAP END -------------


class FinalScoreResult(models.Model):
    fsc_home_01 = '1-0'
    fsc_home_02 = '2-0'
    fsc_home_03 = '2-1'
    fsc_home_04 = '3-0'
    fsc_home_05 = '3-1'
    fsc_home_06 = '3-2'
    fsc_home_07 = '4-0'
    fsc_home_08 = '4-1'
    fsc_home_09 = '4-2'
    fsc_home_10 = '4-3'
    fsc_home_11 = '5-0'
    fsc_home_12 = '5-1'
    fsc_home_13 = '5-2'
    fsc_home_14 = '5-3'
    fsc_home_16 = '6-0'
    fsc_home_17 = '6-1'
    fsc_home_18 = '6-2'
    fsc_home_20 = '7-0'
    fsc_home_21 = '7-1'
    fsc_draw_22 = '0-0'
    fsc_draw_23 = '1-1'
    fsc_draw_24 = '2-2'
    fsc_draw_25 = '3-3'
    fsc_away_26 = '0-1'
    fsc_away_27 = '0-2'
    fsc_away_28 = '1-2'
    fsc_away_29 = '0-3'
    fsc_away_30 = '1-3'
    fsc_away_31 = '2-3'
    fsc_away_32 = '0-4'
    fsc_away_33 = '1-4'
    fsc_away_34 = '2-4'
    fsc_away_35 = '3-4'
    final_score_choices = (
        (fsc_home_01, '1-0'),
        (fsc_home_02, '2-0'),
        (fsc_home_03, '2-1'),
        (fsc_home_04, '3-0'),
        (fsc_home_05, '3-1'),
        (fsc_home_06, '3-2'),
        (fsc_home_07, '4-0'),
        (fsc_home_08, '4-1'),
        (fsc_home_09, '4-2'),
        (fsc_home_10, '4-3'),
        (fsc_home_11, '5-0'),
        (fsc_home_12, '5-1'),
        (fsc_home_13, '5-2'),
        (fsc_home_14, '5-3'),
        (fsc_home_16, '6-0'),
        (fsc_home_17, '6-1'),
        (fsc_home_18, '6-2'),
        (fsc_home_20, '7-0'),
        (fsc_home_21, '7-1'),
        (fsc_draw_22, '0-0'),
        (fsc_draw_23, '1-1'),
        (fsc_draw_24, '2-2'),
        (fsc_draw_25, '3-3'),
        (fsc_away_26, '0-1'),
        (fsc_away_27, '0-2'),
        (fsc_away_28, '1-2'),
        (fsc_away_29, '0-3'),
        (fsc_away_30, '1-3'),
        (fsc_away_31, '2-3'),
        (fsc_away_32, '0-4'),
        (fsc_away_33, '1-4'),
        (fsc_away_34, '2-4'),
        (fsc_away_35, '3-4'),
        (None, 'Open'),
    )
    result = models.CharField(max_length=10, choices=final_score_choices, null=True, default=None)

    def __unicode__(self):
        return 'Final Score Result: {0}'.format(self.result)


class Selection(models.Model):
    original_odd = models.FloatField()
    selected_odd = models.FloatField()
    # combined choices of MarketResult choices except from "void" choice since users don't select a void choice
    winner_home = MarketResult.home_winner_choice
    winner_draw = MarketResult.draw_winner_choice
    winner_away = MarketResult.away_winner_choice
    home = '1'
    draw = 'X'
    away = '2'
    home_draw = '1X'
    draw_away = 'X2'
    away_home = '12'
    over = MarketResult.over
    under = MarketResult.under

    market_results_combined_choices = (
        (winner_home, '1'),
        (winner_draw, 'X'),
        (winner_away, '2'),
        (over, 'Over'),
        (under, 'Under'),
        (home, '1'),
        (draw, 'X'),
        (away, '2'),
        (over, 'Over'),
        (under, 'Under'),
        (home_draw, '1X'),
        (draw_away, 'X2'),
        (away_home, '12'),
    )
    choice = models.CharField(max_length=15, choices=market_results_combined_choices)

    won = 'Won'
    lost = 'Lost'
    open = 'Open'
    void = MarketResult.void
    status_choices = (
        (won, 'Won'),
        (lost, 'Lost'),
        (open, 'Open'),
        (void, void),
    )
    status = models.CharField(max_length=5, choices=status_choices, default=open)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('original_odd', 'selected_odd', 'choice', 'status')

    def __unicode__(self):
        return '{0} on {1}({2}) - {3}'.format(self.choice, self.selected_odd, self.original_odd, self.status)

    def save(self, *args, **kwargs):
        # Explicitly call the full_clean method to validate the model (mainly the choices field)
        # This is automatically called when a model instance is created through a ModelForm whcih is not
        # the case here. Selection is created within a transaction so if there is a validation error
        # the transaction will be rolled back
        self.full_clean()
        super(Selection, self).save(*args, **kwargs)


class BetEvent(models.Model):
    event = models.ForeignKey(Event, related_name='bet_events')
    market_type = models.ForeignKey(MarketType, related_name='markettype_betevent_set')
    selection = models.ForeignKey(Selection, related_name='selection_betevent_set')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '[id:{0}] event: {1}, market_type: {2}, selection: {3}'.format(
            self.id,
            self.event,
            self.market_type,
            self.selection
        )

    def get_raw_bet_event(self):
        return

    def get_popularity(self):
        return

    def settle(self, market_result):
        selection = self.selection
        bet_event_choice = selection.choice
        bet_event_status = selection.status
        # print("--- bet event is: {0}".format(bet_event))
        # print("--- bet_event of the specific market_offer has: {0} choice and {1} status".format(bet_event_choice,
        # bet_event_status))
        # print("--- The specific market result is: {0}".format(market_result.result))
        # TODO OPEN CHECK low make the open check only one time in order to be easy to change it
        if bet_event_status == Selection.open:
            # We do the "in" check instead of "if bet_event_choice == market_result.result" because there is one
            # market that the result is not the same with the bet_event choice. The double_chance market in which
            # the bet_event choice can be '1X' but the result will be '1'. In all the other cases the bet_event
            # choices and the result choices are common. So an example will be: if 'over' in 'over':
            if market_result.result in bet_event_choice:
                won_selection, won_created = Selection.objects.get_or_create(
                    original_odd=selection.original_odd, selected_odd=selection.selected_odd, choice=selection.choice, status=Selection.won)
                new_selection = won_selection
            elif market_result.result == MarketResult.void:
                # Notice that we don't assign odds=1 in the void selection on purpose. In order to facilitate the
                # removing process of a void result.
                void_selection, void_created = Selection.objects.get_or_create(
                    original_odd=selection.original_odd, selected_odd=selection.selected_odd, choice=selection.choice, status=Selection.void)
                new_selection = void_selection
            else:
                lost_selection, lost_created = Selection.objects.get_or_create(
                    original_odd=selection.original_odd, selected_odd=selection.selected_odd, choice=selection.choice, status=Selection.lost)
                new_selection = lost_selection
            self.selection = new_selection
            self.save()
            logger.debug("Bet event %s was updated with selection %s", self, new_selection)
        else:
            logger.debug("Bet event %s is already settled", self)

    @classmethod
    def get_total_bets(cls, bet_events):
        if not bet_events:
            return []
        bets = Bet.objects.filter(bet_events__in=bet_events)
        tbs = TotalBet.objects.filter(bets__in=bets).distinct()
        return tbs

    @classmethod
    @job("default", result_ttl=0, timeout=60*60*3)
    def batch_upd_users_cache(cls, bevs):
        # have in mind that even if the bevs have not changed, the cache update will be made
        from bet_statistics.signals import update_user_cache
        tbets = cls.get_total_bets(bevs)
        user_ids = TotalBet.get_distinct_user_ids(tbets)
        logger.info("updating cache for users: %s ...", user_ids)
        for user_id in user_ids:
            update_user_cache(user_id)

    @classmethod
    def settle_bets_and_tbets(cls, bet_events, update_cache=True):
        """ Their related bets and total_bets are settled """
        logger.debug('%s bet events have passed the settlement process. Their bets are settled...', len(bet_events))
        if not bet_events:
            return [], [], [], [], [], []
        related_bets = Bet.objects.filter(bet_events__in=bet_events).distinct()
        lost_bets, won_bets, open_bets = Bet.settle_bets(related_bets)
        closed_bets = lost_bets + won_bets
        if not closed_bets:
            open_total_bets = TotalBet.objects.filter(bets__in=open_bets).distinct()
            return lost_bets, won_bets, open_bets, [], open_total_bets, []
        related_total_bets = TotalBet.objects.filter(bets__in=closed_bets).distinct()
        logger.debug('%s bets have been settled. The %s related total_bets are settled...',
                     len(closed_bets), related_total_bets.count())
        closed_total_bets, open_total_bets, changed_total_bets = TotalBet.settle_total_bets(related_total_bets, update_cache)
        return lost_bets, won_bets, open_bets, closed_total_bets, open_total_bets, changed_total_bets


# Have in mind that a Bet can belong to only one TotalBet and this is not enforced by the current db scheme. I enforce
# it programaticaly when the Bets are created. (By using create instead of get_or_create every time a BET is created in
# the create_bet_tree function in bet_slip app views. More details in the respective comments there)
class Bet(models.Model):
    amount = models.FloatField()
    odd = models.FloatField(null=True, default=None)
    bet_return = models.FloatField(null=True, default=None)
    won = 'Won'
    lost = 'Lost'
    open = 'Open'
    bet_status_choices = (
        (won, 'Won'),
        (lost, 'Lost'),
        (open, 'Open'),
    )
    status = models.CharField(max_length=5, choices=bet_status_choices, default=open)
    # have in mind that the bet_events field name is used as string by get_exact_m2m_match(). So don't change its name
    bet_events = models.ManyToManyField(BetEvent)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __repr__(self):
        return 'Bet {} - {} Euros on {}, odd = {}, status= {}, return= {} '.format(
            str(self.id),
            self.amount,
            [(bet_event.event.home_team.generic_name, bet_event.event.away_team.generic_name) for bet_event in self.bet_events.all()],
            self.odd,
            self.status,
            self.bet_return,
        )

    def __unicode__(self):
        return "[{}] {} amount:{} return:{} {}".format(self.id, self.odd, self.amount, self.bet_return, self.status)

    def update_odd(self):
        odd = 1.
        bet_events = self.bet_events.all()
        if bet_events:
            for bet_event in bet_events:
                bet_event_odd = bet_event.selection.selected_odd
                if bet_event.selection.status == Selection.void:
                    logger.debug('changing the odd of the void bet event %s', bet_event)
                    bet_event_odd = 1.
                if bet_event_odd:
                    odd *= bet_event_odd
                else:
                    logger.error("Bet_odd isn't calculated. bet_event %s has no selected odd", bet_event)
                    # If there is a bet_event with no odd, then the bet_odd isn't calculated
                    return self.odd
            self.odd = odd
            self.save()
        else:
            logger.error("Bet_odd isn't calculated. Bet %s has no bet_events associated with it", self)
        return self.odd

    def calculate_bet_return(self, bet_status=None):
        if not bet_status:
            bet_status = self.status

        bet_return = self.bet_return
        if bet_status == Bet.lost:
            bet_return = 0.
            # self.bet_return = bet_return
        elif bet_status == Bet.won:
            amount = self.amount
            odd = self.odd
            if amount and odd:
                bet_return = amount * odd
                # self.bet_return = bet_return
            else:
                logger.error("Return of bet {0} can't be calculated. Its bet_amount or its bet_odd are None".format(self))
        else:
            logger.error("Return of bet {0} can't be calculated. Bet is still Open".format(self))
        return bet_return

    def settle(self):
        # TODO OPEN CHECK have in mind that if you don't make this check the same bet must be processed many times
        if self.status == Bet.open:
            lost_related_bet_events = self.bet_events.filter(selection__status=Selection.lost)
            if lost_related_bet_events:
                self.status = Bet.lost
                bet_return = self.calculate_bet_return(bet_status=Bet.lost)
                self.bet_return = bet_return
                self.save()
                logger.debug("bet %s was updated to status 'lost'", self)
            else:
                open_related_bet_events = self.bet_events.filter(selection__status=Selection.open)
                # Just have in mind that since choices is not enforced in the choices field, the fact that the
                # bet_event status is not "lost" nor "open" doesn't guarantee 100% that it is "won" or "void"..
                if not open_related_bet_events:
                    # all bet_events of this bet are won or void. A bet with void bet_events is considered "won"
                    # TODO low add "Void" status for bets for the case in which all of its bet_events are void. The same also for the total bets
                    self.status = Bet.won
                    void_related_bet_events = self.bet_events.filter(selection__status=Selection.void)
                    if void_related_bet_events:
                        logger.debug("bet %s has void bet events", self)
                        # If there are void bet_events then we must recalculate the bet's odd since some of its
                        # bet events are now void and their odd is 1. The bet odd was calculated with the
                        # "initial" selected odds of their bet_events
                        bet_odd = self.update_odd()
                    bet_return = self.calculate_bet_return(bet_status=Bet.won)
                    self.bet_return = bet_return
                    self.save()
                    logger.debug("bet %s was updated to status 'won'", self)
                else:
                    logger.debug("bet %s remains open", self)
        else:
            logger.debug('bet %s is already closed', self)

    @classmethod
    def settle_bets(cls, bets):
        # Notice that a bet will be characterized as lost even if it has open bet_events if it has at least one lost
        # bet_event. In this case the decision date of the total bet will be prior to the last event of the total bet.
        # The remaining open bet_events will also be calculated when their date comes.
        if not bets:
            logger.debug("there are no bets to settle")
            return [], [], []
        logger.debug("settling %s bets...", len(bets))
        lost_bets = []
        won_bets = []
        open_bets = []
        for bet in bets:
            bet.settle()
            if bet.status == cls.open:
                open_bets.append(bet)
            elif bet.status == cls.lost:
                lost_bets.append(bet)
            elif bet.status == cls.won:
                won_bets.append(bet)
            else:
                logger.error('Unknown bet status %s for bet %s', bet.status, bet)
        return lost_bets, won_bets, open_bets

    @classmethod
    def resettle_bets(cls, bets):
        """
        Currently a bet must be open to be processed. We update also the other bet fields to their initial values.
        call to update_odd() is only necessary for the case in which a void bet_event was turned to open (a void result was
        removed) and consequently this bet_event no more has odd 1. This is done in the remove result function. I could add
        it also here and remove it from there (but it would be called for all the bets)
        """
        cls.objects.filter(pk__in=bets).update(status=cls.open, bet_return=None)
        lost_bets, won_bets, open_bets = cls.settle_bets(bets)
        return lost_bets, won_bets, open_bets


class TotalBet(models.Model):
    name = models.CharField(max_length=30, default='default')
    # to give the possibility to anonymous users to save bets you need to make the user field nullable
    user = models.ForeignKey(User, related_name='total_bets')
    bookmaker = models.ForeignKey(Bookmaker, related_name='total_bets')
    date = models.DateTimeField('Bet date')
    decision_date = models.DateTimeField(null=True, default=None)
    # aggregated fields: amount, odd, return, status. They could be calculated with class methods instead of fields.
    # I could also have a new model that is a copy of TotalBets but with aggregated values. It will be updated regularly
    amount = models.FloatField()
    odd = models.FloatField(null=True, default=None)
    total_return = models.FloatField(null=True, default=None)
    won = 'Won'
    lost = 'Lost'
    open = 'Open'
    bet_status_choices = (
        (won, 'Won'),
        (lost, 'Lost'),
        (open, 'Open'),
    )
    status = models.CharField(max_length=5, choices=bet_status_choices, default=open)
    # type = models.CharField(max_length=15, choices=type_choices, default=def_choice) Ex. Goliath, etc like in bet365
    bets = models.ManyToManyField(Bet)
    bet_tag = models.ForeignKey(bet_tagging.models.BetTag, related_name='total_bets')
    bet_tag_balance_snapshot = models.FloatField()  # the tag balance just before the current total bet was submitted
    description = models.CharField(max_length=5000, null=True, default=None)
    url = models.URLField(null=True, default=None)
    # private tbs appear in user's history stats but not in his open bets nor are send as tip
    public = models.BooleanField(default=True)
    is_past = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    allow_comments = True  # used by django_comments_xtd

    def __unicode__(self):
        # Have in mind the decorator: python_2_unicode_compatible()
        # A decorator that defines __unicode__ and __str__ methods under Python 2. Under Python 3 it does nothing.
        # To support Python 2 and 3 with a single code base, define a __str__ method returning text and apply this
        # decorator to the class.
        return '[{}] TotalBet {} [{}] ({}) {}: {} sub_bets, {} MoneyUnits on {}, odd = {}, status= {}, return= {} '.format(
            self.user,
            str(self.id),
            self.bookmaker.name,
            self.name,
            self.date.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
            self.bets.count(),
            self.amount,
            self.bets.all(),
            self.odd,
            self.status,
            self.total_return,
        )

    def get_absolute_url(self):
        return reverse('bet_statistics:total_bet_detail', kwargs={'pk': self.id})

    @classmethod
    def exclude_private(cls, tbs, request_user):
        """ the private tbs of the request_user are not excluded """
        allowed_tbs = tbs.exclude(bet_tag__type=bet_tagging.models.BetTag.private)
        request_user_private_tbs = tbs.filter(bet_tag__type=bet_tagging.models.BetTag.private, user=request_user)
        if request_user_private_tbs:
            allowed_tbs = allowed_tbs | request_user_private_tbs
        return allowed_tbs

    @classmethod
    def exclude_premium(cls, tbs, request_user):
        """ the premium tbs of the request_user are not excluded"""
        # open_tbs = tbs.filter(status=cls.open)
        # if not open_tbs:
        #     return tbs
        premium_tbs = tbs.filter(bet_tag__type=bet_tagging.models.BetTag.premium).exclude(user=request_user)
        if not premium_tbs:
            return tbs
        premium_bet_groups = bet_tagging.models.BetTag.objects.filter(total_bets__in=premium_tbs).distinct()
        hidden_bet_groups = []
        for bet_group in premium_bet_groups:
            active_subscribers = bet_group.get_active_subscribers()
            if request_user not in active_subscribers:
                hidden_bet_groups.append(bet_group)
        allowed_tbs = tbs.exclude(bet_tag__in=hidden_bet_groups)
        return allowed_tbs

    @classmethod
    def exclude_permissioned(cls, tbs, request_user):
        """
        Removes from the given queryset (if necessary) the total bets, that the given request_user
        has no see permission for. i.e the total bets that belong to private or premium bet groups
        """
        tbs = cls.exclude_private(tbs, request_user)
        tbs = cls.exclude_premium(tbs, request_user)
        return tbs

    @classmethod
    def filter_private(cls, tbs, request_user, open_tbs=None):
        if not open_tbs:
            open_tbs = tbs.filter(status=cls.open).exclude(user=request_user)
        if not open_tbs:
            return
        private_tbs = open_tbs.filter(bet_tag__type=bet_tagging.models.BetTag.private)
        return private_tbs

    @classmethod
    def filter_premium(cls, tbs, request_user, open_tbs=None):
        """
        Returns the total bets of the given total bet queryset, for which the request user
        has no see permission (bets of premium bet groups to which request user is not subscribed to)
        """
        if not open_tbs:
            open_tbs = tbs.filter(status=cls.open).exclude(user=request_user)
        if not open_tbs:
            return
        premium_tbs = open_tbs.filter(bet_tag__type=bet_tagging.models.BetTag.premium)
        if not premium_tbs:
            return
        premium_bet_groups = bet_tagging.models.BetTag.objects.filter(total_bets__in=premium_tbs).distinct()
        hidden_bet_groups = []
        for bet_group in premium_bet_groups:
            active_subscribers = bet_group.get_active_subscribers()
            if request_user not in active_subscribers:
                hidden_bet_groups.append(bet_group)
        hidden_tbs = open_tbs.filter(bet_tag__in=hidden_bet_groups)
        return hidden_tbs

    @classmethod
    def permissions_filter(cls, tbs, request_user):
        """
        Returns the total bets of the given total bet queryset, for which the request user
        has no see permission (private and premium)
        """
        if not tbs:
            return None, None
        if not request_user.is_authenticated():
            # if user is unauthenticated label all open bets as private
            private_tbs = tbs.filter(status=cls.open)
            return private_tbs, None
        # Notice: if request_user is unauthenticated he has no id and the filtering will raise an exception
        open_tbs = tbs.filter(status=cls.open).exclude(user=request_user)
        private_tbs = cls.filter_private(tbs, request_user, open_tbs=open_tbs)
        premium_tbs = cls.filter_premium(tbs, request_user, open_tbs=open_tbs)
        return private_tbs, premium_tbs

    @classmethod
    def get(cls, gid):
        try:
            total_bet = cls.objects.get(id=gid)
            return total_bet
        except Exception as e:
            logger.warning('%s', e)
        return

    def has_see_permissions(self, user):
        """ Determine if the given user has permissions to see this total_bet """
        label = self.calc_label(user)
        if label == bet_tagging.models.BetTag.free:
            return True
        return False

    def update_odd(self):
        odd = 1.
        bets = self.bets.all()
        if bets:
            if len(bets) == 1:
                for bet in bets:
                    bet_odd = bet.odd
                    if bet_odd:
                        odd = odd * bet_odd
                    else:
                        logger.warning("Odd isn't calculated. Total bet %s has a bet with no odd", self)
                        return self.odd
                self.odd = odd
                self.save()
            else:
                # TODO BET SYSTEM calculate the total bet odd for a total bet with many bets
                logger.warning("Handle system bets")
        else:
            logger.warning("Odd isn't calculated. Total bet %s has no bets", self)
        return self.odd

    def calculate_total_return(self):
        # Notice: If there is even one Open bet then the return isn't calculated
        # Possible bet combinations of a total_bet: O, O-L, 0-W, O-W-L, W, W-L, L
        open_related_bets = self.bets.filter(status=Bet.open)
        total_return = self.total_return
        if not open_related_bets:
            won_related_bets = self.bets.filter(status=Bet.won)
            if not won_related_bets:
                total_return = 0.
            else:
                total_return = 0
                for won_related_bet in won_related_bets:
                    won_bet_return = won_related_bet.bet_return
                    if won_bet_return:
                        total_return = total_return + won_bet_return
                    else:
                        logger.error("total_bet %s status isn't updated. Won bet %s has no bet_return value", self, won_related_bet)
        else:
            # TODO BET SYSTEM If a total bet has bets that are still open, then we don't calculate their return.
            # It has a meaning to calculate the "partial" current return only for Bet systems (in which a total bet has
            # many bets)
            won_related_bets = self.bets.filter(status=Bet.won)
            logger.debug("total_bet %s return isn't calculated. It has open bets", self)
        return total_return, open_related_bets, won_related_bets

    def calculate_total_status(self, **kwargs):
        # The status is calculated from the return. This is a general solution that deals also with bet systems
        # We define additional arguments. This way if we already know them, we avoid the database hits. It assumes that
        # the total_return is already calculated. This because we consider a total bet as won if its return is greater than
        # the bet_amount. This was done to deal with bet_systems in which you can have return from some bets of the total
        # bet
        total_status = self.status
        if kwargs['total_return'] or kwargs['total_return'] == 0:
            total_return = kwargs['total_return']
        else:
            total_return = self.total_return

        if total_return or total_return == 0:
            if not kwargs['open_related_bets']:
                open_related_bets = self.bets.filter(status=Bet.open)
            else:
                open_related_bets = kwargs['open_related_bets']
            if not kwargs['won_related_bets']:
                won_related_bets = self.bets.filter(status=Bet.won)
            else:
                won_related_bets = kwargs['won_related_bets']

            # There are 7 possible cases. A total bet can have the following bet combinations: O, O-L, 0-W, O-W-L, W, W-L, L
            # Here we handle the 3 of them that have no open bets. When these open bets close, it will be calculated
            if not open_related_bets:
                if not won_related_bets:
                    total_status = TotalBet.lost
                else:
                    total_amount = self.amount
                    if total_amount and total_return:
                        if total_amount > total_return:
                            total_status = TotalBet.lost
                        else:
                            total_status = TotalBet.won
                    else:
                        logger.warning("total_bet %s status isn't calculated. Its bet_amount or/and its bet_return is None", self)
            else:
                logger.warning("total_bet %s status isn't calculated. It has open bets", self)
        else:
            logger.warning("total_bet %s status isn't calculated. The total_return must be calculated first", self)
        return total_status

    def calculate_decision_date(self, method="Active"):
        """
        In case that the call to the decision date is not the same day that the total bet closed then we can use the
        Passive method in order to define a decision date just after the last event of the total bet. This has to be
        like that for presentation reasons (total_bet history graph)
        """
        if method == 'Active':
            decision_date = timezone.now()
        else:
            bets = self.bets.all()
            bet_events = BetEvent.objects.filter(bet__in=bets).distinct()
            events = Event.objects.filter(bet_events__in=bet_events)
            latest_event_date = events.latest('date').date
            decision_date = latest_event_date + timezone.timedelta(hours=3)
        return decision_date

    def calculate_profit(self):
        """ returns the profit if the total bet is closed (it has total_return value) """
        # TODO bet systems
        if self.total_return:
            profit = self.total_return - self.amount
        elif self.total_return == 0:
            profit = 0
        else:
            # bet is open (has no total_return)
            profit = None
        return profit

    def calculate_bank_growth(self):
        """
        returns the bank_growth if the total bet is closed. THe difference with the calc profit is
        that it returns the amount of loss if the bet was lost
        """
        # TODO bet systems
        if self.total_return or self.total_return == 0:
            bank_growth = self.total_return - self.amount
        else:
            # bet is open (has no total_return)
            bank_growth = None
        return bank_growth

    def calculate_expected_profit(self):
        """ returns the expected profit meaning how much the total bet was aiming to win """
        # TODO bet systems
        expected_profit = self.amount*(self.odd - 1)
        return expected_profit

    def calc_balance_change(self):
        # So you can do: new balance = existing_balance + balance_change
        status = self.status
        if status == TotalBet.open:
            balance_change = -self.amount
        else:
            balance_change = self.total_return
        return balance_change

    def update_balance(self, is_reopened=False):
        """
        :param is_reopened: In the case that you want to reopen a tb then you must update the balance. In this case
        the balance must become as it was before the bet was closed
        :return:
        """
        logger.debug("updating balance...")
        balance_change = self.calc_balance_change()
        bet_tag = self.bet_tag
        old_balance = bet_tag.balance
        if not is_reopened:
            new_balance = old_balance + balance_change
        else:
            new_balance = old_balance - balance_change
        bet_tag.balance = new_balance
        logger.debug("[%s] old balance: %s, new_balance: %s, balance change: %s", bet_tag.name, old_balance, new_balance, balance_change)
        bet_tag.save(old_balance=old_balance, balance_change=balance_change, initiator=self)

    def get_bet_events(self):
        """ notice that the return value is a list not a queryset """
        # bets = Bet.objects.filter(totalbet__in=[self])
        bets = self.bets.all()
        if not bets:
            logger.error('Total Bet %s has no Bets', self.id)
            return
        # bet_events = BetEvent.objects.filter(bet__in=bets)
        bet_events = []
        for bet in bets:
            bet_events.extend(bet.bet_events.all())
        return bet_events

    def to_percent(self, *values):
        """ Transforms the given values to percent of the bet_tag_balance as it was the time the tb was submitted """
        percent_values = []
        for value in values:
            if not value and value != 0:
                # For example if tb is open, bank growth is None. The percent would be None. Handle it in template
                percent_value = None
            elif value == 0:
                # For example if tb is void, total_return is 0.
                percent_value = 0
            else:
                try:
                    percent_value = value/self.bet_tag_balance_snapshot * 100
                except ZeroDivisionError:
                    # in case in which you have submit a bet when you had 0 balance
                    # maybe used for past bets, normally this is not allowed
                    percent_value = 100
            percent_values.append(percent_value)
        return percent_values

    def normalize_attributes(self):
        # self.normalization_method = NormalizationMethods.percent
        values = list()
        values.append(self.amount)
        values.append(self.total_return)
        values.append(self.bank_growth)
        percents = self.to_percent(*values)
        # logger.debug('percents: %s', percents)
        # temporarily overriding total_bet values for use in the template
        self.amount = "{:.2f} %".format(percents[0])
        self.total_return = "{:.2f} %".format(percents[1]) if percents[1] else 0  # id None or 0 make 0
        self.bank_growth = "{:.2f} %".format(percents[2]) if percents[2] else 0

    def calc_label(self, user):
        """ Calculates the label of this total bet for the given user. Notice that user's private
         or premium bets will be labeled as Free for that user """
        # permissions_filter function works with a queryset argument so we create one here
        logger.debug("calculating label for tb: %s and user: %s", self, user)
        tbs_qs = TotalBet.objects.filter(id=self.id)
        private_tbs, premium_tbs = TotalBet.permissions_filter(tbs_qs, user)
        if private_tbs:
            if self in private_tbs:
                return bet_tagging.models.BetTag.private
        if premium_tbs:
            if self in premium_tbs:
                return bet_tagging.models.BetTag.premium
        return bet_tagging.models.BetTag.free

    def add_temp_label(self, request_user, label_free=False, private_tbs=None, premium_tbs=None):
        """ adds a temp label attribute to total bet checking if it belongs to the given
        private and premium total bets. If no private or premium are given then the total bet
        is checked if it is a private or premium. Giving the arguments you spare calculation time """
        if label_free:
            self.label = bet_tagging.models.BetTag.free
            return
        if not private_tbs or not premium_tbs:
            self.label = self.calc_label(request_user)
            return
        self.label = bet_tagging.models.BetTag.free
        if private_tbs:
            if self in private_tbs:
                self.label = bet_tagging.models.BetTag.private
        if premium_tbs:
            if self in premium_tbs:
                self.label = bet_tagging.models.BetTag.premium

    def obscure_hidden_values(self):
        if self.label == bet_tagging.models.BetTag.private or self.label == bet_tagging.models.BetTag.premium:
            self.odd = 1
            self.bank_growth = 1
            self.amount = 1

            # NOTICE: doing self.bets = [1] saves in the database (without explicit save) don't do it EVER!!
            bet_event = gutils.utils.DummyObject()
            event = gutils.utils.DummyObject()
            home_team = gutils.utils.DummyObject()
            home_team.generic_name = 'Home'
            away_team = gutils.utils.DummyObject()
            away_team.generic_name = 'Away'
            event.home_team = home_team
            event.away_team = away_team
            bet_event.event = event
            bet = gutils.utils.DummyObject()
            bet.bet_events = gutils.utils.DummyObject()
            bet.bet_events.all = bet_event

    @classmethod
    def batch_enrich(cls, tbs, request, cash_mode='calculate', label_all_free=False):
        """
        It adds some temporary attributes to the total bets mainly for presentation purposes.
        It also normalizes the total bet's attributes that depend on the normalization parameter.
        This function must always be called when the total_bet is to be used in a template.
        :param label_all_free: skip the expensive private and premium calculations and label all as Free
        This is useful when the permissioned tbs have already been excluded from the given tbs argument.
        """
        if not tbs:
            return
        # if you want to label all as free, then the private and premium tbs values are irrelevant
        private_tbs = None
        premium_tbs = None
        if not label_all_free:
            private_tbs, premium_tbs = cls.permissions_filter(tbs, request.user)
        for tb in tbs:
            tb.enrich(request, cash_mode, label_all_free, private_tbs, premium_tbs)

    def enrich(self, request, cash_mode='calculate', label_free=False, private_tbs=None, premium_tbs=None):
        """
        It adds some temporary attributes to the total bet mainly for presentation purposes.
        It also normalizes updates the attributes that depend on the normalization parameter.

        It checks if normalized data are to be sent and adds some temporary attributes to the total_bet. These attributes
        are added even if not normalized data are to be sent. This function must always be called when the total_bet is
        to be used in a template
        :param request:
        :param cash_mode: Choose the mode in which you want the values to be shown (real cash values or normalized ones)
        In default value the function checks the users settings to decide if normalized values should
        be used. If it is False then normalized values are used. If True then real values are used
        :param private_tbs: A queryset of un-permission private tbs. If current tb is one of them enrich it as "Private"
        :param premium_tbs: A queryset of un-permission premium tbs. If current tb is one of them enrich it as "Private"
        :param label_free:
        """
        self.bank_growth = self.calculate_bank_growth()
        self.add_temp_label(request.user, label_free, private_tbs, premium_tbs)
        if cash_mode == 'calculate':
            target_user = self.user
            if not gutils.utils.show_in_money_mode(request, target_user):
                self.normalize_attributes()
        elif not cash_mode:
            self.normalize_attributes()
        # else: show in cash mode (real values as read from the db)

    def settle(self, instant_user_cache_update=True):
        """
        :param instant_user_cache_update: Give False to avoid updating the cache for each total bet.
        If you settle many total bets of a user at once, then it is not efficient to
        update user's cache after each individual total bet settlement. The user cache can be updated just one time
        at the end.
        :return has_changed: If the tb is already closed then nothing has changed (so no further actions need to
         be taken)
        """
        has_changed = False
        closed_total_bets = []
        open_total_bets = []
        # TODO OPEN TOTAL BETS CHECK
        # Currently there is no need to resettle settled tbs, so I protect them.
        if self.status == TotalBet.open:
            # The total bet is open if it has no calculated return, which happens if not all of its bets are closed
            # if self.status != TotalBet.open:
            #     # in this case the tb was already settled and the bet group balance was updated. Since the tb will be
            #     # resettled the balance must be reversed to its prior state as it was when this tb was open
            #     logger.warning("Total Bet %s will be resettled despite the fact that it was already settled", self.id)
            #     self.update_balance(is_reopened=True)
            bets = self.bets.all()
            for bet in bets:
                # in case that it has void bets (the odd of which has changed) we recalculate the total bet odd
                if bet.bet_events.filter(selection__status=Selection.void):
                    logger.debug('bet %s has void bet_events. Total_bet %s odd is recalculated...', bet, self)
                    total_bet_odd = self.update_odd()
            total_return, open_related_bets, won_related_bets = self.calculate_total_return()
            total_status = self.calculate_total_status(total_return=total_return, open_related_bets=open_related_bets, won_related_bets=won_related_bets)
            if total_status != TotalBet.open:
                self.total_return = total_return
                self.status = total_status
                # decision date method Active for production
                decision_date = self.calculate_decision_date(method="Active")
                self.decision_date = decision_date
                self.save()
                # save() to db is a sync operation so the total bet is saved when the signal is emitted
                signal_result = gutils.utils.total_bet_closed.send_robust(sender=TotalBet, total_bet=self)
                if instant_user_cache_update:
                    import bet_statistics.signals
                    bet_statistics.signals.update_user_cache(self.user.id)
                closed_total_bets.append(self)
            else:
                open_total_bets.append(self)
                logger.debug('total_status remains open')
            has_changed = True
        else:
            logger.debug("total_bet %s is already closed", self)
        return has_changed

    # TODO override TotalBet save() method to check total_return, amount, odd values

    def calc_past(self, comparison_date=timezone.now()):
        """
        used for submitting past bets. If at least one bev is settled or it is of past date
        then it belongs to a past total bet.
        :param comparison_date:
        :return:
        """
        if self.date < comparison_date:
            return True
        return False

        # bet_events_list = self.get_bet_events()
        # if not bet_events_list:
        #     logger.warning('total bet %s has no bet events', self)
        #     return False
        #
        # for bev in bet_events_list:
        #     if bev.event.status != Event.in_play:
        #         status = bev.selection.status
        #         if status != Selection.open or bev.event.date < comparison_date:
        #             return True
        #     else:
        #         # todo handle live bets
        #         pass
        # return False

    def update_past_status(self, comparison_date=timezone.now()):
        is_past = self.calc_past(comparison_date)
        if is_past:
            self.is_past = True
            self.save()
        return is_past

    # @property
    # def extra_activity_data(self):
    #     """
    #     By subclassing the Activity class in a model, the actor, verb, object, time and foreign_id are automatically
    #     selected by user field, model name, model instance, created_at field and model instance respectively
    #     Here you can define extra fields for the activity that will be created in the Stream db.
    #     :return:
    #     """
    #     return {'amount': self.amount, 'bookmaker': self.bookmaker.name}

    @classmethod
    def get_distinct_user_ids(cls, tbets):
        if not tbets:
            return []
        user_ids = []
        for tbet in tbets:
            user_ids.append(tbet.user.id)
        user_ids = list(set(user_ids))
        return user_ids

    @classmethod
    def resettle_total_bets(cls, total_bets):
        """ Similar with reprocessing bets """
        TotalBet.objects.filter(pk__in=total_bets).update(status=cls.open, total_return=None, decision_date=None)
        closed_total_bets, open_total_bets, changed_total_bets = cls.settle_total_bets(total_bets)
        return closed_total_bets, open_total_bets, changed_total_bets

    @classmethod
    def settle_total_bets(cls, total_bets, update_cache=True):
        if not total_bets:
            logger.debug("there are no total_bets to settle")
            return [], [], []
        logger.debug("settling %s total_bets...", len(total_bets))
        closed_total_bets = []
        open_total_bets = []
        changed_total_bets = []
        users = {}
        for total_bet in total_bets:
            has_changed = total_bet.settle(instant_user_cache_update=False)
            if total_bet.status != cls.open:
                closed_total_bets.append(total_bet)
                if has_changed:
                    user_id = total_bet.user.id
                    users[user_id] = user_id
                    changed_total_bets.append(total_bet)
            else:
                open_total_bets.append(total_bet)

        if update_cache:
            from bet_statistics.signals import update_user_cache
            for user_id in users.values():
                update_user_cache(user_id)
        return closed_total_bets, open_total_bets, changed_total_bets


# # TEMPORARY CLASSES FOR USE IN PLACE OF DICTIONARIES for all_markets and planned_events
# # __slots__ check it
# class TempEvent():
#     def __init__(self, event, num_of_markets, temp_market_types=None):
#         self.event = event
#         self.num_of_markets = num_of_markets
#         self.temp_market_types_with_order = temp_market_types_with_order
#         # [{'order': 3, 'market': temp_market3}, {'order': 1, 'market': temp_market1}..] To be sorted by template filter
#
#     def __unicode__(self):
#         return self.event, self.temp_market_types
#
#     def __del__(self):
#         print('temp_event deleted')
#
#
# class TempMarketType():
#     def __init__(self, market_type, temp_latest_odd):
#         self.market_type = market_type
#         self.temp_latest_odd = temp_latest_odd
#
#     def __unicode__(self):
#         return self.market_type, self.temp_latest_odd
#
#     def __del__(self):
#         print('temp_market_type deleted')
#
#
# class TempOdd():
#     def __init__(self, latest_odd, from_selected_bookmaker):
#         self.latest_odd = latest_odd
#         self.from_selected_bookmaker = from_selected_bookmaker
#
#     def __unicode__(self):
#         return self.latest_odd, self.from_selected_bookmaker
#
#     def __del__(self):
#         print('temp_odd deleted')


class GenericCommentModerator(SpamModerator, XtdCommentModerator):  # XtdCommentModerator
    # todo notify users that their comment is being moderated due to forbidden words
    # sent to managers if a comment is marked for moderation or if a new comment is published
    email_notification = False
    # sent to managers if there is a suggestion for removal (Removal suggestion flag created)
    removal_suggestion_notification = True

    def moderate(self, comment, content_object, request):
        # logger.debug("moderating %s %s....", comment, content_object)
        # logger.debug("searching for forbidden words: %s", forbidden_words)
        # Make a dictionary where the keys are the words of the message and
        # the values are their relative position in the message.

        def clean(word):
            ret = word
            if word.startswith('.') or word.startswith(','):
                ret = word[1:]
            if word.endswith('.') or word.endswith(','):
                ret = word[:-1]
            return ret

        lowcase_comment = comment.comment.lower()
        msg = dict([(clean(w), i) for i, w in enumerate(lowcase_comment.split())])
        for forbidden_word in forbidden_words:
            # logger.debug("forbidden_word: %s", forbidden_word)
            if isinstance(forbidden_word, unicode) or isinstance(forbidden_word, str):
                if lowcase_comment.find(forbidden_word) > -1:
                    return True
            else:
                # logger.debug("forbidden word is not str nor unicode")
                lastindex = -1
                for subword in forbidden_word:
                    if subword in msg:
                        if lastindex > -1:
                            if msg[subword] == (lastindex + 1):
                                lastindex = msg[subword]
                        else:
                            lastindex = msg[subword]
                    else:
                        break
                if msg.get(forbidden_word[-1]) and msg[forbidden_word[-1]] == lastindex:
                    return True
        return super(GenericCommentModerator, self).moderate(comment, content_object, request)


moderator.register(TotalBet, GenericCommentModerator)
