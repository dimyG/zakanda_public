# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import pytest
import vcr
import json
import pytz
from collections import defaultdict
import games.models
from data_sources.tests import check_events_realization, check_odd_trees, check_brother_settlement, \
    check_events_settlement, check_ft_event, check_results_realization, check_void_event
from django.utils import timezone
import sportmonks
import views
import data_sources.pre_models
import data_sources.utils
import zakanda.db
import games.naming
import gutils.markets_creation
import gutils.utils
from django.core import management


logger = logging.getLogger(__name__)
pytestmark = pytest.mark.django_db  # so that the tests can access the database

sco_premier_1617 = 825  # 825 = 2016/2017 Premier League (Scotland), 469 competition id
den_super_1617 = 759  # 759 = 2016/2017 Superliga (Denmark), 312 competition id
cl_1617 = 718
pl_eng = 6397


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_fixtures_date_range_2017-03-30_2017-03-31_odds_venue.yml',
#                   filter_query_parameters=['api_token'])
def t_fixtures_by_date(start_date_str, end_date_str, **params):
    # '2017-03-30', '2017-03-31',
    data, meta, status_code = sportmonks.fixtures.by_date_range(start_date_str, end_date_str, **params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/fixtures_international_by_date_range_{}_{}_{}.txt'.format(start_date_str, end_date_str, extra), 'w') as outfile:
        json.dump(meta, outfile, indent=4)
        json.dump(data, outfile, indent=4)
    if not data:
        return
    ids = list()
    for fixture in data:
        fixture_id = fixture.get('id')
        ids.append(fixture_id)
        ids = list(set(ids))
    logger.debug('num distinct ids: %i', len(ids))
    assert len(ids) == len(data)


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_seasons_all_incl_rounds.yml', filter_query_parameters=['api_token'])
def t_seasons(**params):
    data = sportmonks.seasons.all(**params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/seasons_all_{}.txt'.format(extra), 'w') as outfile:
        json.dump(data, outfile, indent=4)


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_seasons_6387_incl_stages_fixtures.yml', filter_query_parameters=['api_token'])
def t_seasons_by_id(sid, **params):
    # season id 6387: Eredivisie 2017/2018, 6015: Eredivisie PlayOffs 2017/2018
    data = sportmonks.seasons.by_id(sid=sid, **params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/seasons_by_id_{}_{}.txt'.format(sid, extra), 'w') as outfile:
        json.dump(data, outfile, indent=4)


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_seasons_6015_incl_stages_fixtures.yml', filter_query_parameters=['api_token'])
def t_seasons_03():
    data = sportmonks.seasons.by_id(sid=6015, include='stages,fixtures')
    with open('../sportmonks/response_texts/seasons_6015_incl_stages_fixtures.txt', 'w') as outfile:
        json.dump(data, outfile, indent=4)


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_rounds_by_season_ids_759_825.yml', filter_query_parameters=['api_token'])
def t_rounds():
    season_sids = [den_super_1617, sco_premier_1617]
    combined_data = []
    for season_sid in season_sids:
        data = sportmonks.rounds.by_season_id(season_sid)
        combined_data.append(data)
    with open('../sportmonks/response_texts/rounds_by_season_ids_759_825.txt', 'w') as outfile:
        json.dump(combined_data, outfile, indent=4)


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_leagues_all.yml', filter_query_parameters=['api_token'])
def t_leagues(**params):
    data = sportmonks.leagues.all(**params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/leagues_all_{}.txt'.format(extra), 'w') as outfile:
        json.dump(data, outfile, indent=4)


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_countries_all.yml', filter_query_parameters=['api_token'])
def t_countries(**params):
    data, meta, status_code = sportmonks.countries.all(**params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/countries_all_{}.txt'.format(extra), 'w') as outfile:
        json.dump(data, outfile, indent=4)
    country_names = defaultdict(int)
    for country in data:
        country_names[country.get('name')] += 1
    return country_names


def t_countries_by_id(sid, **params):
    data, meta, status_code = sportmonks.countries.by_id(sid, **params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/countries_by_id_{}_{}.txt'.format(sid, extra), 'w') as outfile:
        json.dump(data, outfile, indent=4)


# @vcr.use_cassette('../sportmonks/vcr_cassetes/sportmonks_teams_all.yml', filter_query_parameters=['api_token'])
def t_teams_by_season(sid, **params):
    data = sportmonks.teams.by_season(sid, **params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/teams_by_season_everton_{}_{}.txt'.format(sid, extra), 'w') as outfile:
        # filepath is relative to xmlsoccer mytest since the code runs from there
        json.dump(data, outfile, indent=4)


def t_teams_by_id(sids, **params):
    extra = params.get('include', '').replace(',', '--').replace('.', '-').replace(':', '__').replace('(', '').replace(')', '').replace('|', '')
    with open('../sportmonks/response_texts/teams_by_id_Aris_526_{}.txt'.format(extra), 'w') as outfile:
        for sid in sids:
            data = sportmonks.teams.by_id(sid, **params)
            json.dump(data, outfile, indent=4)


# @vcr.use_cassette('vcr_cassetes/sportmonks_odds_by_fixtures_01.yml', filter_query_parameters=['api_token'])
def t_odds(event_sids):
    odds_list = []
    with open('../sportmonks/response_texts/odds_by_fixtures_8635002_new.txt', 'w') as outfile:
        # filepath is relative to xmlsoccer mytest since the code runs from there

        for event_sid in event_sids:
            data, meta, status_code = sportmonks.odds.by_fixture_id(event_sid)
            odds_list.append({"event id": int(event_sid), "data": data})
        json.dump(odds_list, outfile, indent=4)


def t_fixtures(start_date, end_date, **params):
    data, meta, status_code = sportmonks.fixtures.by_date_range(start_date, end_date, **params)
    extra = params.get('include', '').replace(',', '--').replace('.', '-') + '__' + params.get('leagues', '')
    start = '_'.join([str(start_date.year), str(start_date.month), str(start_date.day)])
    end = '_'.join([str(end_date.year), str(end_date.month), str(end_date.day)])
    with open('../sportmonks/response_texts/fixtures_{}_{}_{}.txt'.format(start, end, extra), 'w') as outfile:
        json.dump(data, outfile, indent=4)


def t_fixtures_by_id(ids, **params):
    data, meta, status_code = None, None, None
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/fixtures_by_ids_10434066.txt'.format(extra), 'w') as outfile:
        for id in ids:
            data, meta, status_code = sportmonks.fixtures.by_id(id, **params)
            json.dump(data, outfile, indent=4)
    return data, meta, status_code


def t_bookmakers(**params):
    extra = params.get('include', '').replace(',', '--').replace('.', '-')
    with open('../sportmonks/response_texts/bookmakers_all.txt'.format(extra), 'w') as outfile:
        data, meta, status_code = sportmonks.bookmakers.all(**params)
        json.dump(data, outfile, indent=4)


def check_all_teams():
    from gutils.management.commands.initialize import Command



@pytest.fixture(scope='module')
def django_db_setup(django_db_setup, django_db_blocker):
    """ Add data to the database that are available for all module tests """
    with django_db_blocker.unblock():
        # todo Now remove the --noinput just to be sure that the test database's data will be deleted
        management.call_command('flush', '--noinput')
        zakanda.db.create_initial_data()


@vcr.use_cassette('vcr_cassetes/sportmonks_countries_include_leagues-season.yml', filter_query_parameters=['api_token'])
def get_countries_competitions(source):
    pre_countries, pre_competitions = views.get_leagues_and_countries(source)
    return pre_countries, pre_competitions


@vcr.use_cassette('vcr_cassetes/sportmonks_teams_all.yml', filter_query_parameters=['api_token'])
def get_teams(source):
    season_names = ["12/13", "13/14", '14/15', '15/16', '16/17', '17/18',
                    '2012', '2013', '2014', '2015', '2016', '2017', '2018']
    pre_teams = views.get_teams(source=source)
    return pre_teams


@vcr.use_cassette('vcr_cassetes/sportmonks_events_date_range_01.yml', filter_query_parameters=['api_token'])
def get_events(start_date, end_date, source):
    pre_events = views.get_events(start_date, end_date, source)
    return pre_events


@vcr.use_cassette('vcr_cassetes/sportmonks_odds_by_fixtures_01.yml', filter_query_parameters=['api_token'])
def get_odds(event_sids, source):
    pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = views.get_odds(event_sids, source)
    return pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups


# @vcr.use_cassette('vcr_cassetes/sportmonks_countries_all_leagues-seasons.yaml')
@pytest.mark.sportmonks
@pytest.mark.sportmonks_lncs
def test_lnc_pre_models_creation():
    """ since I use a conftest.py in project level, I must place the vcr path
    relative to the project's level """
    source = games.models.Source.objects.get(name=games.naming.source_names[3])
    # have in mind that you need to pass the source here. If you don;t then the global variable is used
    # This variable is the zakanda_db entity, not the zakanda_test_db entity and that caused an unknown source error
    pre_countries, pre_competitions = views.get_leagues_and_countries(source)
    assert pre_countries
    assert pre_competitions

    for pre_country in pre_countries:
        assert isinstance(pre_country, data_sources.pre_models.PreCountry)
        country, country_info = pre_country.get_or_create(define_entity_fun=lambda: '2', define_id_fun=lambda: 'not_used')
        if pre_country.get_gname():
            assert isinstance(country, games.models.Country)
            assert isinstance(country_info, games.models.CountryInfo)

    data_sources.pre_models.MappedEntity.describe(pre_countries)

    for pre_competition in pre_competitions:
        assert isinstance(pre_competition, data_sources.pre_models.PreCompetition)
        competition, competition_seasons = pre_competition.get_or_create(define_entity_fun=lambda: '2', define_id_fun=lambda: 'not_used')
        if pre_competition.is_valid():

            assert isinstance(competition, games.models.Competition)
            comp_by_sid = games.models.Competition.by_sid(sid=pre_competition.sid, source=source)
            assert comp_by_sid == competition

            for competition_season in competition_seasons:
                assert isinstance(competition_season, games.models.CompetitionSeason)

            for util in pre_competition.competition_season_utils:
                if util.is_valid():
                    sid = util.competition_season_sid
                    comp_seasons_by_sid = games.models.CompetitionSeason.by_sid(sid=sid, source=source)
                    assert len(comp_seasons_by_sid) == 1  # sportmonks uses a competition season specific id
                    selected_competition_season = comp_seasons_by_sid[0]
                    assert selected_competition_season in competition_seasons

    data_sources.pre_models.MappedEntity.describe(pre_competitions)


def realize_pre_teams(pre_teams, **kwargs):
    teams = []
    for pre_team in pre_teams:
        logger.debug("pre team: %s %s %s %s", pre_team.sname, pre_team.sid, pre_team.source, pre_team.get_gname())
        if not pre_team:
            logger.warning('pre_team is None')
            continue
        team = pre_team.get_or_create(**kwargs)
        pre_team.team = team
        teams.append(team)
    new_teams, existing_teams, to_be_remapped = data_sources.pre_models.NameMappedEntity.exhaustive_unmapped_mapping(pre_teams)
    # if new_teams is not None and existing_teams is not None and to_be_remapped is not None:
    #     teams = new_teams + existing_teams + to_be_remapped  # to_be_remapped must be empty after exhaustive mapping
    return teams


def create_lncs(source):
    pre_countries, pre_competitions = get_countries_competitions(source)
    countries = []
    competitions = []
    comp_seasons = []
    for pre_country in pre_countries:
        country, country_info = pre_country.get_or_create(define_entity_fun=lambda: '2', define_id_fun=lambda: 'not_used')
        countries.append(country)
    for pre_competition in pre_competitions:
        competition, competition_seasons = pre_competition.get_or_create(define_entity_fun=lambda: '2', define_id_fun=lambda: 'not_used')
        competitions.append(competition)
        comp_seasons.extend(competition_seasons)
    return countries, competitions, comp_seasons


def create_teams(source):
    pre_teams = get_teams(source=source)
    # pre_teams = data_sources.pre_models.PreTeam.get_distinct(pre_teams)
    teams = realize_pre_teams(pre_teams, define_entity_fun=lambda: '2', define_id_fun=lambda: 'not_used')
    return teams


@pytest.mark.sportmonks
@pytest.mark.sportmonks_teams
def test_teams():
    source = games.models.Source.objects.get(name=games.naming.source_names[3])

    create_lncs(source)

    pre_teams = get_teams(source=source)
    # for pre_team in pre_teams:
    #     assert isinstance(pre_team, data_sources.pre_models.PreTeam)

    logger.debug("num pre_teams: %s", len(pre_teams))
    # pre_teams = data_sources.pre_models.PreTeam.get_distinct(pre_teams)
    logger.debug("num distinct pre_teams: %s", len(pre_teams))

    cr_teams = realize_pre_teams(pre_teams, define_entity_fun=lambda: '2', define_id_fun=lambda: 'not_used')
    for team in cr_teams:
        if not team:
            logger.debug('team is None, probably pre team is invalid')
            continue
        assert isinstance(team, games.models.Team)
        assert team.competition_seasons.all()
        ids = []
        for comp_seas in team.competition_seasons.all():
            ids.append(comp_seas.id)
        assert len(ids) == len(list(set(ids)))
        # assert len(team.sources.all()) == 1

    new_entities, existing_entities, to_be_remapped_entities = data_sources.pre_models.MappedEntity.describe(pre_teams)
    for existing_entity in existing_entities:
        logger.debug("existing entity: %s", existing_entity)
        team_infos = games.models.TeamInfo.objects.filter(team=existing_entity.team)
        for team_info in team_infos:
            logger.debug("  > existing entity team_info: %s", team_info)


@pytest.mark.sportmonks
@pytest.mark.sportmonks_events
def test_events():
    source_name = games.naming.source_names[3]
    source = games.models.Source.objects.get(name=source_name)

    countries, competitions, competition_seasons = create_lncs(source)
    logger.debug("num created countries, comps, comp_seasons: %s %s %s", len(countries), len(competitions), len(competition_seasons))
    teams = create_teams(source)
    logger.debug("created teams: %s", len(teams))

    # team = games.models.Team.latest_team_by_sid(65, source)
    # logger.debug("selected team: %s", team)
    # assert team
    start_date = timezone.datetime(2017, 5, 10, 13, tzinfo=pytz.timezone("UTC"))
    end_date = timezone.datetime(2017, 5, 15, 13, tzinfo=pytz.timezone("UTC"))
    pre_events = get_events(start_date, end_date, source)
    check_events_realization(pre_events, source_name, num_sources=1)


@pytest.mark.sportmonks
@pytest.mark.sportmonks_odds
def test_odds():
    source_name = games.naming.source_names[3]
    source = games.models.Source.objects.get(name=source_name)

    countries, competitions, competition_seasons = create_lncs(source)
    teams = create_teams(source)

    start_date = timezone.datetime(2017, 5, 10, 13, tzinfo=pytz.timezone("UTC"))
    end_date = timezone.datetime(2017, 5, 15, 13, tzinfo=pytz.timezone("UTC"))

    pre_events = get_events(start_date, end_date, source)

    events = []
    event_ids = []
    for pre_event in pre_events:
        event, event_info = pre_event.get_or_create()
        events.append(event)
        event_ids.append(event.id)

    market_offers = gutils.markets_creation.create_initial_markets(events)

    event_sids = zakanda.db.event_distinct_sid_list(event_ids, source_name)

    pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = get_odds(event_sids, source)

    pre_odds = pre_winners + pre_ovuns + pre_dcs + pre_hds
    market_odds, market_offers, market_offer_odds = data_sources.utils.realize_pre_odds(pre_odds, unsups)

    check_odd_trees(market_odds, market_offers, market_offer_odds, events)


@pytest.mark.sportmonks
@pytest.mark.sportmonks_results
def test_results():
    #
    # ----- same as test_odds with different dates -----
    #

    source_name = games.naming.source_names[3]
    source = games.models.Source.objects.get(name=source_name)
    countries, competitions, competition_seasons = create_lncs(source)
    teams = create_teams(source)
    start_date = timezone.datetime(2016, 11, 15, 01, tzinfo=pytz.timezone("UTC"))
    end_date = timezone.datetime(2016, 11, 16, 01, tzinfo=pytz.timezone("UTC"))
    pre_events = views.get_events(start_date, end_date, source)  # I don't use the get_event function so as not to
    # use the stored vcr response

    # this date range contains void events (postponed sid 233459)
    start_date_02 = timezone.datetime(2017, 07, 9, 01, tzinfo=pytz.timezone("UTC"))
    end_date_02 = timezone.datetime(2017, 07, 9, 23, tzinfo=pytz.timezone("UTC"))
    pre_events_02 = views.get_events(start_date_02, end_date_02, source)

    pre_events.extend(pre_events_02)

    events = []
    for pre_event in pre_events:
        event, event_info = pre_event.get_or_create()
        events.append(event)
    logger.debug("%s events were created (or selected if the db was't empty)", len(events))
    market_offers = gutils.markets_creation.create_initial_markets(events)
    # event_sids = zakanda.db.event_distinct_sid_list(events, source_name)
    # pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = get_odds(event_sids, source)
    # pre_odds = pre_winners + pre_ovuns + pre_dcs + pre_hds
    # market_odds, market_offers, market_offer_odds = data_sources.utils.realize_pre_odds(pre_odds, unsups)

    #
    # ----- same as test_odds with different dates -----
    #
    # filtered_events = zakanda.db.filter_events(start_date=start_date, end_date=end_date)
    # filtered_events_02 = zakanda.db.filter_events(start_date=start_date_02, end_date=end_date_02)
    # filtered_events = filtered_events | filtered_events_02
    # assert len(events) == len(filtered_events)

    ndr_events, dr_events = zakanda.db.split_decision_no_decision_events(events)
    logger.info("calling get results for %s events (that have no decision result)", len(ndr_events))
    ids = gutils.utils.ids(ndr_events)
    pre_results = views.get_results(ids, source)
    assert pre_results
    for pre_result in pre_results:
        isinstance(pre_result.event, games.models.Event)
        isinstance(pre_result.source, games.models.Source)
    check_results_realization(pre_results)
    check_events_settlement(ndr_events)


# @pytest.mark.test_all
# @pytest.mark.test_01
# def test_temp():
#     from django.conf import settings
#     db_name = settings.DATABASES['default']['NAME']
#     logger.warning('test_01, db name: %s', db_name)
#
#
# @pytest.mark.test_all
# @pytest.mark.test_02
# def test_temp_02():
#     from django.conf import settings
#     db_name = settings.DATABASES['default']['NAME']
#     logger.warning('test_02, db name: %s', db_name)
