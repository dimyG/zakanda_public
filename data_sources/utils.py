from __future__ import unicode_literals
import logging
import games.naming
import xmlSoccerParser.utils
from sportmonks import views as sportmonks_views
import xmlSoccerParser.views
import gutils.markets_creation
from data_sources.pre_models import NameMappedEntity, define_entity, define_id
import games.models
from zakanda.utils import datetime_format
from zakanda.db import event_distinct_sid_list
from collections import defaultdict
from django.db.models import Count


logger = logging.getLogger(__name__)


def realize_pre_lncs(pre_countries, pre_competitions, **kwargs):
    # xmlsoccer follows this same process but it also needs some additional actions too (processing special leagues)
    countries, competitions, competition_seasons = [], [], []
    if pre_countries:
        for pre_country in pre_countries:
            countries.append(pre_country.get_or_create(**kwargs)[0])
    if pre_competitions:
        for pre_competition in pre_competitions:
            competition, rel_competition_seasons = pre_competition.get_or_create(**kwargs)
            if competition:
                competitions.append(competition)
            if rel_competition_seasons:
                competition_seasons.extend(rel_competition_seasons)

    pre_models_group = [pre_countries, pre_competitions]
    for pre_models in pre_models_group:
        NameMappedEntity.exhaustive_unmapped_mapping(pre_models)
    return countries, competitions, competition_seasons


def get_and_create_lncs(source_names, sport_name, seasons, **kwargs):
    """ For each given source, it makes a call to get the competitions and countries and
      creates zakanda entities for them. Read entities go through a Mapping process in which
      they are related with the entities of other sources. User input might be needed.
    """
    all_pre_countries, all_pre_competitions = [], []
    all_countries, all_competitions = [], []
    for source_name in source_names:
        countries, competitions, competition_seasons, pre_countries, pre_competitions = [], [], [], [], []
        if source_name == games.naming.source_names[0]:
            pre_countries, pre_competitions = xmlSoccerParser.views.get_leagues_and_countries(sport_name, seasons)
            # create_pre_lncs is source specific for xmlsoccer, since it has to run the process special league
            countries, competitions, competition_seasons, del_comp_seasons, created_comp_seasons = \
                xmlSoccerParser.utils.create_pre_lncs(pre_countries, pre_competitions)

        elif source_name == games.naming.test_source_name:  # just for the tests
            test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
            pre_countries, pre_competitions = xmlSoccerParser.views.get_leagues_and_countries(sport_name, seasons, test_source)
            # create_pre_lncs is source specific for xmlsoccer, since it has to run the process special league
            countries, competitions, competition_seasons, del_comp_seasons, created_comp_seasons = \
                xmlSoccerParser.utils.create_pre_lncs(pre_countries, pre_competitions)

        elif source_name == games.naming.source_names[3]:
            pre_countries, pre_competitions = sportmonks_views.get_leagues_and_countries()
            countries, competitions, competition_seasons = realize_pre_lncs(pre_countries, pre_competitions, **kwargs)

        else:
            logger.error("Unknown source name: %s", source_name)

        all_countries.extend(countries)
        all_competitions.extend(competitions)
        all_pre_countries.extend(pre_countries)
        all_pre_competitions.extend(pre_competitions)
    return all_pre_countries, all_pre_competitions, all_countries, all_competitions


def realize_pre_teams(pre_teams, **kwargs):
    teams = []
    for pre_team in pre_teams:
        if not pre_team:
            logger.warning('pre_team is None')
            continue
        team = pre_team.get_or_create(**kwargs)
        pre_team.team = team
        if team:
            teams.append(team)
    new_teams, existing_teams, to_be_remapped = NameMappedEntity.exhaustive_unmapped_mapping(pre_teams)
    # to_be_remapped must be empty after exhaustive mapping

    for existing_entity in existing_teams:
        # normally there must be no existing entity when you run this for the first time.
        # Any duplicate teams (same team with more than one ids) will be reported here
        logger.debug("existing entity: %s", existing_entity)
        team_infos = games.models.TeamInfo.objects.filter(team=existing_entity.team)
        for team_info in team_infos:
            logger.debug("  > existing entity team_info: %s", team_info)
    return teams


def get_and_create_teams(source_names, **kwargs):
    mapping = kwargs.pop('mapping', True)
    define_entity_fun = kwargs.pop('define_entity_fun', define_entity)
    define_id_fun = kwargs.pop('define_id_fun', define_id)
    competition_ids = kwargs.pop('competition_ids', 'All')
    season_names = kwargs.pop('season_names', 'All')
    sport_name = kwargs.pop('sport_name', games.naming.sport_names['football'])

    kwargs02 = {'mapping': mapping, 'define_entity_fun': define_entity_fun, 'define_id_fun': define_id_fun}

    all_pre_teams, all_teams = [], []
    for source_name in source_names:
        teams, pre_teams = [], []
        if source_name == games.naming.source_names[0]:
            pre_teams = xmlSoccerParser.views.get_all_teams_by_league_and_season(season_names, competition_ids, sport_name)
            teams = realize_pre_teams(pre_teams, **kwargs02)

        elif source_name == games.naming.test_source_name:  # this is a temp source that exists only in the test db
            test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
            pre_teams = xmlSoccerParser.views.get_all_teams_by_league_and_season(season_names, competition_ids, sport_name, test_source)
            teams = realize_pre_teams(pre_teams, **kwargs02)

        elif source_name == games.naming.source_names[3]:
            pre_teams = sportmonks_views.get_teams(season_names, competition_ids, sport_name)
            # pre_teams = pre_models.PreTeam.get_distinct(pre_teams)
            teams = realize_pre_teams(pre_teams, **kwargs02)

        else:
            logger.error("Unknown source name: %s", source_name)

        all_pre_teams.extend(pre_teams)
        all_teams.extend(teams)
    return all_pre_teams, all_teams


def realize_pre_events(pre_events):
    events = []
    for pre_event in pre_events:
        event, event_info = pre_event.get_or_create()
        if event:
            events.append(event)
    market_offers = gutils.markets_creation.create_initial_markets(events)
    logger.info("%s events were selected or created", len(events))
    return events, market_offers


def get_and_create_events_by_date(source_names, start_date, end_date, **kwargs):
    """
    :param source_names:
    :param start_date: aware datetime object
    :param end_date: aware datetime object
    :param kwargs:
    :return:
    """
    all_events, all_pre_events = [], []
    for source_name in source_names:
        events, pre_events = [], []
        if source_name == games.naming.source_names[0]:
            # (2011-04-03 17:00) The format that the xmlSoccer API expects. In CET timezone (Europe/London)
            start_date_string, end_date_string = datetime_format(start_date=start_date, end_date=end_date, to_timezone='Europe/London', to_format='%Y-%m-%d %H:%M')
            pre_events = xmlSoccerParser.views.get_fixtures_by_date_interval(start_date_string, end_date_string)
            events, market_offers = realize_pre_events(pre_events)

        elif source_name == games.naming.test_source_name:
            start_date_string, end_date_string = datetime_format(start_date=start_date, end_date=end_date, to_timezone='Europe/London', to_format='%Y-%m-%d %H:%M')
            test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
            pre_events = xmlSoccerParser.views.get_fixtures_by_date_interval(start_date_string, end_date_string, test_source)
            events, market_offers = realize_pre_events(pre_events)

        elif source_name == games.naming.source_names[3]:
            # source = games.models.Source.objects.get(name=source_name)
            pre_events = sportmonks_views.get_events(start_date=start_date, end_date=end_date, **kwargs)
            events, market_offers = realize_pre_events(pre_events)

        else:
            logger.error("Unknown source name: %s", source_name)

        all_events.extend(events)
        all_pre_events.extend(pre_events)
    return all_events, all_pre_events


def get_and_create_events_by_lns(source_names, start_date, end_date, season, competition_sid, **kwargs):
    """
    :param source_names:
    :param competition_sid: for xmlsoccer it can also be the sname
    :param start_date, end_date: sportmonks uses daterange and competition sids
    :param season: either season object or season string
    :return:
    """
    all_events, all_pre_events = [], []
    for source_name in source_names:
        events, pre_events = [], []
        if source_name == games.naming.source_names[0]:
            pre_events = xmlSoccerParser.views.get_fixtures_by_league_and_season(competition_sid, season)
            events, market_offers = realize_pre_events(pre_events)

        elif source_name == games.naming.test_source_name:
            test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
            pre_events = xmlSoccerParser.views.get_fixtures_by_league_and_season(competition_sid, season, test_source)
            events, market_offers = realize_pre_events(pre_events)

        elif source_name == games.naming.source_names[3]:
            pre_events = sportmonks_views.get_events(start_date=start_date, end_date=end_date, **kwargs)
            events, market_offers = realize_pre_events(pre_events)

        else:
            logger.error("Unknown source name: %s", source_name)

        all_events.extend(events)
        all_pre_events.extend(pre_events)
    return all_events, all_pre_events


def realize_pre_odds(pre_odds, unsups):
    handle_unsups(unsups)
    market_odds, market_offers, market_offer_odds = [], [], []
    created_market_trees = defaultdict(int)
    invalid_pre_odds = []
    for pre_odd in pre_odds:
        market_odd, market_offer, market_offer_odd, tree_created = pre_odd.get_or_create()
        if tree_created:
            created_market_trees[market_offer.event] += 1
        if not market_odd or not market_offer or not market_offer_odd:
            invalid_pre_odds.append(pre_odd)
        else:
            market_odds.append(market_odd)
            market_offers.append(market_offer)
            market_offer_odds.append(market_offer_odd)

    logger.info("%s pre_odd objects went through the realization process", len(pre_odds))
    logger.warning("there were %s invalid PreOdd objects", len(invalid_pre_odds))
    logger.info("market trees were created for %s events", len(created_market_trees.keys()))
    for event, num in created_market_trees.iteritems():
        logger.info("%s market trees (market offer or/and offer odd) were created for event %s", num, event)

    return market_odds, market_offers, market_offer_odds


def handle_unsups(unsups):
    if not unsups:
        return
    unsupported_markets = defaultdict(int)
    for unsup in unsups:
        unsupported_markets[unsup.fetched_market_name] += 1
    if unsupported_markets:
        for market_type, num in unsupported_markets.iteritems():
            logger.warning("The source returns %s offers for market %s that we don't currently support", num, market_type)


def get_and_create_odd_trees(source_names, event_ids):
    combined_market_odds, combined_market_offers, combined_market_offer_odds = [], [], []
    for source_name in source_names:
        # market_odds, market_offers, market_offer_odds = [], [], []
        pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = [], [], [], [], []
        event_sids = event_distinct_sid_list(event_ids, source_name)

        if source_name == games.naming.source_names[0]:
            pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = xmlSoccerParser.views.get_odds_by_event_sid_api_call(event_sids)

        elif source_name == games.naming.test_source_name:
            event_sids = event_distinct_sid_list(event_ids, games.naming.source_names[0])
            test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
            pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = xmlSoccerParser.views.get_odds_by_event_sid_api_call(event_sids, test_source)

        elif source_name == games.naming.source_names[3]:
            pre_winners, pre_ovuns, pre_dcs, pre_hds, unsups = sportmonks_views.get_odds(event_sids)

        else:
            logger.error("Unknown source name: %s", source_name)

        pre_odds = pre_winners + pre_ovuns + pre_dcs + pre_hds
        market_odds, market_offers, market_offer_odds = realize_pre_odds(pre_odds, unsups)

        combined_market_odds.extend(market_odds)
        combined_market_offers.extend(market_offers)
        combined_market_offer_odds.extend(market_offer_odds)
    return combined_market_odds, combined_market_offers, combined_market_offer_odds


def realize_pre_results(pre_results):
    results = []
    events_with_valid_result = []
    for pre_result in pre_results:
        result, created = pre_result.get_or_create()
        if result:
            results.append(result)
            events_with_valid_result.append(pre_result.event)
    return results, events_with_valid_result


def get_and_create_results(source_names, event_ids):
    if not event_ids:
        return
    all_pre_results = []
    # todo settle_trees event_ids. If settle trees gets event ids instead of events there is no need to order
    # the events here, since ids are already ordered
    events = games.models.Event.objects.filter(id__in=event_ids).annotate(
        num_bet_events=Count('bet_events')).order_by('-num_bet_events')
    for source_name in source_names:
        if source_name == games.naming.source_names[0]:
            pre_results = xmlSoccerParser.views.get_results(events)

        elif source_name == games.naming.test_source_name:
            test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
            pre_results = xmlSoccerParser.views.get_results(events, test_source)

        elif source_name == games.naming.source_names[3]:
            pre_results = sportmonks_views.get_results(event_ids)

        else:
            pre_results = []
            logger.error("Unknown source name: %s", source_name)

        all_pre_results.extend(pre_results)

    results, events_with_valid_result = realize_pre_results(all_pre_results)
    games.models.Event.settle_trees(events_with_valid_result, update_cache=True)
    return
