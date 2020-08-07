from __future__ import unicode_literals
import logging
from collections import defaultdict
from django.db import transaction
from django.contrib.sites.models import Site
from django.utils import timezone
import zakanda.utils
from zakanda.settings import Dummies
import games.models
import games.naming
from gutils.views import try_cache_first


logger = logging.getLogger(__name__)


# --------- CREATE ENTITIES -------------

# -- Initial data --
def create_initial_data():
    create_site_entry()
    create_dummies()
    get_or_create_sources()
    get_or_create_sports()
    get_or_create_seasons()
    create_markets()
    get_or_create_market_results()
    get_or_create_void_results()


def create_site_entry():
    logger.info('creating site entry...')
    site = Site.objects.get(id=1)  # the default one
    site.name = 'zakanda'
    # todo now check urls for example: leader_board_url = reverse('user_accounts:leader_board')
    site.domain = 'www.zakanda.com'
    site.save()


def create_dummies():
    logger.info('creating dummies...')
    dummy_source, s_created = games.models.Source.objects.get_or_create(name=Dummies.name)
    dummy_bookmaker = create_bookmaker_tree(Dummies.name, dummy_source, Dummies.name, Dummies.sid)
    stoiximan_bookmaker = create_bookmaker_tree("Stoiximan", dummy_source, "Stoiximan", 2)


def get_or_create_sources():
    logger.info('creating sources...')
    source_names = games.naming.source_names
    sources = []
    for source_name in source_names:
        source, created = games.models.Source.objects.get_or_create(name=source_name)
        sources.append(source)
    return sources


def get_or_create_sports():
    logger.info('creating sports...')
    football_gname = games.naming.sport_names.get('football')
    source_01 = games.models.Source.objects.get(name=Dummies.name)
    source_02 = games.models.Source.objects.get(name=games.naming.source_names[3])  # sportmonks
    sources = [source_01, source_02]
    sports = []
    sports_sinfo = []
    for source in sources:
        if source == source_01:
            sport, sport_sinfo = create_sport_tree(gname=football_gname, source=source, sname=football_gname, sid=Dummies.sid)
        else:
            sport, sport_sinfo = create_sport_tree(gname=football_gname, source=source, sname='Soccer', sid=1)
        sports.append(sport)
        sports_sinfo.append(sport_sinfo)
    return sports, sports_sinfo


def supported_markets():
    supported_markets_list = []
    for market_name_tupple in games.models.MarketType.market_type_choices:
        market_name = market_name_tupple[1]
        if market_name.find('Asian') == -1:
            supported_markets_list.append(market_name)
    return supported_markets_list


def create_markets():
    logger.info('creating markets...')
    supported_markets_list = supported_markets()
    for market_name in supported_markets_list:
        market, market_created = games.models.MarketType.objects.get_or_create(name=market_name)


def get_or_create_seasons():
    logger.info('creating seasons...')
    seasons = []
    for season in games.models.Season.season_choices:
        season_name = season[0]
        season, created = games.models.Season.objects.get_or_create(name=season_name)
        seasons.append(season)
    return seasons


def get_or_create_market_results():
    logger.info('creating market_results...')
    market_results = []
    for choice in games.models.MarketResult.market_choices:
        market_result = games.models.MarketResult.objects.get_or_create(result=choice[0])
        market_results.append(market_result)
    return market_results


# -- Initial data --


def create_event_tree(event_date_as_datetime, competition_season, home_team, away_team, event_round, source, event_sid):
    # Notice: -It applies to all trees-
    # todo high The necessary attributes to determine if an entry exists or not, must not be
    # manually altered through the Admin so that no new entries are created during
    # a get_or_create call, without a real reason.
    logger.debug("getting creating event tree...")
    try:
        with transaction.atomic():
            event, event_created = games.models.Event.objects.get_or_create(
                # It has the default status which is "Not Started"
                date=event_date_as_datetime,
                competition_season=competition_season,
                home_team=home_team,
                away_team=away_team,
                round=event_round,
            )
            if event_created:
                logger.info("event %s was created successfully", event)
            # notice that in case of a postponed events: Some APIs use the same sid of the original event
            # for the newly arranged event.
            # In this case there will be 2 events with the same sid (for the same source).
            # The 2 events are 2 different zakanda events since they have a different date.
            # There are also 2 different event_info entries with the same sid, since they are connected
            # with different events.
            # I must check all cases in which I get an event from its sid. sid to event will not be one to one.
            # the other option is to update the existing event info. But this will leave the original event
            # without an event info. Check which approach is better. probably disable the constraint and use
            # latest to get the event from an sid and source.
            event_info, event_info_created = games.models.EventInfo.objects.get_or_create(source=source, sid=event_sid, event=event)
            if event_info_created:
                logger.info("event_info %s for event %s created successfully", event_info, event)
            else:
                logger.info("event_info %s already existed", event)
    except Exception as e:
        logger.error("%s, transaction rolled back, event tree wasn't created %s - %s %s %s ", e, home_team, away_team, competition_season, event_date_as_datetime)
        return None, False, None, False
    return event, event_created, event_info, event_info_created


def create_competition_season_tree(competition, season, source, competition_season_sid, competition_sname, competition_season_type):
    """ creates a competition_season and its corresponding competition_season_info for the given source """
    # logger.debug("creating competition_season tree...")
    if not competition or not season or not source or not competition_sname:
        logger.warning("competition season tree can not be created! competition: %s, season: %s, source: %s, "
                       "competition_sname: %s", competition, season, source, competition_sname)
        # the specific comp_season will no be created. Others that are valid will be created
        return None, False, None, False
    competition_season, competition_season_created = games.models.CompetitionSeason.objects.get_or_create(
        competition=competition, season=season, type=competition_season_type)
    competition_season_info, competition_season_info_created = games.models.CompetitionSeasonInfo.objects.get_or_create(
        source=source,
        sid=competition_season_sid,
        sname=competition_sname
    )
    return competition_season, competition_season_created, competition_season_info, competition_season_info_created


def create_competition_tree(competition_season_utils, competition_gname, country, sport, source, competition_sgname, competition_sid):
    """
    creates a competition and a competition_season for each given season. Many competition_season trees are going
    to be created (one for each competition_season_util object) so even if some of these objects are invalid
    the valid ones will still be created.
    Each comp_season is connected with at least one competition_season_info, so one such entity is created for
    the given source.
    :param competition_sid: it is the competition specific id
    :param competition_sgname: it is the competition specific name
    :param competition_season_utils: It is a list of some help objects that map season objects
    to competition_season_specific ids and names
    """
    logger.info("getting creating competition tree %s (%s comp_seasons)...", competition_gname, len(competition_season_utils))
    try:
        with transaction.atomic():
            # todo: a comp_seas can have different sname (or sid) per season (through the comp_seas_info model).
            # the comp_seas_info is created from the comp_seas_util objects. one comp_seas object is created per
            # season all of them use the same name which is the current generic name of the source (sportmonks).
            # Normally this name is only the sname of the current season.
            # This has this outcome: if there is a change in the name of the competition in the source, then the
            # zakanda competition already exists and the comp_info already exists. But since now there is a
            # different name, a new comp_info will be created. But we don't allow more than one info for
            # each comp so we get an integrity error. The information that there is a new name for the current season
            # is mend to be kept in the comp_seas_info. So if I want to have the new name I must
            # change the code so that the exception is not raised and a new comp_seas_info is created with the new name
            # while the existing comp_seas_info remain the same, or update the existing comp_seas_info sgname.
            competition, c_created = games.models.Competition.objects.get_or_create(
                country=country, sport=sport, generic_name=competition_gname)
            competition_info, ci_created = games.models.CompetitionInfo.objects.get_or_create(
                competition=competition, source=source, sid=competition_sid, sgname=competition_sgname)
            competition_seasons = []
            for util in competition_season_utils:
                competition_season, cs_created, competition_season_info, csi_created = create_competition_season_tree(
                    competition, util.season, source, util.competition_season_sid, util.competition_season_sname,
                    util.competition_season_type
                )
                # logger.debug("competition_season %s created %s, competition_season_info %s created %s",
                #              competition_season, cs_created, competition_season_info, csi_created)
                if competition_season_info:
                    competition_season.infos.add(competition_season_info)
                if competition_season:
                    competition_seasons.append(competition_season)
                if cs_created:
                    logger.info('competition season %s was created successfully', competition_season)
                if csi_created:
                    logger.info('competition season info %s was created successfully', competition_season_info)
            if c_created:
                logger.info("competition %s was created successfully", competition)
            if ci_created:
                logger.info("competition_info %s was created successfully", competition_info)
    except Exception as e:
        logger.error("%s, transaction rolled back, competition tree %s wasn't created. "
                     "input values: gname: %s, country: %s, sport: %s, source: %s, sname: %s, sid: %s, "
                     "comp_Seas_utils: %s", repr(e), competition_gname,
                     competition_gname, country, sport, source, competition_sgname, competition_sid,
                     [(util.competition_season_sname, util.competition_season_sid) for util in competition_season_utils])
        return None, None
    return competition, competition_seasons


def create_sport_tree(gname, source, sname, sid=None):
    logger.debug("getting creating sport tree...")
    try:
        with transaction.atomic():
            sport, sport_created = games.models.Sport.objects.get_or_create(name=gname)
            sport_info = games.models.SportInfo.objects.get_or_create(sport=sport, source=source, sname=sname, sid=sid)
    except Exception as e:
        logger.error("%s, transaction rolled back, sport tree %s wasn't created", e, gname)
        return None, None
    return sport, sport_info


def create_country_tree(gname, source, sname, sid, fifa_code=None):
    logger.debug("getting creating country tree...")
    try:
        with transaction.atomic():
            country, country_created = games.models.Country.objects.get_or_create(name=gname)
            if fifa_code:
                # if the fifa code is different from the existing one, then no new country is created.
                # Instead, the existing code is updated with the new value
                country.fifa_code = fifa_code
                country.save()
            country_info, ci_created = games.models.CountryInfo.objects.get_or_create(country=country, source=source, sname=sname, sid=sid)
    except Exception as e:
        logger.error("%s, transaction rolled back, country tree %s wasn't created", e, gname)
        return None, None
    return country, country_info


def create_bookmaker_tree(gname, source, sname, sid):
    # logger.debug("getting creating bookmaker tree...")
    if gname == Dummies.name:
        source = games.models.Source.objects.get(name=Dummies.name)
        sid = Dummies.sid
    try:
        with transaction.atomic():
            bookmaker, bookmaker_created = games.models.Bookmaker.objects.get_or_create(name=gname)
            bookmaker_info, bi_created = games.models.BookmakerInfo.objects.get_or_create(bookmaker=bookmaker, source=source, sname=sname, sid=sid)
            if bookmaker_created:
                logger.info("bookmaker for %s created successfully", bookmaker)
            if bi_created:
                logger.info("bookmaker info was added for bookmaker %s", bookmaker)
    except Exception as e:
        logger.warning("%s, transaction rolled back, bookmaker tree %s wasn't created", e, gname)
        return None
    return bookmaker


def create_team_tree(gname, source, sname, sid, competition_season):
    logger.debug("getting creating team tree...")
    try:
        with transaction.atomic():
            team, team_created = games.models.Team.objects.get_or_create(generic_name=gname)
            team_info, team_info_created = games.models.TeamInfo.objects.get_or_create(
                team=team,
                source=source,
                sname=sname,
                sid=sid,
                # defaults={'timestamp': timezone.now()}
            )
            if team_created:
                logger.info("team %s [%s] was created successfully", team, competition_season)
            if team_info_created:
                logger.info("team info %s [%s] was created successfully", team_info, competition_season)
            team.competition_seasons.add(competition_season)
    except Exception as e:
        logger.warning("%s, transaction rolled back, team tree %s wasn't created", e, gname)
        return None, False, None, False
    return team, team_created, team_info, team_info_created


def get_or_create_void_results():
    types = games.models.Result.void_types
    results = []
    for res_type in types:
        result, created = games.models.Result.objects.get_or_create(home_goals=0, away_goals=0, minute=0, type=res_type, final=True)
        results.append(result)
    return results


# --------- GET ENTITIES -------------
def split_final_no_final_events(events):
    """ splits events between a list with events that have a final result and one that doesn't """
    no_fr_events = []
    fr_events = []
    # logger.debug('events for splitting: %s', events)
    for event in events:
        res = event.has_final_result()
        if not res:
            no_fr_events.append(event)
        else:
            fr_events.append(event)
    logger.debug("%s events without final result were found", len(no_fr_events))
    logger.debug("%s events with final result were found", len(fr_events))
    return no_fr_events, fr_events


def split_decision_no_decision_events(events):
    ndr_events = []  # no decision result events
    dr_events = []
    for event in events:
        res = event.get_decision_result()
        if not res:
            ndr_events.append(event)
        else:
            dr_events.append(event)
    logger.debug("%s events without decision result type", len(ndr_events))
    logger.debug("%s events with decision result type", len(dr_events))
    return ndr_events, dr_events


def split_open_closed_events(events):
    open_events = []
    closed_events = []
    for event in events:
        if event.status == games.models.Event.not_started:
            open_events.append(event)
        else:
            closed_events.append(event)
    return open_events, closed_events


def split_void_events(events):
    void_events = []
    no_void_events = []
    for event in events:
        if event.status in games.models.Event.void_event_statuses:
            void_events.append(event)
        else:
            no_void_events.append(event)
    return void_events, no_void_events


def events_by_iso8601_daterange(start_date, end_date, status):
    """
    db data are stored in utc
    :param start_date, end_date: ISO 8601 (1997-07-16T19:20:30+01:00)
    :return: list of filtered events
    """
    from dateutil import parser
    # utc = pytz.timezone(timezone)
    # min_dt = timezone.datetime(2015, 11, 06, tzinfo=utc)
    # max_dt = timezone.datetime(2015, 11, 10, tzinfo=utc)
    start_date_datetime = parser.parse(start_date)
    end_date_datetime = parser.parse(end_date)
    # if you use .filter(date=date) the date is a datetime object and it will try to match to the exact millisecond so
    # probably no entries will be returned
    events = games.models.Event.objects.filter(date__range=(start_date_datetime, end_date_datetime), status=status)
    return events


def event_sids_per_source(events, source_name=None):
    """
    You get the sids (ids that the source APIs use) for the given events
    :param events: list, event instances
    :param source_name: string, optional, filter only for this source
    :return: dict of dicts, {event_id: {u'xmlSoccer': event_sid, u'otherSource': event_sid}}
    """

    sids_per_source = {}
    for event in events:
        event_info_entries = games.models.EventInfo.objects.filter(event=event)
        if source_name:
            event_info_entries = event_info_entries.filter(source__name=source_name)
        sid_per_event = {}
        for event_info in event_info_entries:
            event_sid = event_info.sid
            event_source_name = event_info.source.name
            sid_per_event[event_source_name] = event_sid
        sids_per_source[event.id] = sid_per_event
    # print(sids_per_source)
    return sids_per_source


def event_distinct_sid_list(event_ids, source_name):
    event_sids = []
    for event_id in event_ids:
        if not event_id:
            continue
        event_info_entries = games.models.EventInfo.objects.filter(event__id=event_id).filter(source__name=source_name)
        for event_info in event_info_entries:
            # have in mind that if a source has different sid for postponed events there could be sids that
            # appear more than one times in the list
            event_sid = event_info.sid
            event_sids.append(event_sid)
    event_sids = list(set(event_sids))  # distinct sids list
    return event_sids


def get_competition_type_from_sname(sname, source):
    # TODO CompetitionInfo model. It must be updated to support the new CompetitionInfo model
    """
    Notice that there is no such thing as type of competition. The competition_season has the type attribute. This way
    a competition might change types depending on the season. In this function we don't know the season so we return the
    type of the most recently created competition_season which is probably the one that we want. Notice that this rarely
    will be an issue since most competitions don't change type. But have it in mind
    """
    # TODO have in mind get competition type for correct season
    competition_season_type = None
    try:
        competition_season_info = games.models.CompetitionSeasonInfo.objects.filter(sname=sname, source=source).latest()
        # any comp_season related with this info refer to the competition.
        competition_season = competition_season_info.competition_seasons.all().latest()
        if competition_season:
            competition_season_type = competition_season.type
    except games.models.CompetitionSeasonInfo.DoesNotExist:
        logger.warning("CompetitionSeasonInfo doesn't exist in db. Competition type won't be calculated")
    return competition_season_type


def get_competition_type_from_gname(gname):
    """
    We get the type of the most recently created competition season. See get_competition_type_from_sname description
    """
    competition_season_type = None
    try:
        competition_season_type = games.models.CompetitionSeason.objects.filter(competition__generic_name=gname).latest().type
    except games.models.CompetitionSeason.DoesNotExist:
        logger.warning("CompetitionSeason doesn't exist in db. Competition type won't be calculated")
    return competition_season_type


def get_competition_season_from(competition_sname, source, season):
    # TODO CompetitionInfo model. It must be updated to support the new CompetitionInfo model
    # we can't get directly the competition season entry, since we have the comp sname not the gname.
    # So we need to get it through its comp_seas_info that contains the sname (but not the season)
    # There is the chance that there is a comp_seas_info that is from the same source, has the same sname but
    # different sid. This might happen if the source API change the competition sid in a new season. But since we
    # search all the comp_seas_infos independently of seasons we might have more than one com_seas_info with the
    # same name. But only one of them corresponds to the specific season and so to the specific
    # competition_season that we want. This is why we loop through them and collect the one with the season that we want
    competition_season_infos = games.models.CompetitionSeasonInfo.objects.filter(sname=competition_sname, source=source)
    competition_season = None
    for competition_season_info in competition_season_infos:
        # normally only one comp_seas will be filtered
        competition_season = competition_season_info.competition_seasons.filter(season=season).first()
        if competition_season:
            break
    return competition_season


def get_competition_season_list_from(competition_ids='All', season_names='All'):
    """
    get the competition seasons for given season names and competition generic names.
    the arguments must by tuples of names or "All"
    :param competition_ids: list of competition gids
    :param season_names: list of season names
    """
    # todo replace the stupid 'All' default value with None
    seasons = []
    competitions = []

    if season_names == 'All':
        seasons = games.models.Season.objects.all()
    else:
        for season_name in season_names:
            season = zakanda.utils.season_from_season_name(season_name)
            if season:
                seasons.append(season)

    if competition_ids == 'All':
        competitions = games.models.Competition.objects.all()
    else:
        for competition_id in competition_ids:
            try:
                competition = games.models.Competition.objects.get(id=competition_id)
                competitions.append(competition)
            except games.models.Competition.DoesNotExist:
                logger.warning("Competition %s doesn't exist in the database", competition_id)

    competition_seasons = games.models.CompetitionSeason.objects.filter(
        season__in=seasons).filter(competition__in=competitions)
    logger.info('%s competition seasons were selected', competition_seasons.count())
    return competition_seasons


# TODO it needs to be checked for competitions that have more than one info
def get_distinct_comp_seas_info_list_from(competition, season='All'):
    # why I did this function? There is no way to have a duplicated info since I do get_or_create to create them or not?
    competition_season_infos = []
    if season == 'All':
        competition_seasons = games.models.CompetitionSeason.objects.all().filter(competition=competition)
    else:
        competition_seasons = games.models.CompetitionSeason.objects.all().filter(competition=competition, season=season)
    for competition_season in competition_seasons:
        infos = competition_season.infos.distinct()
        for info in infos:
            competition_season_infos.append(info)
    competition_season_infos = list(set(competition_season_infos))
    return competition_season_infos


def get_events_in_daterange_and_competition(competition_id, start_date, end_date, status_list):
    """
    it gets the events for the given arguments.
    if seasons from start and end date are different (for example start date 25/5 end date 10/6 for winter
    or 25/12 - 10/1 for summer types) then events from both seasons are returned as they should
    """
    logger.debug("getting events in range: %s - %s and competition: %s", start_date, end_date, competition_id)
    filtered_events_list = []
    country_name = None
    try:
        competition = games.models.Competition.objects.get(id=competition_id)
        country_name = competition.country.name

        competition_seasons = competition.competition_seasons.all()
        # Here I collected only the competition_seasons for the seasons extracted by the dates.
        # But WC qualification season is 2018 despite the fact that the event might take place
        # in 2016, 2017. So instead you can search for the events in the date range for all the competition seasons.
        # dates = [start_date, end_date]
        # competition_seasons_dict = defaultdict(int)
        # for date in dates:
        #     competition_season = zakanda.utils.competition_season_by_datetime_and_competition(date, competition)
        #     competition_seasons_dict[competition_season] += 1
        #
        # competition_seasons = competition_seasons_dict.keys()
        #
        # if None in competition_seasons:
        #     return [], country_name

        filtered_events_list = games.models.Event.objects.filter(competition_season__in=competition_seasons).exclude(public=False)
        if start_date and end_date:
            filtered_events_list = filtered_events_list.filter(date__range=(start_date, end_date))
        if status_list:
            filtered_events_list = filtered_events_list.filter(status__in=status_list)
        logger.debug('num filtered evens: %s', filtered_events_list.count())

    except games.models.Competition.DoesNotExist:
        logger.error("Competition %s doesn't exist", competition_id)
    return filtered_events_list, country_name


# @try_cache_first(timeout=60*60*24)
def get_events_in_daterange_and_competitions(competition_ids, start_date, end_date, status_list):
    """
    it gets the events of the given competition_ids, for the given date range, status and season of the end_date
    :param competition_id: it can be either a list of competition ids, or one id, or "All"
    """
    logger.debug("getting events...")
    if type(competition_ids) is list or type(competition_ids) is tuple:
        competition_ids = competition_ids
    elif competition_ids == 'All':
        competitions = games.models.Competition.objects.all()   # competition objects
        competition_ids = games.models.Competition.ids_list(competitions)
    else:
        competition_ids = [competition_ids]

    all_events = []
    events_per_competition = {}
    counter = 0
    logger.debug("comp ids: %s", competition_ids)
    for competition_id in competition_ids:
        if competition_id == 623 or competition_id == '623':
            # Important: For World Cup show events of extended period
            # (for a specific competition the id is a string)
            end_date = end_date + timezone.timedelta(days=20)
        planned_competition_events_list, country_name = get_events_in_daterange_and_competition(competition_id, start_date, end_date, status_list)
        if planned_competition_events_list:
            events_per_competition[counter] = planned_competition_events_list
            all_events.extend(planned_competition_events_list)
            counter += 1
    return events_per_competition, all_events


def get_bet_events(total_bets, distinct=False, exclude_open=False):
    """
    if you want to get all the bet_events from all bets of a user, then the bets must not be distinct and also when
    the bet_events are selected from these bets, then if a bet appears more than one times, then its bet_events
    must be added to the list, more than one times (this is what values() method does indirectly).
    this is achieved without using the distinct in both queries. Notice that the values() method must not be used in
    such a queryset since the results will be multiplied
    :param total_bets queryset or list
    """
    # TODO BET SYSTEMS check if the bets are collected properly (for statistics calculations)
    bets = games.models.Bet.objects.filter(totalbet__in=total_bets)
    bet_events = games.models.BetEvent.objects.filter(bet__in=bets)
    if distinct:
        bet_events = games.models.BetEvent.objects.filter(bet__in=bets).distinct()
    if exclude_open:
        bet_events = bet_events.exclude(selection__status=games.models.Selection.open)

    # logger.debug('bets: len %d', len(bets))
    # logger.debug('bet events: len %d', len(bet_events))
    return bet_events


def get_bet_events_from(total_bet):
    bets = total_bet.bets
    bet_events_per_bet = {}
    for bet in bets.all():
        # todo bet system we return bet events per bet (nothing to be done just for reference)
        bet_events_per_bet[bet] = bet.bet_events.all()
    return bet_events_per_bet