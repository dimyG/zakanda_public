from __future__ import unicode_literals

from django.shortcuts import render
from django_rq import job

import pytz
import logging
import numpy as np
from dateutil import parser
from collections import defaultdict

from xmlSoccer import XmlSoccer
import zakanda.utils
import zakanda.db
import zakanda.settings
import data_sources.pre_models
import games.models
import games.naming
import games.utils
import utils
from utils import get_native_source


global_XMLSOCCER_API_KEY = zakanda.settings.XMLSOCCER_API_KEY
global_use_demo = zakanda.settings.xmlsoccer_demo
global_days = 40
logger = logging.getLogger(__name__)

# TODO There are also summer competitions (MLS, Sweden) the season of which is only one year string and not two. Notice
# the comment regarding these leagues in xmlSoccer API:
# Bear in mind that as more leagues are added, we now see some leagues that do not follow
# the "traditional" cross-year strategy. The American "Major league" and the Swedish "Allsvenskan" is two examples
# of this, as they start in the beginning of the year and end in the end of the year. Despite of this, they too follow
# the same seasonDateString rules. So the 2013 season of the American "Major League" will need the input: 1314

# Other APIs might use a different convention for this. So maybe the season field must become xmlSoccer_season?
# Or I can use this convention for all "summer" competitions TODO

# TODO NOW Create Friendly competitions


def dummy_view():
    # for unused urls
    return


def get_competition_season_type(competition_sid, competition_sname, season):
    # todo xmlsoccer get type from manually created list
    default_type = games.models.CompetitionSeason.winter
    return default_type


def get_leagues_and_countries(sport_name, seasons, source=get_native_source):
    """
    allowed xmlsoccer call every 3600 seconds
    Call to leagues contains also the country to which the league belongs
    There is no get_countries endpoint

    :param seasons: Season queryset or list of season objects

    # Have in mind that in xmlsoccer get leagues you don't define season. You get all leagues.
    # But a league could not be valid for the season that you will create it for. This is not a big
    # issue since any call for teams or events for it will return nothing. But they will exist in the db.
    # AN isues could be the id and the name of these leagues. For example PremierLeague could have sid 1 for 16/17
    # but sid 2 for 11/12. This can;t be the case for xmlsoccer since the leagues are unique, not identified
    # by a season.

    We get all the leagues that the api currently supports and so they correspond to the current season. But the api
    doesn't return the season. The season for which the competition_seasons will be created must be explicitly given as
    argument.
    But if the seasons argument is a tuple of seasons then we will create competition_seasons not only for the current
    season, but also for all given seasons. This is fine, if the api sids and snames  were the same for
    the previous seasons and also that these leagues were existing in the api for the previous seasons

    It can be run at any point in time. It makes changes only if it is necessary
    """
    # TODO leagues for previous seasons just have this in mind

    if not isinstance(source, games.models.Source):
        source = source()
    logger.debug("GetAllLeagues, calling api...")
    if not source:
        return [], []
    if not seasons or not sport_name:
        logger.warning('Needed argument has no value, no api call will be made!')
        return [], []

    xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
    leagues = xmlsoccer.call_api(method='GetAllLeagues')

    pre_countries = []
    pre_competitions = []
    distinct_countries = defaultdict(int)
    pre_country_per_country = {}
    for league in leagues:
        country_sname = league.get('Country')
        competition_sid = league.get('Id')
        competition_sname = league.get('Name')
        logger.debug("%s, competition_sid: %s, country_sname: %s, in response", competition_sname,
                     competition_sid, country_sname)

        distinct_countries[country_sname] += 1
        if distinct_countries[country_sname] == 1:
            # notice: a pre_country can appear more than one times since a country might be connected
            # with many competitions (super league, football league etc.). This is not an issue
            # since get_or_create is applied when you create zakanda models from pre_models
            pre_country = data_sources.pre_models.PreCountry(source=source, sname=country_sname, sid=None)
            pre_country_per_country[country_sname] = pre_country
            pre_countries.append(pre_country)  # collect only the distinct pre_countries
        else:
            pre_country = pre_country_per_country[country_sname]

        comp_seas_utils = []
        for season in seasons:
            # xmlsoccer doesn't support competition season specific sids and snames so we use the competition specific
            # attributes for them.
            competition_season_type = get_competition_season_type(competition_sid, competition_sname, season)
            comp_seas_util = data_sources.pre_models.CompetitionSeasonUtil(season=season, competition_season_sid=None,
                        competition_season_sname=competition_sname, competition_season_type=competition_season_type)
            comp_seas_utils.append(comp_seas_util)

        pre_competition = data_sources.pre_models.PreCompetition(
            source=source, sname=competition_sname, sid=competition_sid, sport_name=sport_name,
            competition_season_utils=comp_seas_utils, pre_country=pre_country)
        pre_competitions.append(pre_competition)
    return pre_countries, pre_competitions


# From xmlSoccer API documentation:
# As of August 2013, it is now possible to get the current season by simply passing an empty string ("") as
# seasonDateString parameter. Bear in mind that as more leagues are added, we now see some leagues that do not follow
# the "traditional" cross-year strategy. The American "Major league" and the Swedish "Allsvenskan" is two examples
# of this, as they start in the beginning of the year and end in the end of the year. Despite of this, they too follow
# the same seasonDateString rules.
# So the 2013 season of the American "Major League" will need the input: 1314
def get_all_teams_by_league_and_season(season_names='All', competition_ids='All', sport_name='Football', source=get_native_source):
    # TODO CompetitionInfo model. It must be updated to support the new CompetitionInfo model
    """
    allowed xmlsoccer call every 3600 seconds (for a specific league)
    gets the teams for the given competitions from the api, and connect them to the competition_seasons defined by the
    given seasons and competitions
    arguments season and competition names must be tuples of names or "All". The api will be polled for teams of these
    competitions. Further actions must be taken for the case of change in the id or name of a team of a source

    It can run at any point in time. It makes changes (create, delete entities etc.) if it is necessary
    """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.debug("GetAllTeamsByLeagueAndSeason, calling api...")
    if not source:
        return []
    if not season_names or not competition_ids:
        logger.warning('Api Call to get teams will not be made since no seasons or competitions were defined')
        return []
    # distinct_competitions = models.Competition.objects.order_by('name').distinct('name')
    xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
    xmlns = '{http://xmlsoccer.com/Team}'
    competition_seasons = zakanda.db.get_competition_season_list_from(competition_ids, season_names)
    # teams = []
    # xml_teams = []
    # team_info_list = []
    pre_teams = []
    for competition_season in competition_seasons:
        logger.info("calling api for %s teams", competition_season)
        try:
            competition_info = competition_season.infos.all().filter(source=source).latest()
            competition_sid = competition_info.sid
            seasonDateString = utils.make_season_date_string_from(competition_season.season)
            xml_teams = xmlsoccer.call_api(method='GetAllTeamsByLeagueAndSeason', league=competition_sid, seasonDateString=seasonDateString)
            for xml_team in xml_teams:
                team_sid = xml_team.get(xmlns+'Team_Id')
                team_sname = xml_team.get(xmlns+'Name')
                pre_team = data_sources.pre_models.PreTeam(source=source, sname=team_sname, sid=team_sid,
                                                           competition_season=competition_season, sport_name=sport_name)
                pre_teams.append(pre_team)
                # if team_sid and team_sname:
                #     team, team_created, team_info, team_info_created = zakanda.db.create_team_tree(
                #         gname=team_sname, source=source, sname=team_sname, sid=team_sid, competition_season=competition_season
                #     )

        except games.models.CompetitionSeasonInfo.DoesNotExist:
            logger.warning("The competition_season '%s' doesn't exist in the db", competition_season)
    return pre_teams


def get_odds_by_event_sid_api_call(event_sids, source=get_native_source):
    """ allowed xmlsoccer call every 3600 seconds (for a specific event) """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("GetAllOddsByFixtureMatchId, calling api...")
    pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = [], [], [], [], []
    if not source:
        return pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups
    if not event_sids:
        logger.info("There are no event sids to process!")
        return pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups

    xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
    for event_sid in event_sids:
        odds = xmlsoccer.call_api(method='GetAllOddsByFixtureMatchId', fixtureMatch_Id=event_sid)
        for odd in odds:
            # response_event_sid = odd.get('FixtureMatch_Id')
            # event = games.models.Event.latest_event_from_sid(response_event_sid, source=source)
            bookmaker_name = odd.get('Bookmaker')
            # The timestamp returned is in GMT (utc offset is 0)
            source_timestamp = odd.get('UpdatedDate')
            source_timestamp_datetime = parser.parse(source_timestamp)
            source_timestamp_utc = source_timestamp_datetime.replace(tzinfo=pytz.UTC)
            market_type = odd.get('Type')
            if market_type == '1X2':
                home = odd.get('HomeOdds')
                draw = odd.get('DrawOdds')
                away = odd.get('AwayOdds')

                pre_winner = data_sources.pre_models.PreWinnerOdd(
                    event_sid, source, bookmaker_name, None, source_timestamp_utc, market_type, home, draw, away)
                pre_winners.append(pre_winner)

            elif market_type == 'Over/Under':
                threshold = 2.5
                under = odd.get('HomeOdds')
                over = odd.get('AwayOdds')

                pre_ovun = data_sources.pre_models.PreOverUnderOdd(
                    event_sid, source, bookmaker_name, None, source_timestamp_utc, market_type, over, under, threshold)
                pre_ovuns.append(pre_ovun)

            elif market_type == 'Double Chance':
                home_draw = odd.get('HomeOdds')
                draw_away = odd.get('DrawOdds')
                away_home = odd.get('AwayOdds')

                pre_dc = data_sources.pre_models.PreDoubleChanceOdd(
                    event_sid, source, bookmaker_name, None, source_timestamp_utc, market_type, home_draw, draw_away, away_home)
                pre_dcs.append(pre_dc)

            elif market_type == 'Handicap':
                home = odd.get('HomeOdds')
                draw = odd.get('DrawOdds')
                away = odd.get('AwayOdds')
                # TODO NOW does the handicap value refer to the home team?
                threshold = odd.get('Handicap')
                threshold = float(threshold)

                pre_hd = data_sources.pre_models.PreHandicapOdd(
                    event_sid, source, bookmaker_name, None, source_timestamp_utc, market_type, home, draw, away, threshold)
                pre_hds.append(pre_hd)

            # elif market_type == 'Asian Handicap':
            #     home = odd.get('HomeOdds')
            #     away = odd.get('AwayOdds')
            #     thresholds = odd.get('Handicap')
            #     asian_handicap_odd, asian_handicap_offer, asian_handicap_offer_odd, ah_tree_created = \
            #         create_asian_handicap_offer_tree(event, bookmaker_name, source_timestamp_utc_datetime, home, away,
            #                                          thresholds, source=global_xmlsoccer)

            else:
                unsup = data_sources.pre_models.PreUnsupported(event_sid, source, bookmaker_name, None, source_timestamp_utc, market_type)
                unsups.append(unsup)
    return pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups


def create_pre_events(fixtures, source=get_native_source):
    """
    The competition seasons for the response's events must already exist in the db
    """
    if not isinstance(source, games.models.Source):
        source = source()
    if not source:
        return []
    pre_events = []
    competition_seasons = defaultdict(int)
    for event in fixtures:
        event_sid = event.get('Id')
        event_date = event.get('Date')
        competition_sname = event.get('League')
        event_round = event.get('Round')    # Some events might not have round (euro knock out) so round is not necessary
        if not event_round:
            event_round = None
        home_team_id = event.get('HomeTeam_Id')
        home_team_name = event.get('HomeTeam')
        away_team_id = event.get('AwayTeam_Id')
        away_team_name = event.get('AwayTeam')
        # The future events don't have a time attribute
        # event_time = event.get('Time')

        if event_sid and event_date and competition_sname and home_team_id and away_team_id and competition_sname:
            # YYYY-MM-DDThh:mm:ssTZD (1997-07-16T19:20:30+01:00) The format that the xmlSoccer API returns
            event_datetime = parser.parse(event_date)
            event_datetime = event_datetime.astimezone(pytz.utc)  # I used to save them with their tzinfo but not in utc
            winter_season_name, summer_season_name = zakanda.utils.season_names_from_datetime(event_datetime)
            season = zakanda.utils.season_from_season_name(winter_season_name)
            home_team, away_team = None, None
            if season:
                competition_season = zakanda.db.get_competition_season_from(competition_sname, source, season)
                competition_seasons[competition_season] += 1
                try:
                    home_team = games.models.TeamInfo.objects.filter(sid=home_team_id, sname=home_team_name, source=source).latest().team
                except games.models.TeamInfo.DoesNotExist:
                    logger.warning("Team Info for team %s [sid %s] of %s doesn't exist. Event tree won't be created", home_team_name, home_team_id, competition_sname)
                    # continue
                try:
                    away_team = games.models.TeamInfo.objects.filter(sid=away_team_id, sname=away_team_name, source=source).latest().team
                except games.models.TeamInfo.DoesNotExist:
                    logger.warning("Team Info for team %s [sid %s] of %s doesn't exist. Event tree won't be created", away_team_name, away_team_id, competition_sname)
                    # continue

                # if home_team and away_team:
                pre_event = data_sources.pre_models.PreEvent(
                    source=source, sid=event_sid, utc_date=event_datetime, home_team=home_team, away_team=away_team,
                    competition_season=competition_season, event_round=event_round)
                pre_events.append(pre_event)

            else:
                logger.warning("Event wasn't created because the season %s doesn't exist in the db", season)
        else:
            logger.warning("Event wasn't created because the api response doesn't contain all the necessary data")
    for k, v in competition_seasons.iteritems():
        logger.info("response contained %s valid events for %s", v, k)  # events that have sll the necessary data
    return pre_events


# TODO I have to use the timezone.activate() for each user in order to present aware utc datetimes to the end's user timezone
# TODO Get the fixtures for the whole season
@job
def get_fixtures_by_date_interval(start_date_string, end_date_string, source=get_native_source):
    """
    The date format that the xmlSoccer API expects is (2011-04-03 17:00) in CET timezone (Europe/London)
    """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("GetFixturesByDateInterval, calling api...")
    if not source:
        return []
    xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
    fixtures = xmlsoccer.call_api(method='GetFixturesByDateInterval', startDateString=start_date_string, endDateString=end_date_string)
    # created_events, event_infos, created_event_sids = parse_fixtures(fixtures)
    pre_events = create_pre_events(fixtures, source)

    # markets_creation.create_initial_markets(created_events, source)
    # logger.info("%s event trees created", len(created_event_sids))

    # context = {
    #     'events': events,
    #     'event_infos': event_infos,
    #     'now_in_tz_formatted': start_date_string,
    #     'now_plus_delta_in_tz_formatted': end_date_string,
    #     'fixture': fixture
    # }
    # return render(request, 'xmlsoccerParser/Future_Events.html', context)
    # return created_event_sids
    return pre_events


@job
def get_fixtures_by_league_and_season(competition_sname_sid, season, source=get_native_source):
    """
    xmlsoccer expects the seasonDateString in the format 1516, 1617 etc. For summer or whole year leagues the current
    year is the first one for example for EURO 2016 the seasonDateString is 1617.
    If we want to get the fixtures for many comps its better to make the loop outside of the function and put it in
    the queue with each iteration since it is a long enough task by itself

    season: it can be either season instance or season name string
    competition_sname_sid: it can be either the competition xmlsoccer name or the xmlsoccer id
    """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("GetFixturesByLeagueAndSeason, calling api...")
    if not source:
        return []
    if not competition_sname_sid or not season:
        logger.warning('no sname/sid or season were given, get fixtures call will not be made')
        return []
    xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
    seasonDateString = utils.make_season_date_string_from(season)
    fixtures = xmlsoccer.call_api(method='GetFixturesByLeagueAndSeason', seasonDateString=seasonDateString, league=competition_sname_sid)

    pre_events = create_pre_events(fixtures, source)
    # events, event_infos, created_event_sids = parse_fixtures(fixtures)
    # markets_creation.create_initial_markets(events, source)
    # logger.info("%s event trees created", len(created_event_sids))
    # return created_event_sids
    return pre_events


def create_result_from_goals(home_goals, away_goals, result_type):
    result, result_created = games.models.Result.objects.get_or_create(
        # If there was no final=False argument an existing one which had final=True was used. It does so due to the
        # way the get_or_create works. First it makes a try to find an entry with the arg that you defined. So if
        # you don't define a final arg it will search without it.
        home_goals=home_goals, away_goals=away_goals, minute=90, type=result_type, final=False
    )
    # print('FT result_created', result_created)
    return result


def goals_from_xmlsoccer_goal_details_string(goal_details, minute_threshold, splitter):
    """
    the format is: 84': Iker Muniain;45': Ander Iturraspe;38': Aymeric Laporte;
    if there is a goal in added time (90+3) then it is marked in response as if it was in 90' with no info about the
    added time, so I collect all goals < 90'
    """
    splitted = goal_details.split(splitter)
    goal_minutes = []
    for string in splitted:
        if string != '':
            goal_minute = int(string.split(':')[0].strip("'"))
            goal_minutes.append(goal_minute)
    goal_minutes_ar = np.asarray(goal_minutes)
    # print(goal_minutes_ar)
    full_time_goals = len(goal_minutes_ar[goal_minutes_ar <= minute_threshold])
    return full_time_goals


def extract_goals(home_goal_details, away_goal_details):
    logger.debug("calculating full time result...")
    # TODO NOW results, handle the case that there are no goal_details. Empty variables that is? In this case I must not
    # process the event. I must manually edit a full_time result. I mark them as 'No goal details'
    if home_goal_details == 'No goals':
        ft_home_goals = 0
    else:
        ft_home_goals = goals_from_xmlsoccer_goal_details_string(home_goal_details, 90, ';')
    if away_goal_details == 'No goals':
        ft_away_goals = 0
    else:
        ft_away_goals = goals_from_xmlsoccer_goal_details_string(away_goal_details, 90, ';')
    return ft_home_goals, ft_away_goals


def extract_result(home_goal_details, away_goal_details, result_type=games.models.Result.ft_result):
    # if not event.results.filter(type=decision_type_result):
    ft_home_goals, ft_away_goals = extract_goals(home_goal_details, away_goal_details)
    ft_result = create_result_from_goals(ft_home_goals, ft_away_goals, result_type=result_type)
    return ft_result


def extract_pre_results(event, fetched_status, home_goals, away_goals, home_goal_details, away_goal_details, source=get_native_source):
    """ Extracts the results (pre_results) of this event from the response data. If the response is a extra time
       result, then 2 pre_results will be created. One et_result and one ft_result. The ft_result will be extracted
       from the goal details string """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.debug("extracting pre result from data: %s, %s, %s, %s, %s, %s, %s", event, fetched_status, home_goals, away_goals, home_goal_details, away_goal_details, source)
    if not source:
        return []
    # if event.home_team.generic_name == "Aberdeen":  # Just for debugging the "void" case
    #     result_status = games.models.Event.postponed
    void_event_statuses = games.models.Event.void_event_statuses
    finished_event_statuses = games.models.Event.finished_event_statuses
    # ft_result = None
    # related_bet_events = []

    pre_results = []  # the pre_results extracted from the response item for a specific event

    if isinstance(fetched_status, (int, long)):
        logger.warning("Live result was parsed")
        # TODO LIVE MATCHES handle live score
        pass

    elif fetched_status in finished_event_statuses:
        if fetched_status == games.models.Event.finished:
            logger.debug('full time result parsed')
            zakanda_result_type = games.models.Result.ft_result
            minute = 90
            is_final = True
            pre_result = data_sources.pre_models.PreResult(
                event, fetched_status, home_goals, away_goals, zakanda_result_type, minute, is_final, source)
            pre_results.append(pre_result)

        elif fetched_status == games.models.Event.finished_aet:
            logger.debug('aet result parsed')
            zakanda_result_type = games.models.Result.et_result
            minute = 120
            is_final = True
            pre_result = data_sources.pre_models.PreResult(
                event, fetched_status, home_goals, away_goals, zakanda_result_type, minute, is_final, source)
            pre_results.append(pre_result)

            # extract the ft_result from the goal details string
            ft_home_goals, ft_away_goals = extract_goals(home_goal_details, away_goal_details)
            zakanda_result_type = games.models.Result.ft_result
            minute = 90
            is_final = False
            pre_result = data_sources.pre_models.PreResult(
                event, fetched_status, ft_home_goals, ft_away_goals, zakanda_result_type, minute, is_final, source)
            pre_results.append(pre_result)

        elif fetched_status == games.models.Event.finished_ap:
            logger.debug('ap result parsed')
            zakanda_result_type = games.models.Result.pen_result
            minute = 120
            is_final = True
            pre_result = data_sources.pre_models.PreResult(
                event, fetched_status, home_goals, away_goals, zakanda_result_type, minute, is_final, source)
            pre_results.append(pre_result)

            ft_home_goals, ft_away_goals = extract_goals(home_goal_details, away_goal_details)
            zakanda_result_type = games.models.Result.ft_result
            minute = 90
            is_final = False
            pre_result = data_sources.pre_models.PreResult(
                event, fetched_status, ft_home_goals, ft_away_goals, zakanda_result_type, minute, is_final, source)
            pre_results.append(pre_result)

        else:
            logger.error("pre_result can not be extracted for result with status: %s", fetched_status)
            pass

    elif fetched_status in void_event_statuses:
        logger.warning("void result parsed")
        zakanda_result_type = fetched_status
        minute = 0
        is_final = True
        pre_result = data_sources.pre_models.PreResult(
            event, fetched_status, home_goals, away_goals, zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

    else:
        logger.error("unsupported status: %s for fetched result", fetched_status)
        pass

    return pre_results


def parse_result_fixture(item):
    event_status = item.get('Time')
    home_goals = item.get('HomeGoals')
    away_goals = item.get('AwayGoals')
    home_goal_details = 'No goals'
    away_goal_details = 'No goals'
    if home_goals != '0':
        home_goal_details = item.get('HomeGoalDetails')
        if not home_goal_details:
            # just in case that there are no goal details even if the event has some goals.
            # Currently I don't do anything for this case
            home_goal_details = 'No goal details'
    if away_goals != '0':
        away_goal_details = item.get('AwayGoalDetails')
        if not away_goal_details:
            away_goal_details = 'No goal details'
    return event_status, home_goals, away_goals, home_goal_details, away_goal_details


def get_results(events, source=get_native_source):
    if not isinstance(source, games.models.Source):
        source = source()
    # Notice that with the GetFixtureMatchByID method if you request past events we got basic results not the advanced
    # historic statistics of the xmlsoccer API that can be accessed from the "GetHistoricalMatches..." methods
    logger.info("GetFixtureMatchByID, getting results for %s events...", len(events))
    if not source:
        return []
    pre_results = []
    if events:
        xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
        for event in events:
            sids = event.get_sids(source_name=source.name)
            if not sids:
                continue
            for sid in sids:
                fixture = xmlsoccer.call_api(method='GetFixtureMatchByID', Id=sid)
                logger.debug('sid: %s', sid)
                # There is only one match in the fixture and also the <AccountInformation> tag
                for item in fixture:
                    # do things only if the item is not the <AccountInformation> which has no children
                    if item:
                        event_status, home_goals, away_goals, home_goal_details, away_goal_details = parse_result_fixture(item)
                        event_status, home_goals, away_goals = utils.make_integers(event_status, home_goals, away_goals)
                        event_pre_results = extract_pre_results(event, event_status, home_goals, away_goals,
                                                                home_goal_details, away_goal_details, source)
                        # logger.debug("pre_results %s", event_pre_results)
                        pre_results.extend(event_pre_results)
    return pre_results


def get_league_standings(request, xmlSoccer_league_id):
    xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
    standings = xmlsoccer.call_api(
        method='GetLeagueStandingsBySeason',
        seasonDateString='1415',
        league=xmlSoccer_league_id
    )
    namespace = '{http://xmlsoccer.com/LeagueStanding}'
    team_names = []
    for entry in standings:
        team_name = entry.get(namespace+'Team')
        if team_name is not None:
            team_names.append(team_name)
    context = {'team_names': team_names}
    return render(request, 'xmlSoccerParser/xmlSoccer_Teams.html', context)