# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import json
import vcr
import os
from collections import defaultdict
import constants
import games.models
import games.naming
import gutils.utils
import pytz
import sportmonks
import utils
import zakanda.db
import zakanda.settings
import zakanda.utils
from data_sources import pre_models
from dateutil import parser
from django.http import HttpResponse
from django.core.cache import cache  # this is the default cache

logger = logging.getLogger(__name__)
api_key = zakanda.settings.sportmonks_api_key


def seasons_special_treatment(season_string):
    # they have been corrected by sportmonks
    if season_string.find("-") != -1:
        logger.warning("season special treatment for season string: %s", season_string)
        season_string = season_string.replace("-", "/")

    if season_string == "2018/2018":
        logger.warning("season special treatment for season string: %s", season_string)
        season_string = "2017/2018"

    if season_string == "2017/2017":
        logger.warning("season special treatment for season string: %s", season_string)
        season_string = "2016/2017"

    # Notice that there is also a wrong season 2010/2012 for Euro Qualification. This season will be
    # invalid and not going to be created: corrected to 2012
    return season_string


def is_in_problematic_teams(sid):
    # todo sportmonks fix
    special_sids = [3191, 8348, 2794, 3383, 4754, 9389, 16652, 16674, 23362, 960, 7561, 7627, 12234, 2946, 3378, 13322,
                    13328, 28156, 28238, 2971, 2604, 838, 6315, 3608, 9335, 10840, 9698,
                    9896, 30619, 7382,
                    6549, 9650, 17558, 526, 9882, 11372, 28000, 11019, 680, 609, 19652, 2807, 3021, 6780, 21089, 3684,
                    5310, 62,
                    10497, 886, 27539, 9173, 15306, 15320, 91, 2569, 6735, 6844, 6931, 7780, 8463, 9289, 9502, 9570,
                    2274,
                    11036, 2513, 12882, 3467, 95, 862, 15975, 58086, 58087, 58088, 76145, 8013, 9150, 476, 9908, 16184,
                    29743,
                    15185, 6027, 16772, 696, 8180, 9804, 25101, 9019, 7812, 13665, 10797, 8730, 2652, 16815,
                    9266,
                    12217, 5995, 15016, 1439, 2690, 5664, 6954, 7273, 7361, 7983, 8032, 8106, 10106, 14732, 18296, 904,
                    3605,
                    12317, 6483, 111, 3736, 123, 18136, 131804, 15399, 6497, 60004, 60043, 6201, 17812, 15691, 16965,
                    134030]
    # [579, 1820, 260, 1232, 1294, 910, 1126]  # excluded from list since they are correct
    if sid in special_sids:
        return True
    return False


def check_problematic_teams(sid, sname):
    """ There are some teams that belong to competition_seasons of more than countries (excluding International
    competitions). These teams should have been distinct teams.  """
    # todo high manually remove the teams from the wrong competitions.
    if is_in_problematic_teams(sid):
        logger.warning("team special treatment for team %s %s", sname, sid)
        # so that the pre_team will be invalid and team will not be created
        return None, sname

    if not sname:
        # there are 21 teams that have no name. I create them just to be able to update them in the future
        sname = sid

    return sid, sname


def countries_special_treatment(name):
    if name.isspace():
        logger.warning("country special treatment for country %s", name)
        # country with sid 765143 has the name "\n    " and no seasons. I make it invalid
        return None
    return name


def get_competition_season_type(season):
    """ in sportmonks we get the seasons for which competitions exists. So we can determine the type of a
    competition_season by the season name. If it is 2017 its a summer one. If it's 16/17 it's a winter one.
    :param season: season object """
    default_type = games.models.CompetitionSeason.winter
    try:
        season_name = season.name
        if season_name.find("/") == -1:
            return games.models.CompetitionSeason.summer
        return default_type
    except Exception as e:
        return default_type


def parse_sport(meta):
    """ notice that it used to be 'sport' instead of 'sports' and a dictionary instead of a list """
    sport_sids = []
    try:
        sport_sid = meta.get('sport').get('id')
    except Exception as e:
        sports = meta.get('sports')
        if len(sports) != 1:
            logger.info('number of sports returned is: %s', len(sports))
        for sport in sports:
            sport_sid = sport.get('id')
            sport_sids.append(sport_sid)
            logger.debug('sport_sid: %s', sport_sid)
    return sport_sids


# @vcr.use_cassette('../sportmonks/vcr_cassetes/countries_all.yml', filter_query_parameters=['api_token'])
def countries_flags(source=utils.get_native_source):
    if not isinstance(source, games.models.Source):
        # If I used source=native_source() or if native_source was a global variable then
        # during db initialization (running command initialize) you would get an error since
        # it gets its value when the database is empty.
        source = source()
    logger.info("getting countries from source %s...", source)
    if not source:
        return
    data, meta, status_code = sportmonks.countries.all()
    if not data:
        # if the status code is not 200 data and meta are None
        return

    pre_countries = []
    for item in data:
        try:
            country_sid = item.get('id')
            # logger.debug('country_sid: %s', country_sid)
            country_sname = item.get('name')
            # logger.debug('country_sname: %s', country_sname)
            extra = item.get('extra')
            # logger.debug('extra: %s', extra)
            # leagues = item.get('leagues').get('data')
            # logger.debug('leagues: %s', leagues)
            try:
                fifa_code = extra.get('fifa')  # some countries might lack extra information
                flag = extra.get('flag')
            except AttributeError:
                fifa_code = None
                flag = None
            pre_country = pre_models.PreCountry(source=source, sname=country_sname, sid=country_sid,
                                                fifa_code=fifa_code, flag=flag)
            pre_countries.append(pre_country)
        except Exception as e:
            logger.data_error('%s', e)
            continue

    # Reunion, Cote d'Ivoire, Sao Tome e Principe, Niue, Curacao: Unicode characters replaced with ASCII
    for pre_country in pre_countries:
        pre_country.internal_map()
        country = pre_country.existing_entity
        try:
            # logger.debug('flag type: %s, flag: %s', type(pre_country.flag), pre_country.flag)
            with open('../static/img/flags/{}.svg'.format(country.name), 'w') as svg_file:
                svg_file.write(pre_country.flag)
                # json.dump(pre_country.flag, svg_file, indent=4)
        except Exception as e:
            logger.warning('country sname: %s, %s', pre_country.sname, e)
            continue


def get_leagues_and_countries(source=utils.get_native_source):
    """
    Sportmonks uses an sgname convention (a global name for a competition). It doesn't have a name for each
    competition season. Zakanda supports both an sgname convention and a season specific naming convention.
    So for sportmonks the zakanda season specific competition names are the sgname.
    This means that if there is a change in the sgname all the season specific names will be updated
    or new competitionSeasonInfos will be created for all seasons.
    :param source:
    :return:
    """
    if not isinstance(source, games.models.Source):
        # If I used source=native_source() or if native_source was a global variable then
        # during db initialization (running command initialize) you would get an error since
        # it gets its value when the database is empty.
        source = source()
    logger.info("getting leagues and countries from source %s...", source)
    if not source:
        return [], []
    data, meta, status_code = sportmonks.countries.all(include='leagues.seasons')
    if not data:
        # if the status code is not 200 data and meta are None
        return [], []
    # with open('sportmonks/response_texts/aws_01.txt', 'w') as outfile:
    #     json.dump(meta, outfile, indent=4)
    #     json.dump(data, outfile, indent=4)

    pre_countries, pre_competitions = [], []

    try:
        # Notice that only the first supported sport will be processed (currently this is is acceptable since we only
        # support football and so the first supported sport will always be football)
        sport_sids = parse_sport(meta)
        sports = []
        for sport_sid in sport_sids:
            sport = games.models.Sport.by_sid(sid=sport_sid, source=source)
            if not sport:
                logger.info("Sport contained in the response with sid {} is not supported".format(sport_sid))
                continue
            sports.append(sport)
        if not sports:
            logger.error("No supported sport in the response")
            return [], []
        football_gname = games.naming.sport_names.get('football', None)
        football = games.models.Sport.objects.get(name=football_gname)
        if football not in sports:
            logger.info("Football is not in response")
            return [], []
        # logger.debug("Trying to get sport from source: %s and sid: %s", source, sport_sid)
        sport_gname = football_gname
        for item in data:
            try:
                country_sid = item.get('id')
                # logger.debug('country_sid: %s', country_sid)
                country_sname = item.get('name')
                # logger.debug('country_sname: %s', country_sname)
                extra = item.get('extra')
                # logger.debug('extra: %s', extra)
                leagues = item.get('leagues').get('data')
                # logger.debug('leagues: %s', leagues)
                try:
                    fifa_code = extra.get('fifa')  # some countries might lack extra information
                except AttributeError:
                    fifa_code = None
            except Exception as e:
                logger.data_error('%s', e)
                continue
            pre_country = pre_models.PreCountry(source=source, sname=country_sname, sid=country_sid, fifa_code=fifa_code)
            pre_countries.append(pre_country)
            for league in leagues:
                try:
                    # sportmonks uses sgname for leagues. I use this sgname as an sname (comp_season_specific name)
                    competition_sname = league.get('name')
                    # logger.debug('competition_sname: %s', competition_sname)
                    sid = league.get('id')
                    # logger.debug('sid: %s', sid)
                    seasons = league.get('seasons').get('data')
                    # logger.debug('seasons: %s', seasons)
                except Exception as e:
                    logger.data_error('%s', e)
                    continue
                competition_season_utils = []
                # comp_seas_sids = []
                for season in seasons:
                    try:
                        season_name = season.get('name')
                        # logger.debug('season_name: %s', season_name)
                        # season_name = seasons_special_treatment(season_name)
                        competition_season_sid = season.get('id')
                        # logger.debug('competition_season_sid: %s', competition_season_sid)
                        is_current_season = season.get('is_current_season', False)
                        # logger.debug('is_current_season: %s', is_current_season)
                    except Exception as e:
                        logger.data_error('%s', e)
                        continue
                    # comp_seas_sids.append(competition_season_sid)
                    zak_season_name = games.models.Season.zakandify_season_string(season_name)
                    season = zakanda.utils.season_from_season_name(zak_season_name)
                    competition_season_type = get_competition_season_type(season)
                    competition_season_util = pre_models.CompetitionSeasonUtil(season, competition_season_sid, competition_sname, competition_season_type)
                    competition_season_utils.append(competition_season_util)
                # logger.debug("competition season sids: %s", comp_seas_sids)
                pre_competition = pre_models.PreCompetition(
                    source=source, sname=competition_sname, sid=sid, sport_name=sport_gname,
                    competition_season_utils=competition_season_utils, pre_country=pre_country)
                pre_competitions.append(pre_competition)

    except Exception as e:
        logger.error('%s Unexpected problem with sportmonks.countries.all from source %s', e, source)
    logger.info("%s pre countries and %s pre competitions were created", len(pre_countries), len(pre_competitions))
    return pre_countries, pre_competitions


def get_name_of_same_named_teams(sname, sid):
    """ Sportmonks has some teams with the same name that are actually different teams. Zakanda assumes unique name
    for teams.

    Initially I had identified these 6 teams so I manually applied different names with this function. Now there
    is a global treatment of same named teams so this can be omitted.

    Notice that there are also 3 more teams that have the same name and have a different id but they are
    actually the same team. I don't do anything for these teams. They will be stored in the db as different teams
    with different names.
    These teams are are Vaduz (Liechtenstein 1514, 13771) plays in Swiss football league,
    Geel (Belgium 7079, 2784), FH (Iceland 10420, 439)"""

    if sname == 'Zamora':
        if sid == 9404:
            return 'Zamora FC'  # Venezuela
        elif sid == 26394:
            return 'Zamora CF'  # Spain
        else:
            logger.error('Sportmonk ids for same named teams "%s" have changed', sname)
            return sname
    elif sname == 'Atromitos':
        if sid == 9849:
            return 'Atromitos A.'  # Greece
        elif sid == 2953:
            return 'Atromitos Yeroskipou'  # Cyprus
        else:
            logger.error('Sportmonk ids for same named teams "%s" have changed', sname)
            return sname
    elif sname == 'Atromitos/H.':  # sid 9842
        return None
    elif sname == 'Libertas':
        if sid == 11019:
            return 'Libertas Novska'  # Croatia
        elif sid == 19357:
            return 'A.C Libertas'  # San Marino
        else:
            logger.error('Sportmonk ids for same named teams "%s" have changed', sname)
            return sname
    elif sname == 'Irtysh':
        if sid == 4000:
            return 'Irtysh Omsk'  # Russia
        elif sid == 11058:
            return 'Irtysh Pavlodar'  # Kazakstan
        else:
            logger.error('Sportmonk ids for same named teams "%s" have changed', sname)
            return sname
    elif sname == 'Linense':
        if sid == 7812:
            return 'Atletico Linense'  # Brazil
        elif sid == 26006:
            return 'Real Balompedica Linense'  # SPain
        else:
            logger.error('Sportmonk ids for same named teams "%s" have changed', sname)
            return sname
    elif sname == 'Sorrento':
        if sid == 10773:
            return 'Sorrento FC'  # Australia
        elif sid == 24305:
            return 'F.C. Sorrento'  # Italy
        else:
            logger.error('Sportmonk ids for same named teams "%s" have changed', sname)
            return sname
    else:
        return sname


def get_teams(season_names='All', competition_ids='All', sport_name='Football', source=utils.get_native_source):
    """
    :param season_names:
    :param competition_ids:
    :param sport_name:
    :param source:
    :return:
    """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("getting teams for seasons: %s and competitions: %s from source %s...", season_names, competition_ids, source)
    if not source:
        return []
    # with open('sportmonks/response_texts/teams_by_seasons_initialize_02__country.txt', 'w') as outfile:
    pre_teams = []
    competition_seasons = zakanda.db.get_competition_season_list_from(competition_ids, season_names)

    counter = -1
    for competition_season in competition_seasons:
        try:
            counter += 1
            # num_teams = competition_season.team_set.count()
            # logger.debug("competition season: %s has %s teams", competition_season, num_teams)
            competition_season_info = competition_season.infos.filter(source=source).latest()
            competition_season_sid = competition_season_info.sid
            logger.debug("getting teams for competition season: %s", competition_season)
            data, meta, status_code = sportmonks.teams.by_season(competition_season_sid, include='country')
            # logger.debug("data: %s, meta:%s, status_code: %s", data, meta, status_code)
            # data, meta, status_code = sportmonks.teams.by_season(competition_season_sid)
            # logger.debug("meta: %s", meta)
            if status_code == 429:
                logger.warning("Maximum number of allowed calls for sportmonks.teams.by_season has been reached!")
                remaining_comp_seasons = competition_seasons[counter:]
                logger.error("No call is made for %s excessive competition seasons", len(remaining_comp_seasons))
                # todo high schedule excessive get_teams calls
                # chunks = gutils.utils.to_chunks(remaining_comp_seasons, constants.calls_limit)
                break
            if not data:
                continue
            # json.dump(data, outfile, indent=4)
            for team in data:
                try:
                    team_sname = team.get('name')
                    team_sid = team.get('id')
                except Exception as e:
                    logger.data_error('%s', e)
                    continue
                # since the teams have already created, I keep reading them
                # team_sid, team_sname = check_problematic_teams(team_sid, team_sname)
                pre_team = pre_models.PreTeam(source=source, sname=team_sname, sid=team_sid,
                                              competition_season=competition_season, sport_name=sport_name)
                pre_teams.append(pre_team)
        except Exception as e:
            logger.error('%s Unexpected problem with sportmonks.teams.by_season for competition_season %s '
                         'from source %s', repr(e), competition_season, source)
            continue
    logger.info("%s pre teams were created", len(pre_teams))
    return pre_teams


def get_events(start_date, end_date, source=utils.get_native_source, **kwargs):
    """ Currently the season is extracted from the event's date and competition's type
    :param kwargs: the keys will become query string parameters """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("getting events from source %s...", source)
    if not source:
        return []
    # with open('sportmonks/response_texts/fixtures_{}-{}.txt'.format(start_date.strftime('%Y-%m-%d'),
    #                                                                 end_date.strftime('%Y-%m-%d')), 'w') as outfile:
    # season is necessary so that the season object is extracted and used
    include = kwargs.get('include', '')
    include = ','.join([include, 'season']) if include else 'season'
    kwargs['include'] = include
    data, meta, status_code = sportmonks.fixtures.by_date_range(start_date=start_date, end_date=end_date, **kwargs)
    # json.dump(data, outfile, indent=4)
    if not data:
        return []
    pre_events = []
    try:
        num_fetched_objects = len(data)
    except:
        num_fetched_objects = None
    num_processed_objects = 0
    try:
        for obj in data:
            num_processed_objects += 1
            try:
                sid = obj.get('id', None)
                time = obj.get('time', dict())
                starting_at = time.get('starting_at', dict())
                event_datetime = get_date(starting_at, 'date_time')
                # custom_timezone = pytz.timezone('Europe/Athens')
                # event_datetime = event_datetime.astimezone(custom_timezone)
                home_team_sid = obj.get('localteam_id', None)
                away_team_sid = obj.get('visitorteam_id', None)
                competition_season_sid = obj.get('season_id', None)
                season_string = obj.get('season', {}).get('data', {}).get('name')
                stage_sid = obj.get('stage_id', None)
                round_sid = obj.get('round_id', None)
                competition_sid = obj.get('league_id', None)
            except Exception as e:
                logger.data_error('%s', e)
                continue

            zak_season_name = games.models.Season.zakandify_season_string(season_string)
            season = zakanda.utils.season_from_season_name(zak_season_name)
            if not season:
                logger.data_error('Could not extract season object from season string: %s', season_string)
                continue

            # todo sportmonks fix
            # if the event involves a problematic team it is not created in order to avoid future problems
            if is_in_problematic_teams(home_team_sid):
                home_team_sid = None
            if is_in_problematic_teams(away_team_sid):
                away_team_sid = None

            competition_seasons = games.models.CompetitionSeason.by_sid(competition_season_sid, source, season)
            try:
                competition_season = competition_seasons.first()  # only one entity exists in the queryset
            except Exception as e:
                logger.warning('%s', e)
                competition_season = None

            home_team = games.models.Team.by_sid(home_team_sid, source)
            away_team = games.models.Team.by_sid(away_team_sid, source)
            pre_event = pre_models.PreEvent(source, sid, event_datetime, home_team, away_team, competition_season)
            pre_events.append(pre_event)
    except Exception as e:
        logger.error('%s Unexpected problem with sportmonks.fixtures.by_date_range %s %s from source %s',
                     e, start_date, end_date, source)
    logger.info("%s event objects were contained in the response", num_fetched_objects)
    logger.info("%s event objects were processed", num_processed_objects)
    logger.info("%s pre events were created", len(pre_events))
    return pre_events


def get_date(obj, date_key, timezone_key='timezone'):
    try:
        date = obj.get(date_key)
        fetched_timezone = obj.get(timezone_key)
    except Exception as e:
        # some of the last update fields are not a json object but a plain json string (without the
        # timezone and date keys). It is just a string describing the date
        logger.debug('%s, last update is a just a string', e)
        date = obj
        fetched_timezone = 'UTC'

    if fetched_timezone != 'UTC':
        # todo support all timezones
        logger.error('fetched timezone %s is not UTC but utc has been used!', fetched_timezone)
    date = parser.parse(date)
    aware_date = date.replace(tzinfo=pytz.UTC)
    return aware_date


class TempMarketType(object):
    def __init__(self, market_type, temp_bookmakers=None, event_sid=None, source=None):
        self.market_type = market_type
        self.temp_bookmakers = temp_bookmakers
        self.event_sid = event_sid
        self.source = source

    def __unicode__(self):
        return '{} num bookmakers: {}'.format(self.market_type, len(self.temp_bookmakers))

    def log(self):
        logger.debug('temp market type obj: %s', self)
        for b_obj in self.temp_bookmakers:
            logger.debug('   temp bookmaker obj: %s', b_obj)
            for o_obj in b_obj.temp_odds:
                logger.debug('    odd obj: %s', o_obj)

    def create_pre_winners(self):
        event_sid = self.event_sid
        source = self.source
        market_type = self.market_type
        temp_bookmakers = self.temp_bookmakers
        home, draw, away, last_update_utc = None, None, None, None
        pre_winners = []
        for temp_bookmaker in temp_bookmakers:
            bookmaker_sid = temp_bookmaker.bookmaker_sid
            bookmaker_name = temp_bookmaker.bookmaker_name
            for temp_odd in temp_bookmaker.temp_odds:
                label = temp_odd.label
                odd_value = temp_odd.value
                last_update_utc = temp_odd.last_update
                if label == '1' or label == 'Home':
                    home = odd_value
                elif label == 'X' or label == 'Draw':
                    draw = odd_value
                elif label == '2' or label == 'Away':
                    away = odd_value
                else:
                    logger.data_error('Unknown sportmonks label %s for %s', label, market_type)
            pre_winner = pre_models.PreWinnerOdd(event_sid, source, bookmaker_name, bookmaker_sid,
                                                 last_update_utc, market_type, home, draw, away)
            pre_winners.append(pre_winner)
        return pre_winners

    def create_pre_over_unders(self):
        event_sid = self.event_sid
        source = self.source
        market_type = self.market_type
        temp_bookmakers = self.temp_bookmakers
        over, under, threshold, last_update_utc = None, None, None, None
        pre_ovuns = []
        for temp_bookmaker in temp_bookmakers:
            bookmaker_sid = temp_bookmaker.bookmaker_sid
            bookmaker_name = temp_bookmaker.bookmaker_name
            per_threshold_odds = dict()
            for temp_odd in temp_bookmaker.temp_odds:
                last_update_utc = temp_odd.last_update
                threshold = temp_odd.total
                label = temp_odd.label
                odd_value = temp_odd.value
                try:
                    per_threshold_odds[threshold]
                except KeyError:
                    per_threshold_odds[threshold] = dict()
                if label == 'Over':
                    per_threshold_odds[threshold]['Over'] = odd_value
                elif label == 'Under':
                    per_threshold_odds[threshold]['Under'] = odd_value
                else:
                    logger.data_error('Unknown sportmonks label %s for %s', label, market_type)

            for threshold, odds_dict in per_threshold_odds.items():
                over = odds_dict.get('Over')
                under = odds_dict.get('Under')
                if threshold != '2.5':
                    # todo NOW more Over/Under thresholds Can I just add them. Check front side
                    continue
                try:
                    threshold = float(threshold)
                except ValueError:
                    threshold = None

                pre_ovun = pre_models.PreOverUnderOdd(
                    event_sid, source, bookmaker_name, bookmaker_sid, last_update_utc,
                    market_type, over, under, threshold)
                pre_ovuns.append(pre_ovun)
        return pre_ovuns

    def create_pre_double_chances(self):
        event_sid = self.event_sid
        source = self.source
        market_type = self.market_type
        temp_bookmakers = self.temp_bookmakers
        pre_dcs = []
        for temp_bookmaker in temp_bookmakers:
            bookmaker_sid = temp_bookmaker.bookmaker_sid
            bookmaker_name = temp_bookmaker.bookmaker_name
            home_draw, draw_away, away_home, last_update = None, None, None, None
            for temp_odd in temp_bookmaker.temp_odds:
                # logger.debug("Double Chance temp_bookmaker.temp_odds: %s", temp_bookmaker.temp_odds)
                label = temp_odd.label
                value = temp_odd.value
                last_update = temp_odd.last_update
                if label == '1X' or label == 'Home/Draw':
                    home_draw = value
                elif label == 'X2' or label == 'Draw/Away':
                    draw_away = value
                elif label == '12' or label == 'Home/Away':
                    away_home = value
                else:
                    logger.data_error('Unknown sportmonks label %s for %s', label, market_type)

            pre_dc = pre_models.PreDoubleChanceOdd(event_sid, source, bookmaker_name, bookmaker_sid, last_update,
                                                   market_type, home_draw, draw_away, away_home)
            pre_dcs.append(pre_dc)
        return pre_dcs

    def create_pre_handicaps(self):
        event_sid = self.event_sid
        source = self.source
        market_type = self.market_type
        temp_bookmakers = self.temp_bookmakers
        pre_hds = []
        for temp_bookmaker in temp_bookmakers:
            bookmaker_sid = temp_bookmaker.bookmaker_sid
            bookmaker_name = temp_bookmaker.bookmaker_name
            temp_handicap_odds = group_by_threshold(temp_bookmaker)

            for hd_odd in temp_handicap_odds:
                pre_hd = pre_models.PreHandicapOdd(
                    event_sid, source, bookmaker_name, bookmaker_sid, hd_odd.last_update,
                    market_type, hd_odd.home, hd_odd.draw, hd_odd.away, hd_odd.threshold)
                pre_hds.append(pre_hd)
        return pre_hds

    def create_pre_unsupported(self):
        event_sid = self.event_sid
        source = self.source
        market_type = self.market_type
        temp_bookmakers = self.temp_bookmakers
        unsupported = []
        for temp_bookmaker in temp_bookmakers:
            bookmaker_sid = temp_bookmaker.bookmaker_sid
            bookmaker_name = temp_bookmaker.bookmaker_name
            unsup = pre_models.PreUnsupported(event_sid, source, bookmaker_name, bookmaker_sid, None, market_type)
            unsupported.append(unsup)
        return unsupported

    def create_pre_markets(self):
        """ Creates the pre_market objects from the parsed and temporarily stored data """
        market_type = self.market_type
        pre_winners, pre_over_unders, pre_dcs, pre_handicaps, pre_unsupported = [], [], [], [], []
        if market_type == '3Way Result':
            pre_winners = self.create_pre_winners()
        elif market_type == 'Over/Under':
            pre_over_unders = self.create_pre_over_unders()
        elif market_type == 'Double Chance':
            pre_dcs = self.create_pre_double_chances()
        elif market_type == '3Way Handicap' or market_type == 'Handicap Result':
            pre_handicaps = self.create_pre_handicaps()
        else:
            pre_unsupported = self.create_pre_unsupported()
        return pre_winners, pre_over_unders, pre_dcs, pre_handicaps, pre_unsupported


class TempBookmaker(object):
    def __init__(self, bookmaker_name, bookmaker_sid, temp_odds=None):
        self.bookmaker_name = bookmaker_name
        self.bookmaker_sid = bookmaker_sid
        self.temp_odds = temp_odds

    def __unicode__(self):
        return '{} num odds: {}'.format(self.bookmaker_name, len(self.temp_odds))


class TempOddValuesObj(object):
    def __init__(self, label, value, last_update, handicap=None, total=None, winning=None):
        self.label = label
        self.value = value
        self.last_update = last_update
        self.handicap = handicap
        self.total = total
        self.winning = winning

    def __unicode__(self):
        return 'label: {} value: {} last_upd: {} handicap: {} total: {} winning: {}'.format(
            self.label, self.value, self.last_update, self.handicap, self.total, self.winning)


class TempHandicap(object):
    def __init__(self, threshold, home=None, draw=None, away=None, last_update=None):
        self.threshold = threshold
        self.home = home
        self.draw = draw
        self.away = away
        # note: each odd value has its own last updated value but I keep only one of them (the first read one)
        self.last_update = last_update

    def __unicode__(self):
        return '{} 1: {} X: {} 2: {}'.format(self.threshold, self.home, self.draw, self.away)


def group_by_threshold_01(temp_odds):
    """ Groups by threshold extracted from the "handicap" field of temp odd """
    temp_handicaps_per_threshold = defaultdict(int)
    for temp_odd in temp_odds:
        try:
            last_update = temp_odd.last_update
            odd_value = temp_odd.value
            choice = temp_odd.label
            threshold = temp_odd.handicap
        except Exception as e:
            logger.data_error('%s', e)
            continue

        try:
            threshold = float(threshold)
        except Exception as e:
            logger.data_error('odd parsing, error on parsing the threshold value from handicap field: %s, %s', threshold, e)
            continue

        if not temp_handicaps_per_threshold[threshold]:
            temp_handicaps_per_threshold[threshold] = TempHandicap(threshold=threshold, last_update=last_update)

        # logger.debug('choice: %s, threshold: %s', choice, threshold)
        if choice == '1':
            temp_handicaps_per_threshold[threshold].home = odd_value
        elif choice == '2':
            temp_handicaps_per_threshold[threshold].away = odd_value
        elif choice == 'X':
            temp_handicaps_per_threshold[threshold].draw = odd_value
        else:
            logger.data_error('odd parsing, unknown sportmonks label: %s', choice)
    # logger.debug('list of temp handicaps: %s', temp_handicaps_per_threshold.values())
    return temp_handicaps_per_threshold.itervalues()


def group_by_threshold_02(temp_odds):
    """ Groups by threshold extracted from the "label" field of temp odd """
    temp_handicaps_per_threshold = defaultdict(int)
    for temp_odd in temp_odds:
        try:
            last_update = temp_odd.last_update
            odd_value = temp_odd.value
            label = temp_odd.label
        except Exception as e:
            logger.data_error('%s', e)
            continue

        label_raw_values = label.split(':')
        label_values = []
        for label_value in label_raw_values:
            label_value = label_value.strip(' ')
            label_values.append(label_value)
        choice = label_values[0]
        # logger.debug('handicap extracted values: %s', label_values)

        try:
            threshold = float(label_values[1])
        except Exception as e:  # ValueError, IndexError, float error if threshold = None
            logger.data_error('odd parsing, error on parsing the threshold value from label field: %s, %s', label, e)
            continue

        if not temp_handicaps_per_threshold[threshold]:
            temp_handicaps_per_threshold[threshold] = TempHandicap(threshold=threshold, last_update=last_update)
        if not temp_handicaps_per_threshold[-threshold]:
            # initialize it here so that we can add the away odd
            temp_handicaps_per_threshold[-threshold] = TempHandicap(threshold=-threshold, last_update=last_update)

        # logger.debug('choice: %s, threshold: %s', choice, threshold)
        if choice == '1':
            temp_handicaps_per_threshold[threshold].home = odd_value
        elif choice == '2':
            temp_handicaps_per_threshold[-threshold].away = odd_value
        elif choice == 'X':
            temp_handicaps_per_threshold[threshold].draw = odd_value
        else:
            logger.data_error('odd parsing, unknown sportmonks label %s', label)
    # logger.debug('list of temp handicaps: %s', temp_handicaps_per_threshold.values())
    return temp_handicaps_per_threshold.itervalues()


def group_by_threshold(temp_bookmaker):
    """ It transforms a list of temp odds to a list (iterator) of temp handicap odds.
        The later groups the odds by threshold so one handicap odd refers to a specific threshold.
        The initial temp odd contains just one odd value (of the home, draw, away)
        for a specific threshold.
        Important:
        If the threshold is extracted from the label field of the temp odd then:
        The correct odds for the [+1 market] are: 1(thr: +1) X(thr: +1) 2(thr: -1) instead of 1(+1) X(+1) 2(+1)
        Meaning that if the choice is 2 and the threshold is +1 this odd refers to the [-1 market].
        So in case of away choice, we must add this odd to the opposite threshold
        But:
        If the threshold is extracted by the threshold field of the temp odd (bet365) then this threshold is
        just one value eg. +1 and its odds refer to the +1 market.
        So in this case the away odd must be added to the same threshold.
    """
    try:
        temp_odds = temp_bookmaker.temp_odds
    except Exception as e:
        return []
    if temp_bookmaker.bookmaker_name == utils.bet365_name:
        temp_handicaps = group_by_threshold_01(temp_odds)
    else:
        temp_handicaps = group_by_threshold_02(temp_odds)
    return temp_handicaps


# def group_by_threshold(temp_odds):
#     temp_handicaps_per_threshold = defaultdict(int)
#     for temp_odd in temp_odds:
#         # logger.debug("3Way Handicap temp_bookmaker.temp_odds: %s", temp_bookmaker.temp_odds)
#         last_update = temp_odd.last_update
#         odd_value = temp_odd.value
#         label = temp_odd.label
#         label_raw_values = label.split(':')
#         label_values = []
#         for label_value in label_raw_values:
#             label_value = label_value.strip(' ')
#             label_values.append(label_value)
#         # logger.debug('handicap extracted values: %s', label_values)
#
#         try:
#             threshold = float(label_values[1])
#             from_handicap_field = False
#             logger.debug('threshold: %s', threshold)
#         except Exception as e:  # ValueError, IndexError, float error if threshold = None
#             # some entries have the threshold on the handicap field and not in the label
#             from_handicap_field = True
#             threshold = temp_odd.handicap
#             logger.debug('threshold from_handicap_field: %s', threshold)
#             try:
#                 threshold = float(threshold)
#             except Exception as e:
#                 logger.debug('%s, Neither the label nor the handicap fields contain the threshold', e)
#                 continue
#
#         if not temp_handicaps_per_threshold[threshold]:
#             temp_handicaps_per_threshold[threshold] = TempHandicap(threshold=threshold, last_update=last_update)
#         if not temp_handicaps_per_threshold[-threshold]:
#             # initialize it here so that we can add the away odd (see description)
#             temp_handicaps_per_threshold[-threshold] = TempHandicap(threshold=-threshold, last_update=last_update)
#
#         choice = label_values[0]
#         logger.debug('choice: %s, threshold: %s', choice, threshold)
#         if choice == '1':
#             temp_handicaps_per_threshold[threshold].home = odd_value
#         elif choice == '2':
#             if from_handicap_field:
#                 # see description
#                 temp_handicaps_per_threshold[threshold].away = odd_value
#             else:
#                 temp_handicaps_per_threshold[-threshold].away = odd_value
#         elif choice == 'X':
#             temp_handicaps_per_threshold[threshold].draw = odd_value
#         else:
#             logger.data_error('odd parsing, unknown sportmonks label %s', label)
#     logger.debug('list of temp handicaps: %s', temp_handicaps_per_threshold.values())
#     return temp_handicaps_per_threshold.itervalues()


def parse_odd_data(data, event_sid, source):
    """ Parses the json odd data of an event and creates Temporary objects which hold the data """
    temp_market_types = []
    for market_type_obj in data:
        # logger.debug('market type obj: %s', market_type_obj)
        try:
            market_type = market_type_obj.get('name')
            bookmakers_obj = market_type_obj.get('bookmaker', dict())
            bookmakers_list = bookmakers_obj.get('data', list())
        except Exception as e:
            logger.data_error('%s, get odds, data error on parsing market_type_obj data', e)
            continue

        temp_bookmakers = []
        for bookmaker_obj in bookmakers_list:
            try:
                bookmaker_name = bookmaker_obj.get('name')
                bookmaker_sid = bookmaker_obj.get('id')
                odds_obj = bookmaker_obj.get('odds', dict())
                odds_list = odds_obj.get('data', list())
            except Exception as e:
                logger.data_error('%s, get odds, data error on parsing bookmaker_obj data', e)
                continue

            temp_odds = []
            for odd_obj in odds_list:
                try:
                    label = odd_obj.get('label')
                    odd_value = odd_obj.get('value')
                    last_update_obj = odd_obj.get('last_update', dict())
                    last_update_utc = get_date(last_update_obj, 'date')
                    handicap = odd_obj.get('handicap')
                    total = odd_obj.get('total')
                    winning = odd_obj.get('winning')
                except Exception as e:
                    logger.data_error('%s, get odds, data error on parsing odd_obj data', e)
                    continue

                temp_odd = TempOddValuesObj(label, odd_value, last_update_utc, handicap, total, winning)
                temp_odds.append(temp_odd)

            temp_bookmaker = TempBookmaker(bookmaker_name, bookmaker_sid, temp_odds)
            temp_bookmakers.append(temp_bookmaker)

        temp_market_type = TempMarketType(market_type, temp_bookmakers, event_sid, source)
        temp_market_types.append(temp_market_type)
    return temp_market_types


# @vcr.use_cassette('./sportmonks/vcr_cassetes/odds_Girona_180214.yml', filter_query_parameters=['api_token'])
def get_odds(event_sids, source=utils.get_native_source):
    """ Makes a call for each event_sid, the data are parsed and stored in temporary objects and then
    these temporary objects are transformed to PreModels.

    Have in mnd that I have implemented the maximum limit handling code in the get functions so that
    it is transparently handled. These functions are called by many different commands so the commands
    code doesn't have to worry about maximum limits. One more reason is that max limits are source specific """
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("getting odds for %s events from source %s...", len(event_sids), source)
    pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = [], [], [], [], []
    if not source:
        return pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups
    if not event_sids:
        logger.info("There are no event sids to process!")
        return pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups

    all_markets = defaultdict(int)
    counter = -1
    # with open('./sportmonks/response_texts/odds_by_id.json', 'w') as outfile:
    # odds_list = []
    for event_sid in event_sids:
        counter += 1
        data, meta, status_code = sportmonks.odds.by_fixture_id(event_sid)
        # odds_list.append({"event id": int(event_sid), "data": data})
        if status_code == 429:
            logger.warning("Maximum number of allowed calls for sportmonks.odds.by_fixture_id has been reached!")
            remaining_sids = event_sids[counter:]
            chunks = gutils.utils.to_chunks(remaining_sids, constants.calls_limit)
            gutils.utils.schedule_chunks(chunks, constants.interval, utils.get_and_create_odd_trees_wrapper_sids, source_name=source.name)
            break
        if not data:
            continue
        try:
            temp_market_types = parse_odd_data(data, event_sid, source)
            for temp_market_type in temp_market_types:
                market_type = temp_market_type.market_type
                all_markets[market_type] += 1
                temp_market_type.log()
                winners, ovuns, dcs, hds, uns = temp_market_type.create_pre_markets()
                pre_winners.extend(winners)
                pre_ovuns.extend(ovuns)
                pre_dcs.extend(dcs)
                pre_hds.extend(hds)
                unsups.extend(uns)
        except Exception as e:
            logger.error('%s Unexpected problem with sportmonks.odds.by_fixture_id for event %s from source %s', repr(e), event_sid, source)
    # json.dump(odds_list, outfile, indent=4)
    logger.info('all markets (excluding those with data parsing errors): (len %s) %s', len(all_markets.keys()), all_markets.items())
    logger.info('%s pre winners, %s pre over under, %s pre double chance, %s pre handicap were created, '
                '%s unsupported market types', len(pre_winners), len(pre_ovuns), len(pre_dcs), len(pre_hds), len(unsups))
    return pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups


def goals_from_string(goal_string):
    """
    :param goal_string: A string in the form "2-2"
    """
    if not goal_string:
        return None, None
    split = goal_string.split('-')
    try:
        home_goals = int(split[0])
        away_goals = int(split[1])
    except Exception as e:
        logger.data_error("%s No goals were extracted from the goal string: %s", e, goal_string)
        return None, None
    return home_goals, away_goals


def to_total_scores(ht_score, ft_score, et_score, pen_score):
    """ et_score and pen_score refer to their respective periods. For example ft=1-1, if there is extra time
    and home team scores the total score will be 2-1 but the et_score=1-0. Zakanda scores use the total score
    so we calculate the total score """
    total_score = ft_score
    try:
        for score in [et_score, pen_score]:
            if None in score:
                continue
            score[0] = total_score[0] + score[0]
            score[1] = total_score[1] + score[1]
            total_score = score
    except Exception:
        return ht_score, ft_score, et_score, pen_score
    return ht_score, ft_score, et_score, pen_score


def create_pre_results(event, fetched_status, ht_score, ft_score, et_score, pen_score, source):
    """ scores are tuples of integers like (2,1)
        The result_status is determined by the fetched status. During event's settlement the event's status
        will be determined by it's results status """

    logger.debug("creating pre results for: %s, %s, %s, %s, %s, %s, %s",
                 event, fetched_status, ht_score, ft_score, et_score, pen_score, source)

    ht_score, ft_score, et_score, pen_score = to_total_scores(ht_score, ft_score, et_score, pen_score)
    # todo half time/full time market: create pre_results for ht_score too
    pre_results = []
    if fetched_status == constants.fetched_status['FT'].name:
        zakanda_result_type = utils.map_fetched_status_to_result_type(fetched_status)
        minute, is_final = 90, True
        pre_result = pre_models.PreResult(event, fetched_status, ft_score[0], ft_score[1],
                                          zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

    elif fetched_status == constants.fetched_status['AET'].name:
        zakanda_result_type = games.models.Result.ft_result
        minute, is_final = 90, False
        pre_result = pre_models.PreResult(event, fetched_status, ft_score[0], ft_score[1],
                                          zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

        zakanda_result_type = utils.map_fetched_status_to_result_type(fetched_status)
        minute, is_final = 120, True
        pre_result = pre_models.PreResult(event, fetched_status, et_score[0], et_score[1],
                                          zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

    elif fetched_status == constants.fetched_status['FT_PEN'].name:
        zakanda_result_type = games.models.Result.ft_result
        minute, is_final = 90, False
        pre_result = pre_models.PreResult(event, fetched_status, ft_score[0], ft_score[1],
                                          zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

        zakanda_result_type = games.models.Result.et_result
        minute, is_final = 120, False
        pre_result = pre_models.PreResult(event, fetched_status, et_score[0], et_score[1],
                                          zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

        zakanda_result_type = utils.map_fetched_status_to_result_type(fetched_status)
        minute, is_final = 120, True
        pre_result = pre_models.PreResult(event, fetched_status, pen_score[0], pen_score[1],
                                          zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

    elif fetched_status in utils.void_fetched_statuses:
        zakanda_result_type = utils.map_fetched_status_to_result_type(fetched_status)
        minute, is_final, home_goals, away_goals = 0, True, 0, 0
        pre_result = pre_models.PreResult(event, fetched_status, home_goals, away_goals,
                                          zakanda_result_type, minute, is_final, source)
        pre_results.append(pre_result)

    elif fetched_status in utils.not_started_fetched_statuses:
        pass

    elif fetched_status in utils.in_play_fetched_statuses:
        # todo live result
        pass

    return pre_results


def get_results(event_ids, source=utils.get_native_source):
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("getting results for %s events from source %s...", len(event_ids), source)
    if not source:
        return []
    all_pre_results = []
    if not event_ids:
        return []

    fetched_event_status_dict = defaultdict(int)
    id_counter = -1
    sid_counter = -1
    chunk_size = constants.calls_limit - int(0.2 * constants.calls_limit)
    # chunk_size < limit so that it leaves some space for new betted events
    for event_id in event_ids:
        id_counter += 1
        try:
            event = games.models.Event.objects.get(id=event_id)
        except Exception as e:
            logger.error("%s", e)
            continue
        sids = event.get_sids(source_name=source.name)
        if not sids:
            continue
        status_code = None
        for sid in sids:
            logger.debug('calling for sid: %s', sid)
            sid_counter += 1
            data, meta, status_code = sportmonks.fixtures.by_id(sid)
            # data, status_code = [], 429
            if not data:
                continue
            if status_code == 429 or sid_counter >= chunk_size:
                break
            try:
                time = data.get('time', dict())
                fetched_status = time.get('status')
                fetched_minute = time.get('minute')
                fetched_extra_minute = time.get('extra_minute')
                fetched_injury_time = time.get('injury_time')
                scores = data.get('scores', dict())
                ht_score = scores.get('ht_score')
                ft_score = scores.get('ft_score')
                et_score = scores.get('et_score')
                # As I saw this is the et_goals in case of AET or PEN and the ft_goals in case of FT
                home_goals = scores.get('localteam_score')
                away_goals = scores.get('visitorteam_score')
                pen_home_goals = scores.get('localteam_pen_score')  # 0 in case of FT or AET
                pen_away_goals = scores.get('visitorteam_pen_score')

                deleted = data.get('deleted', False)
                if deleted:
                    fetched_status = constants.fetched_status["Deleted"].name

                fetched_event_status_dict[fetched_status] += 1

                ht_goals = goals_from_string(ht_score)
                ft_goals = goals_from_string(ft_score)
                et_goals = goals_from_string(et_score)
                try:
                    pen_goals = int(pen_home_goals), int(pen_away_goals)
                except Exception:  # ValueError, TypeError
                    pen_goals = None, None

                pre_results = create_pre_results(event, fetched_status, ht_goals, ft_goals, et_goals, pen_goals, source)

                all_pre_results.extend(pre_results)

            except Exception as e:
                logger.warning('%s Unexpected problem with sportmonks.fixtures.by_id for event %s from source %s',
                               repr(e), event, source)
        if status_code == 429 or sid_counter >= chunk_size:
            logger.warning("Maximum number of allowed calls for sportmonks.fixtures.by_id has been reached!")
            remaining_event_ids = event_ids[id_counter:]
            chunks = gutils.utils.to_chunks(remaining_event_ids, chunk_size)
            gutils.utils.schedule_chunks(chunks, constants.interval, utils.get_and_create_results_wrapper, source_name=source.name)
            break
    logger.info("fetched events by status: %s", fetched_event_status_dict)
    logger.info("%s pre_results were created", len(all_pre_results))
    return all_pre_results


# ########################### Odds zakanda endpoint START ###########################
def odds_source_call(request):
    logger.info('zakanda api call for odds...')
    # import time
    # time.sleep(60*4)

    if request.method != 'GET':
        logger.warning('Request method is not allowed')
        return HttpResponse('Request method is not allowed', content_type="application/json")

    chatzich_key = 'chatzich'
    events_num_limit = 350  # max calls per hour to sportmonks for odds per event id
    events_num_days = 3
    ttl = 60 * 60

    key = request.META.get('HTTP_ZAKANDA_API_KEY')
    num_events = request.GET.get('num_events')
    num_days = request.GET.get('num_days')
    if not num_days:
        num_days = events_num_days
    else:
        num_days = int(num_days)
    logger.debug("parameters: [key: %s], [num_events: %s], [num_days: %s]", key, num_events, num_days)

    if not key or (key != chatzich_key):
        logger.warning('Authorization Error')
        return HttpResponse('Authorization Error', content_type="application/json")

    if not num_events:
        num_events = events_num_limit

    try:
        num_events = int(num_events)
    except Exception as e:
        return HttpResponse('Error on num_events parameter', content_type="application/json")

    if num_events > events_num_limit:
        num_events = events_num_limit

    event_sids = events_by_days(num_days=num_days)
    # event_sids = [8773305, 8773315, 8773296, 8773295]
    if len(event_sids) > num_events:
        event_sids = event_sids[:num_events]
    # logger.debug('filtered event sids: %s', len(event_sids))

    cache_key = key + '_api_key'
    made_calls = cache.get(cache_key)
    new_calls = len(event_sids)
    logger.debug('number of calls the last hour: %s, new calls: %s', made_calls, new_calls)
    if not made_calls:
        logger.debug('updating cache with: %s', new_calls)
        cache.add(cache_key, new_calls, ttl)
    elif int(made_calls) < events_num_limit:
        total_calls = int(made_calls) + new_calls
        logger.debug('total calls: %s', total_calls)
        if total_calls < events_num_limit:
            cache.set(cache_key, total_calls, ttl)
        else:
            additional_allowed_calls = events_num_limit - made_calls
            event_sids = event_sids[:additional_allowed_calls]
            cache.set(cache_key, events_num_limit, ttl)
            logger.warning('you can only get data for {} more events'.format(additional_allowed_calls))
    else:
        logger.warning('zakanda api call hourly limit reached')
        return HttpResponse('zakanda api call hourly limit reached', content_type="application/json")

    odds_list = odds_api_call(event_sids)

    # logger.debug('json odds list: %s', odds_list)
    # with open(os.path.join(os.path.dirname(__file__), 'response_texts/arb_odds.json'), 'w') as outfile:
    #     json.dump(odds_list, outfile, indent=4)

    json_odds_list = json.dumps(odds_list)
    return HttpResponse(json_odds_list, content_type="application/json")


def events_by_days(num_days):
    from django.utils import timezone
    from zakanda.db import event_distinct_sid_list

    competition_seasons = None
    # competition_gids = []
    # if competition_gids:
    #     competition_seasons = games.models.CompetitionSeason.objects.filter(
    #         competition__id__in=competition_gids, season__name='18/19')

    start_date = timezone.now()
    end_date = start_date + timezone.timedelta(days=num_days)
    status = games.models.Event.not_started  # in play
    source_name = games.naming.source_names[3]
    source = games.models.Source.objects.get(name=source_name)
    events = games.models.Event.filter_events(
        competition_seasons=competition_seasons, start_date=start_date, end_date=end_date, status=status
    )
    event_ids = events.values_list("id", flat=True)
    event_sids = event_distinct_sid_list(event_ids, source_name)
    return event_sids


# @vcr.use_cassette(os.path.join(os.path.dirname(__file__), 'vcr_cassetes/sportmonks_arb_odds.yml'), filter_query_parameters=['api_token'])
def odds_api_call(event_sids, source=utils.get_native_source):
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("getting odds for %s events from source %s...", len(event_sids), source)
    odd_objects = []
    for event_sid in event_sids:
        data, meta, status_code = sportmonks.odds.by_fixture_id(event_sid)
        event = games.models.Event.latest_event_from_sid(event_sid, source)
        odd_obj = {}
        event_obj = {
            # datetime is not json serializable
            "event_sid": event_sid, 'home_team': event.home_team.generic_name,
            'away_team': event.away_team.generic_name, 'date': event.date.__str__(),
            'competition': event.competition_season.competition.generic_name,
            'country': event.competition_season.competition.country.name,
        }
        odd_obj['event'] = event_obj
        odd_obj['data'] = data
        odd_objects.append(odd_obj)
        if status_code == 429:
            logger.warning("Maximum number of allowed calls for sportmonks.odds.by_fixture_id has been reached!")
            break
    return odd_objects
# ########################### Odds zakanda endpoint END ###########################
