from __future__ import unicode_literals
import logging
import vcr
import pytest
from django.utils import timezone
import pytz
from collections import defaultdict
import gutils.utils
import data_sources.utils
import data_sources.pre_models
import games.models
import games.naming
from bet_slip.utils import get_exact_m2m_match
from xmlSoccerParser.tests import create_lnc_pre_models
import xmlSoccerParser.utils
import xmlSoccerParser.views
from zakanda.utils import datetime_format
import gutils.markets_creation
import zakanda.db


logger = logging.getLogger(__name__)
pytestmark = pytest.mark.django_db  # so that the tests can access the database
default_source_names = [games.naming.default_source_name]

# dates used by the calls to get events. We assume that the db doesn't contain those
# events yet
start_date = timezone.datetime(2017, 5, 10, 13, tzinfo=pytz.timezone("UTC"))
end_date = timezone.datetime(2017, 5, 15, 13, tzinfo=pytz.timezone("UTC"))


def check_brother_settlement(pre_events, source_name):
    events_with_brothers = []
    for pre_event in pre_events:
        event = pre_event.event
        if event:
            assert event.status == games.models.Event.not_started
            brothers = event.get_brothers(source_name)
            if brothers:
                print('active event: {}'.format(event))
                events_with_brothers.append(event)
                for brother in brothers:
                    print(' > brother: {}'.format(brother))
                    # assert brother.date < event.date  # this is not always true. An event can move to a previous date
                    assert brother.status in games.models.Event.void_event_statuses
                    assert brother.get_sids(source_name) == event.get_sids(source_name)
    return events_with_brothers


def check_events_realization(pre_events, source_name, num_sources=1):
    assert pre_events
    # events, market_offers = data_sources.utils.realize_pre_events(pre_events)
    events = []
    event_ids = []
    for pre_event in pre_events:
        event, event_info = pre_event.get_or_create()
        events.append(event)
        event_ids.append(event.id)
        if pre_event.event:
            assert isinstance(pre_event.event, games.models.Event)
            assert pre_event.event.event_infos.all().count() == num_sources

    events_with_brothers = check_brother_settlement(pre_events, source_name=source_name)

    distinct_event_sids = zakanda.db.event_distinct_sid_list(event_ids, source_name=source_name)
    assert distinct_event_sids
    assert len(list(set(distinct_event_sids))) == len(distinct_event_sids)  # check if they are distinct

    events_with_markets = []
    for event in events:
        if event:
            if event.market_types.all():
                events_with_markets.append(event)
    num_ev_markets = len(events_with_markets)  # num events that already have markets
    num_invalid_events = events.count(None)
    num_markets = games.models.MarketType.objects.all().count()
    # how many markets must be created for the events that have no markets
    num_created_markets = num_markets * (len(events) - num_ev_markets - num_invalid_events)

    market_offers = gutils.markets_creation.create_initial_markets(events)
    assert market_offers
    assert num_created_markets == len(market_offers)

    print('{} pre events were created'.format(len(pre_events)))
    print('{} events were realized'.format(len(events)))
    print('{} pre events are invalid'.format(num_invalid_events))
    print('{} pre events already had markets'.format(num_ev_markets))
    print('{} events have brothers'.format(len(events_with_brothers)))


def check_odd_trees(odds, offers, offer_odds, events):
    assert odds
    assert offers
    assert offer_odds

    for odd in odds:
        if isinstance(odd, games.models.WinnerOdd) or isinstance(odd, games.models.HandicapOdd):
            assert odd.home
            assert odd.away
            assert odd.draw
        elif isinstance(odd, games.models.OverUnderOdd):
            assert odd.over
            assert odd.under

    events_dict = defaultdict(int)
    for offer in offers:
        assert isinstance(offer.event, games.models.Event)
        events_dict[offer.event] += 1
    logger.info("market trees were created for %s events ", len(events_dict.keys()))
    # for event in events_dict.keys():
    #     logger.debug("event: %s", event)

    for offer_odd in offer_odds:
        if isinstance(offer_odd, games.models.WinnerOfferOdd):
            assert isinstance(offer_odd.offer, games.models.WinnerOffer)
            assert offer_odd.offer in offers
            assert offer_odd.odd in odds

    exception_events = defaultdict(int)
    for event in events:
        if not event:
            continue

        try:
            woffer = games.models.WinnerOffer.objects.get(event=event)
            assert woffer in offers
        except Exception as e:
            exception_events[event] += 1
            logger.info("Exception: %s", e)

        try:
            dcoffer = games.models.DoubleChanceOffer.objects.get(event=event)
            assert dcoffer in offers
        except Exception as e:
            exception_events[event] += 1
            logger.info("Exception: %s", e)

        try:
            hdoffers = games.models.HandicapOffer.objects.filter(event=event)
            for hdoffer in hdoffers:
                assert hdoffer in offers
        except Exception as e:
            exception_events[event] += 1
            logger.info("Exception: %s", e)

        try:
            ougoffers = games.models.OverUnderOffer.objects.filter(event=event)
            for ougoffer in ougoffers:
                assert ougoffer in offers
        except Exception as e:
            exception_events[event] += 1
            logger.info("Exception: %s", e)

    logger.debug("there are %s events for which at least one market wasn't created from this source call", len(exception_events))
    for event, num in exception_events.items():
        logger.debug("%s market trees were not created for exception event: %s", num, event)


def check_results_realization(pre_results):
    for pre_result in pre_results:
        logger.debug("event %s has this pre_result: %s, %s, %s, %s", pre_result.event, pre_result.result_type, pre_result.home_goals, pre_result.away_goals, pre_result.is_final)
    results, evets_with_new_result = data_sources.utils.realize_pre_results(pre_results)
    assert results
    logger.info("%s new results were created", len(results))
    events_upd_with_result = []
    invalid_pre_results = []
    for result in results:
        # logger.debug("result obj: %s, %s, %s, %s, %s", result, result.minute, result.extra_minute, result.type, result.final)
        if result:
            assert isinstance(result, games.models.Result)
            events_upd_with_result.extend(result.event_set.all())
        else:
            invalid_pre_results.append(result)
    events_upd_with_result = list(set(events_upd_with_result))
    logger.info("there are %s invalid pre_results", len(invalid_pre_results))
    logger.info("%s events were updated with new results", len(events_upd_with_result))


def check_void_event(event):
    # result for event 364513 from xmlsoccer has been manually switched to "Postponed"
    assert event.status in games.models.Event.void_event_statuses
    bet_events = games.models.BetEvent.objects.filter(event=event)
    for bet_event in bet_events:
        assert bet_event.selection.status == games.models.Selection.void
    tbets = event.get_tbets()
    for tbet in tbets:
        bets = tbet.bets.all()
        for bet in bets:
            assert bet.bet_events.filter(selection__status=games.models.Selection.void)
            bet_events = bet.bet_events.all()
            init_bet_odd = 1
            for bet_event in bet_events:
                init_bet_odd *= bet_event.selection.selected_odd
            assert bet.odd < init_bet_odd  # since the void bet_event has calculated as if it has odd 1
            if bet_events.count() == 1:
                assert bet.odd == 1
                assert tbet.odd == 1
                assert tbet.amount == tbet.total_return
                assert tbet.status == games.models.TotalBet.won
    logger.debug("void tbets: %s", tbets)


def check_ft_event(event):
    # an event can have a ft_result but also an interrupted final result (in extra time).
    assert event.status in games.models.Event.finished_event_statuses or event.status in games.models.Event.void_event_statuses
    bet_events = games.models.BetEvent.objects.filter(event=event)
    for bet_event in bet_events:
        assert bet_event.selection.status != games.models.Selection.open
    tbets = event.get_tbets()
    for tbet in tbets:
        for bet in tbet.bets.all():
            if bet.bet_events.count() == 1:
                assert tbet.status != games.models.TotalBet.open
                if tbet.status == games.models.TotalBet.won:
                    assert pytest.approx(tbet.total_return, 0.00001) == tbet.amount * tbet.odd
                    # assert tbet.total_return - (tbet.amount * tbet.odd) < 0.000001
                elif tbet.status == games.models.TotalBet.lost:
                    assert tbet.total_return == 0


def create_event_with_2_dec_results(dr_events):
    # it adds a new postponed result (which is a decision type) to an event that already has a ft_result
    # (which is a decision type)
    for dr_event in dr_events:
        if dr_event.results.count() == 1 and dr_event.get_decision_result().type == games.models.Result.ft_result:
            logger.info("adding result of type 'Interrupted' to event: %s", dr_event)
            result, created = games.models.Result.objects.get_or_create(
                home_goals=0, away_goals=0, minute=0, type=games.models.Result.interrupted, final=True)
            dr_event.add_result(result)
            break


def check_events_settlement(events):
    # todo create automatically some total bets for testing
    for event in events:
        if event.results.all():
            assert event.results.get(final=True)
            assert event.results.filter(type__in=games.models.Result.decision_types)
        else:
            # no results were fetched for these events
            pass

    # a result call was made so ndr and dr events have changed
    ndr_events, dr_events = zakanda.db.split_decision_no_decision_events(events)

    create_event_with_2_dec_results(dr_events)

    c_bevs, c_cbs, c_wbs, c_obs, c_ctbs, c_otbs, c_changed_tbs = games.models.Event.settle_trees(dr_events, update_cache=False)

    voids, fts, others = [], [], []
    for event in dr_events:
        # related_bet_events, cbs, wbs, obs, ctbs, otbs, changed_tbs = event.settle_tree()
        logger.debug("checking event: %s, with results: %s, decision type result: %s ", event, event.results, event.get_decision_result())
        assert event.status not in games.models.Event.open_event_statuses
        dec_result = event.get_decision_result()
        if dec_result.type in games.models.Result.void_types:
            voids.append(event)
            check_void_event(event)
        elif dec_result.type == games.models.Result.ft_result:
            fts.append(event)
            check_ft_event(event)
        else:
            others.append(event)
            logger.error("unsupported decision type %s", dec_result.type)

    logger.info("%s events settled with ft result", len(fts))
    logger.info("%s events settled with Void result", len(voids))
    logger.info("%s events settled with Unsupported decision result", len(others))
    c_cbs = list(set(c_cbs))
    c_ctbs = list(set(c_ctbs))
    logger.info("%s bets were closed", len(c_cbs))
    logger.info("%s total bets were closed", len(c_ctbs))
    for tb in c_ctbs:
        logger.info("%s", tb)


@pytest.fixture(scope='module')
def django_db_setup(django_db_setup, django_db_blocker):
    """ Add data to the database that are available for all module tests. Comps and countries
     need to exist in order for teams to be created """
    with django_db_blocker.unblock():
        test_source, created = games.models.Source.objects.get_or_create(name=games.naming.test_source_name)


@pytest.fixture
def create_lncs():
    pre_countries, pre_competitions, test_source = create_lnc_pre_models()
    countries, competitions, competition_seasons, del_comp_seasons, created_comp_seasons = \
        xmlSoccerParser.utils.create_pre_lncs(pre_countries, pre_competitions)


@pytest.fixture
@vcr.use_cassette('vcr_cassetes/xmlsoccer_get_teams_by_league_and_season_1617.yaml')
def create_teams():
    source_names = [games.naming.default_source_name]
    season_names = ['16/17']
    all_pre_teams, all_teams = data_sources.utils.get_and_create_teams(
        source_names, season_names=season_names, define_entity_fun=lambda: '2', define_id_fun=lambda: 'Not used')


@pytest.fixture
@vcr.use_cassette('vcr_cassetes/xmlsoccer_fixtures_by_daterange.yaml')
def create_events(source_names=default_source_names):
    # start_date = timezone.datetime(2017, 5, 10, 13, tzinfo=pytz.timezone("UTC"))
    # end_date = timezone.datetime(2017, 5, 15, 13, tzinfo=pytz.timezone("UTC"))
    events, pre_events = data_sources.utils.get_and_create_events_by_date(source_names, start_date, end_date)
    return events, pre_events


@pytest.mark.call_create_lncs
@vcr.use_cassette('vcr_cassetes/get_leagues_and_countries.yaml')
def test_lncs_combo():
    """ tests the creation of lncs (leagues and countries) for any given source or combination of sources.
    it makes the call and also creates the entities (thus the combo in the name)
    it is not source related. Source related tests for the same function exist in the sources django app.
    """
    # kwargs = {'source': ' xmlsoccer , ' + games.naming.test_source_name}
    kwargs = {'source': games.naming.test_source_name}
    assert games.models.Source.objects.get(name=games.naming.test_source_name)
    args = []
    source_names = gutils.utils.get_command_sources(*args, **kwargs)
    football_gname = games.naming.sport_names.get('football', None)
    # seasons = games.models.Season.objects.all()[49:79]  # Seasons: currently position 49 is Season 93/94
    seasons = [games.models.Season.objects.all()[72]]  # 16/17?

    pre_countries, pre_comps, countries, comps = data_sources.utils.get_and_create_lncs(source_names, football_gname, seasons)

    assert pre_countries
    assert pre_comps
    assert countries
    assert comps

    for country in countries:
        assert isinstance(country, games.models.Country)
    for comp in comps:
        assert isinstance(comp, games.models.Competition)


@pytest.mark.call_create_combo2
@vcr.use_cassette('vcr_cassetes/xmlsoccer_get_teams_by_league_and_season_1617.yaml')
def test_teams_combo(create_lncs):
    """ It assumes that the db already has the xmlsoccer teams. A call is made to xmlsoccer to get the teams again
    but we define them as if it was from a different source. Any possible new teams are saved in the db """

    # kwargs = {'source': ' xmlsoccer , ' + games.naming.test_source_name}
    # kwargs = {'source': games.naming.test_source_name}
    kwargs = {'source': games.naming.default_source_name}
    args = []
    source_names = gutils.utils.get_command_sources(*args, **kwargs)
    season_names = ['16/17']

    old_db_teams = games.models.Team.objects.all()
    num_old_db_teams = old_db_teams.count()
    all_pre_teams, all_teams = data_sources.utils.get_and_create_teams(
        source_names, season_names=season_names, define_entity_fun=lambda: '2', define_id_fun=lambda: 'Not used')
    db_teams = games.models.Team.objects.all()
    num_db_teams = db_teams.count()

    assert all_pre_teams
    assert all_teams
    assert len(all_pre_teams) == len(all_teams)
    pre_check = 0
    for pre_team in all_pre_teams:
        if pre_team.sname == 'Atlanta United':
            pre_check += 1
        assert isinstance(pre_team, data_sources.pre_models.PreTeam)

    # a team might appear more than one times in the results from the data-source
    teams_set = set(all_teams)
    all_teams = list(teams_set)
    n2sources, n1sources = 0, 0  # n1sources: the number of the pre entities that have only 1 source
    check = 0
    for team in all_teams:
        if team.generic_name == 'Atlanta United':
            check += 1
        assert isinstance(team, games.models.Team)
    assert pre_check == check

    if source_names == [games.naming.test_source_name]:  # and the existing db has only xmlsoccer teams
        for team in all_teams:
            if len(team.sources.all()) == 2:
                n2sources += 1
            elif len(team.sources.all()) == 1:
                n1sources += 1
            else:
                assert False

        # teams that existed some time in the past but they are no longer returned by the call to the data-source
        old_teams = get_exact_m2m_match(games.models.Team, 'sources', games.models.Source.objects.filter(name=games.naming.default_source_name))
        new_teams = get_exact_m2m_match(games.models.Team, 'sources', games.models.Source.objects.filter(name=games.naming.test_source_name))
        assert len(new_teams) == n1sources
        assert len(all_teams) - len(new_teams) == n2sources
        assert len(old_teams) + len(new_teams) == num_db_teams - n2sources
        assert num_db_teams == n2sources + n1sources + len(old_teams)

    print('number of already existing teams: {}'.format(num_old_db_teams))
    print('number of currently existing teams: {}'.format(num_db_teams))
    print('number of teams in the response: {}'.format(len(all_teams)))
    print('number of new teams: {}'.format(num_db_teams - num_old_db_teams))
    print('number of old teams that were not in the response: {}'.format(num_old_db_teams - (len(all_teams) - (num_db_teams - num_old_db_teams))))


# @pytest.fixture(params=[
#     [games.naming.default_source_name],
#     [games.naming.default_source_name, games.naming.test_source_name]
# ])
# def get_source_names(request):
#     source_names = request.param
#     return source_names


@pytest.mark.events
# @pytest.mark.parametrize("create_lncs, create_teams, source_names", [
#     (create_lncs, create_teams, [games.naming.default_source_name]),
#     (create_lncs, create_teams, [games.naming.default_source_name, games.naming.test_source_name]),
# ])
@vcr.use_cassette('vcr_cassetes/xmlsoccer_fixtures_by_daterange.yaml')
def test_events_combo(create_lncs, create_teams, source_names=default_source_names):
    # start_date = timezone.datetime(2017, 5, 10, 13, tzinfo=pytz.timezone("UTC"))
    # end_date = timezone.datetime(2017, 5, 15, 13, tzinfo=pytz.timezone("UTC"))
    events, pre_events = data_sources.utils.get_and_create_events_by_date(source_names, start_date, end_date)
    num_sources = len(source_names)
    assert pre_events
    assert events
    for pre_event in pre_events:
        assert isinstance(pre_event, data_sources.pre_models.PreEvent)
        if pre_event.event:
            assert isinstance(pre_event.event, games.models.Event)
            assert pre_event.event.event_infos.all().count() == num_sources
    # for event in events:
    #     assert isinstance(event, games.models.Event)
    #     assert event.event_infos.all().count() == num_sources

    print('{} pre events were created'.format(len(pre_events)))
    print('{} events were realized'.format(len(events)))
    num_invalid_events = events.count(None)
    print('{} pre events are invalid'.format(num_invalid_events))


@pytest.mark.events
@vcr.use_cassette('vcr_cassetes/xmlsoccer_fixtures_by_daterange.yaml')
def test_events_realization(create_lncs, create_teams):
    start_date_string, end_date_string = datetime_format(start_date=start_date, end_date=end_date, to_timezone='Europe/London', to_format='%Y-%m-%d %H:%M')
    pre_events = xmlSoccerParser.views.get_fixtures_by_date_interval(start_date_string, end_date_string)
    source_name = games.naming.source_names[0]
    check_events_realization(pre_events, source_name, num_sources=2)


@pytest.mark.odds
@vcr.use_cassette('vcr_cassetes/xmlsoccer_odds_by_daterange.yaml')
def test_odd_trees_combo(create_lncs, create_teams, create_events, source_names=default_source_names):
    # notice: the source that the events were created from must match this source since the pre_odds
    # are connected with the events and they get the events from their sid and source
    events, pre_events = create_events
    event_ids = gutils.utils.ids(events)
    odds, offers, offer_odds = data_sources.utils.get_and_create_odd_trees(source_names, event_ids)
    check_odd_trees(odds, offers, offer_odds, events)


@pytest.mark.results
@vcr.use_cassette('vcr_cassetes/xmlsoccer_get_results.yaml')
def test_results():
    test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
    xmlSoccer_source = games.models.Source.objects.get(name=games.naming.source_names[0])

    start_date = timezone.datetime(2017, 2, 01, 13, tzinfo=pytz.timezone("UTC"))
    end_date = timezone.datetime(2017, 5, 15, 13, tzinfo=pytz.timezone("UTC"))
    events = games.models.Event.filter_events(start_date=start_date, end_date=end_date)

    ndr_events, dr_events = zakanda.db.split_decision_no_decision_events(events)
    logger.info("calling get results for %s events with no decision result", len(ndr_events))
    # events.filter(status__in=games.models.Event.open_event_statuses)

    pre_results = xmlSoccerParser.views.get_results(ndr_events, xmlSoccer_source)
    assert pre_results
    for pre_result in pre_results:
        isinstance(pre_result.event, games.models.Event)
        isinstance(pre_result.source, games.models.Source)

    check_results_realization(pre_results)

    check_events_settlement(ndr_events)




