# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

import feeds.utils
import gutils.utils
import models
import pytz
import zakanda.db
# import bet_statistics.utils
import zakanda.utils
from actstream.models import following
from dateutil import parser
from django.contrib.auth.models import User
# from django.views.decorators.cache import cache_page
# from django.views.decorators.vary import vary_on_cookie
# from django.views.decorators.vary import vary_on_headers
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils import timezone
# from django.db.models import Prefetch
from djpjax import pjaxtend
from gutils.views import try_cache_first
from zakanda.settings import cache_time
import bet_tagging.models
from django.contrib.auth.decorators import login_required
# from itertools import chain
# tips_list = list(chain(*tips_list_of_querysets))  # concatenate the querysets into one list

logger = logging.getLogger(__name__)


@try_cache_first(timeout=cache_time/3)
def get_popular_raw_bev_events(num, bet_group_type):
    """ Only total bets of the given bet_group_type are included in the calculation. Your premium tips will not appear.
    The reason is to avoid different versions of the popular bet events page for each user.
    There is only one version of the page and it is cached.
    :param num:
    :param bet_group_type:
    :return :
    """
    # TODO NOW REGULAR CACHE
    # bet_events = models.BetEvent.objects.filter(selection__status=models.Selection.open)
    # related_tbs = models.BetEvent.get_total_bets(bet_events)
    total_bets = models.TotalBet.objects.filter(status=models.TotalBet.open, bet_tag__type=bet_group_type)
    bets = models.Bet.objects.filter(totalbet__in=total_bets).distinct()
    bet_events = models.BetEvent.objects.filter(bet__in=bets).filter(selection__status=models.Selection.open)
    pop_raw_bet_events = feeds.utils.popular_raw_bet_events(bet_events, num, bet_group_type)
    return pop_raw_bet_events


@try_cache_first(timeout=cache_time/3)
def get_latest_wins(num):
    # TODO NOW REGULAR CACHE
    logger.debug("getting latest wins...")
    win_tbs = models.TotalBet.objects.filter(status=models.TotalBet.won).order_by('decision_date')[:num].\
        select_related('user', 'bookmaker', 'bet_tag').\
        prefetch_related('bets__bet_events', 'bets__bet_events__selection', 'bets__bet_events__market_type',
                          'bets__bet_events__event__home_team', 'bets__bet_events__event__away_team',
                          'bets__bet_events__event__competition_season__competition',
                          'bets__bet_events__event__competition_season__season', 'bets__bet_events__event__results',
                          'bets__bet_events__event__competition_season__competition__country')
    # to be enriched in outer scope
    return win_tbs


# @try_cache_first(cache_time/3)
def user_tips(request, user_pk):
    # logger.debug("tips not cached, calculating tips...")
    target_user = gutils.utils.get_user(user_pk)
    if not target_user:
        return
    tips = target_user.profile.get_tips()
    models.TotalBet.batch_enrich(tips, request)
    return tips


# @cache_page(cache_time/3)
@login_required()
@pjaxtend()  # It must be after @cache_page as I saw
def user_tips_view(request, user_pk):
    logger.debug("user tips view...")
    tips = user_tips(request, user_pk)
    context = {'total_bets': tips, 'title': 'Tips'}
    return TemplateResponse(request, 'bet_statistics/simple_tbs_list.html', context)


# @cache_page(cache_time/3)
# @vary_on_cookie
@zakanda.utils.custom_pjaxtend()
def popular_raw_bevs(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('home'))
        # return TemplateResponse(request, 'gutils/index.html', {})

    context = {}
    context['cookie'] = request.COOKIES
    context['session'] = request.session

    # from actstream import registry
    # from django.contrib.auth.models import User
    # registry.register(User)
    # import stream_django
    # import os
    # print("PATH: ", os.path.abspath(stream_django.__file__))

    # tips = user_tips(request, request.user.pk)
    # context['tips'] = tips

    bet_group_type = bet_tagging.models.BetTag.free
    pop_raw_bet_events = get_popular_raw_bev_events(50, bet_group_type)
    context['raw_bet_events'] = pop_raw_bet_events

    # win_tbs = get_latest_wins(60)
    # win_tbs = None
    # context["win_tbs"] = win_tbs

    return TemplateResponse(request, 'games/popular_raw_bevs.html', context)


# ------------------------------------------------------
# COLLECT EVENTS WITH THEIR MARKETS (the games app main purpose)
# ------------------------------------------------------

def odd_to_show(event, market_type, bookmaker):
    """ if there is no odd from the given bookmaker show odds only
    from mainstream bookmakers so that there is no strange odd """
    from_selected_bookmaker = True
    odds = market_type.get_market_odds(event, bookmaker)
    if not odds:
        odds = market_type.get_market_odds(event, bookmaker='mainstream')
        from_selected_bookmaker = False
    try:
        latest_market_odd = odds[-1]  # odds are ordered
    except Exception as e:
        latest_market_odd = None
    return latest_market_odd, from_selected_bookmaker


def calculate_odds_per_market_type(event, market_type, bookmaker, odds_per_market_type):
    # print('market_type found', market_type.name)
    market_types_with_order = {}
    thresholds_for_market_specific_offer = {}
    market_specific_offer, order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(event)

    thresholds_for_market_specific_offer[market_specific_offer] = [threshold_1, threshold_2]
    # print('market_specific_offer', market_specific_offer)
    if order:
        market_types_with_order = {'order': order, 'market_type': market_type}

    latest_market_odd, from_selected_bookmaker = odd_to_show(event, market_type, bookmaker)

    # print('latest_market_odd', latest_market_odd)
    latest_market_odd_from_bookmaker = {latest_market_odd: from_selected_bookmaker}
    if latest_market_odd:
        # {market type: {latest odd for this event and market type : is this odd from the selected bookmaker}, ...}
        odds_per_market_type[market_type] = latest_market_odd_from_bookmaker
    return odds_per_market_type, market_types_with_order, thresholds_for_market_specific_offer


def odds_from_events(events, bookmaker, market_type_names='ALL'):
    logger.info('getting latest odds and related info for given events and market types...')
    odds_per_market_type_per_event = {}
    market_types_with_order_per_event = {}
    market_types_with_order_list = []
    offer_and_thresholds_per_market_type_per_event = {}
    offer_and_thresholds_per_market_type = {}

    logger.info("   getting the market specific offers (their thresholds and order) of given events and market types")
    logger.info("   getting the latest odds for the given market specific offers")
    for event in events:
        odds_per_market_type = {}
        if market_type_names == 'ALL':
            market_types = event.market_types.all()
        else:
            # TODO low support a random list of  market_type_names. Now only ALL or ONE is supported
            market_types = event.market_types.filter(name=market_type_names)

        for market_type in market_types:
            odds_per_market_type, market_types_with_order, thresholds_for_market_specific_offer = calculate_odds_per_market_type(
                event, market_type, bookmaker, odds_per_market_type)
            # odds_per_market_type
            # {market type: {latest odd for this event and market type : is this odd from the selected bookmaker}, ...}
            market_types_with_order_list.append(market_types_with_order)
            # [{'order': 3, 'market': market3}, {'order': 1, 'market': market1}..]
            offer_and_thresholds_per_market_type[market_type] = thresholds_for_market_specific_offer
            # { market_type_1: {offer_1: [thr1, thr2]}, market_type_2: {offer_2: [thr1, thr2], .. }

        # TODO TEMP_CLASSES check if it is better to replace the dictionaries with the TempClasses approach
        odds_per_market_type_per_event[event] = odds_per_market_type
        # {ev1_obj: {winner_market_obj: {latest_odd_obj: True}, over_under_market_obj: {latest_odd_obj: False},..},
        # ev2_obj: {winner_market_obj: {latest_odd_obj: True}, over_under_market_obj: {latest_odd_obj: True},..}}
        market_types_with_order_per_event[event] = market_types_with_order_list
        offer_and_thresholds_per_market_type_per_event[event] = offer_and_thresholds_per_market_type
        # {event1: { market_type_1: {offer_1: [thr1, thr2]}, market_type_2: {offer_2: [thr1, thr2], .. }, event_2" {}, }

    return odds_per_market_type_per_event, market_types_with_order_per_event, offer_and_thresholds_per_market_type_per_event


# @cache_page(cache_time)  the page contains the bookmaker form that contains a csrf token so
# the cached page must be varied by cookie
@pjaxtend()
def planned_competition_events(request, competition_ids, competition_gnames=None):
    """
    It can be called with GET request from the competitions list and with POST from the bookmakers list
    competition_gnames: it isn't used anymore to select competitions. Can be deleted
    """
    logger.debug('getting planned events for selected competitions...')

    # default_start_date = timezone.datetime(2015, 12, 01, 12, tzinfo=pytz.timezone("UTC"))
    # default_start_date = timezone.now() - timezone.timedelta(days=7)
    default_start_date = timezone.now() + timezone.timedelta(minutes=5)
    default_end_date = timezone.now() + timezone.timedelta(days=5)
    start_date = request.GET.get('start', default_start_date)
    end_date = request.GET.get('end', default_end_date)

    # start_date = timezone.now() - timezone.timedelta(days=7)
    # end_date = timezone.now()

    # date strings from js contain tz info so here they are transformed to utc.
    # this way the user filters the event according to his tz
    if not isinstance(start_date, timezone.datetime):
        # start_date = timezone.datetime.strptime(start_date, '%B-%d-%Y%z')
        # parser is slower than strptime since you have to guess the format but it can parse timezone info
        # logger.debug("received start date: %s", start_date)
        start_date = parser.parse(start_date)
        # logger.debug("parsed start date: %s", start_date)
        start_date = start_date.astimezone(pytz.utc)
        # logger.debug("utc start date: %s", start_date)
        # start_date.replace(tzinfo=pytz.utc)
    if not isinstance(end_date, timezone.datetime):
        end_date = parser.parse(end_date)
        end_date = end_date.astimezone(pytz.utc)

    max_date_range = timezone.timedelta(days=8)
    if end_date - start_date > max_date_range:
        end_date = start_date + max_date_range

    # end_date = end_date + timezone.timedelta(days=20)
    status_list = models.Event.open_event_statuses
    # status_list = []

    # Have in mind: the events belong to a competition season but the fact that you see the teams in these events
    # doesn't mean that these teams are indeed assigned to this competition season. Normally they should but
    # in case of data errors, you can't be sure without checking
    # todo cache it
    events_per_competition, all_events = zakanda.db.get_events_in_daterange_and_competitions(
        competition_ids, start_date, end_date, status_list=status_list)

    # logger.debug('filtering events from %s(%s) to %s(%s)', start_date, start_date.tzinfo, end_date, end_date.tzinfo)
    # for event in all_events[:10]:
    #     logger.debug('event date: %s(%s)', event.date, event.date.tzinfo)

    selected_bookmaker, selected_bookmaker_name, bookmaker_added, bookmaker_updated = zakanda.utils.get_selected_bookmaker(request)
    if bookmaker_updated:
        bet_slip_events_list = sync_session_bet_slip_with_bookmaker(request, selected_bookmaker)

    odds_per_market_type_per_event = {}
    market_types_with_order_per_event = {}
    if selected_bookmaker:
        odds_per_market_type_per_event, market_types_with_order_per_event, offer_and_thresholds_per_market_type_per_event = odds_from_events(
            all_events, bookmaker=selected_bookmaker, market_type_names=models.MarketType.winner_market_type)
    else:
        logger.error('Bookmaker with name "%s" does not exist', selected_bookmaker_name)
        raise Http404('Bookmaker with name "{0}" does not exist'.format(selected_bookmaker_name))
    try:
        # TODO CACHE IT
        winner_market = models.MarketType.objects.get(name=models.MarketType.winner_market_type)
    except models.MarketType.DoesNotExist:
        winner_market = None

    bookmakers = models.Bookmaker.objects.all()
    winner_market_choices = {'1': models.MarketResult.home_winner_choice, 'X': models.MarketResult.draw_winner_choice, '2': models.MarketResult.away_winner_choice}
    context = {
        # 'planned_competition_events_list': planned_competition_events_list,
        # 'country_name': country_name,
        # 'competition_gnames': competition_gnames,
        'events_per_competition': events_per_competition,
        'odds_per_market_type_per_event': odds_per_market_type_per_event,
        'winner_market': winner_market,
        'winner_market_choices': winner_market_choices,

        'selected_bookmaker_name': selected_bookmaker_name,
        'bookmakers': bookmakers,

        'session': request.session,
    }
    # init_winner_odd = models.WinnerOdd.objects.get(home=2.63, draw=3.5, away=2.5)
    # winner_odd = models.WinnerOdd.objects.get(home=2.6, draw=3.4, away=2.4)
    # winner_offer_odd = models.WinnerOfferOdd.objects.filter(winner_odd=winner_odd, bookmaker=bookmaker)
    # init_timestamp = winner_offer_odd.first().timestamp
    # timestamp = init_timestamp - timezone.timedelta(hours=2)
    # winner_offer_odd.update(winner_odd=winner_odd, timestamp=timestamp)
    return TemplateResponse(request, 'games/planned_competition_events.html', context)


def send_tb_closed_signal(tb_id):
    # TODO HIGH remove this test code
    # used tbs: 128, 602
    tb = models.TotalBet.objects.get(id=tb_id)
    signal_result = gutils.utils.total_bet_closed.send_robust(sender=models.TotalBet, total_bet=tb)
    logger.debug("tb closed signal res: %s", signal_result)


# todo now check if the csrf is needed there and cache the page or it's data
# have in mind issue https://code.djangoproject.com/ticket/15855
# using the decorator the page can't be varied by cookie. It needs to be since the page contains a csrf token
# in the bookmakers form
# @cache_page(cache_time)
def pick_bets(request):
    # TODO FAVORITES select the user's favorite teams

    # country_names=['England', 'Spain', 'Greece', 'Germany', 'Italy', 'France', 'Europe', 'International', 'World'],
    # competition_names=['Premier League', 'Championship', 'La Liga', 'Copa Del Rey', 'Bundesliga', 'DFB Pokal',
    #                   'Serie A', 'Coppa Italia', 'Ligue 1', 'Coupe de France', 'Superleague', 'Football League',
    #                   'Greek Cup', 'Champions League', 'Europa League', 'Euro Qualification', 'European Championship',
    #                   'World Cup', 'WC Qualification Europe', 'WC Qualification South America', 'WC Qualification Africa']

    country_names = ['England', 'Spain', 'Greece', 'Europe', 'International', 'World']
    competition_names = ['Premier League', 'La Liga', 'Super League', 'Champions League',
                         'Europa League', 'WC Qualification Europe', 'World Cup', 'UEFA Nations League']

    if timezone.now().weekday() in [4, 5, 6]:
        # don't show CL and Europa during weekends
        country_names = ['England', 'Spain', 'Greece', 'International', 'World', 'Europe']
        competition_names = ['Premier League', 'La Liga', 'Super League', 'WC Qualification Europe', 'World Cup', 'UEFA Nations League']

    country_names.extend(['Scotland', 'Denmark'])
    competition_names.extend(['Premiership', 'Superliga', 'Playoffs 1/2', 'Playoffs 2/3', 'Playoffs 3/4',
                              'Superliga Play-offs', 'Premiership Play-Offs'])

    competitions = models.Competition.objects.filter(country__name__in=country_names, generic_name__in=competition_names)

    if not competitions:
        country_names = ['England', 'Spain', 'Greece', 'Italy', 'France', 'Germany']
        competition_names = ['Championship', 'La Liga 2', 'Serie B', 'Ligue 2']
        competitions = models.Competition.objects.filter(country__name__in=country_names,
                                                         generic_name__in=competition_names)

    competition_ids = models.Competition.ids_list(competitions)
    response = planned_competition_events(request, competition_ids)

    events_per_competition = response.context_data.get('events_per_competition')
    logger.debug('events_per_competition: %s', events_per_competition)
    if not events_per_competition:
        country_names = ['England', 'Spain', 'Greece', 'Italy', 'France', 'Germany']
        competition_names = ['Championship', 'La Liga 2', 'Serie B', 'Ligue 2']
        competitions = models.Competition.objects.filter(country__name__in=country_names,
                                                         generic_name__in=competition_names)
        competition_ids = models.Competition.ids_list(competitions)
        response = planned_competition_events(request, competition_ids)

    return response


# @cache_page(cache_time * 2)
@pjaxtend()
def all_markets_for_event(request, event_id):
    """
    It can be called with GET request from the competitions list and with POST from the bookmakers list
    """
    odds_per_market_type_for_event = {}
    market_types_with_order_per_event = {}
    winner_market_name = None
    winner_market_choices = None
    over_under_market_choices = None
    double_chance_market_name = None
    double_chance_market_choices = None
    handicap_market_choices = None
    asian_handicap_market_choices = None
    threshold_1 = None
    threshold_2 = None
    threshold_per_over_under_market_type = {}
    threshold_per_handicap_market_type = {}
    threshold_1_per_asian_handicap_market_type = {}
    threshold_2_per_asian_handicap_market_type = {}

    if event_id and int(event_id):
        selected_events = []
        try:
            event = models.Event.objects.get(id=event_id)
        except:
            raise Http404("Event does not exist")
        selected_events.append(event)

        selected_bookmaker, selected_bookmaker_name, bookmaker_added, bookmaker_updated = zakanda.utils.get_selected_bookmaker(request)
        if bookmaker_updated:
            bet_slip_events_list = sync_session_bet_slip_with_bookmaker(request, selected_bookmaker)

        if not selected_bookmaker:
            logger.error('Bookmaker with name "%s" does not exist',  selected_bookmaker_name)
            raise Http404('Bookmaker with name "{0}" does not exist'.format(selected_bookmaker_name))

        # {event_obj: {winner_market_type_obj: latest_odd_obj, over_under_market_type_obj: latest_odd_obj, ...} }
        odds_per_market_type_for_event, market_types_with_order_per_event, offer_and_thresholds_per_market_type_per_event = odds_from_events(
            selected_events, bookmaker=selected_bookmaker)
        # logger.debug('odds_per_market_type_for_event: %s' % odds_per_market_type_for_event)

        logger.info("event %s -collecting market choices and thresholds...", event_id)
        for event, odds_per_market_type in odds_per_market_type_for_event.iteritems():
            offer_and_thresholds_per_market_type_for_event = offer_and_thresholds_per_market_type_per_event[event]
            for market_type, odd_dict in odds_per_market_type.iteritems():
                logger.debug("  '%s' market type for given event has:", market_type.name)
                market_type_name = market_type.name

                offer_and_thresholds_for_market_type = offer_and_thresholds_per_market_type_for_event[market_type]
                # { market_specific_offer: [threshold_1, threshold_2] }
                for offer, thresholds in offer_and_thresholds_for_market_type.iteritems():
                    threshold_1 = thresholds[0]
                    threshold_2 = thresholds[1]
                    logger.debug("      '%s' market_specific_offer", offer)
                    logger.debug("      '%s' threshold_1, '%s' threshold_2", threshold_1, threshold_2)

                if market_type_name == models.MarketType.winner_market_type:
                    winner_market_name = market_type_name
                    winner_market_choices = {'1': models.MarketResult.home_winner_choice, 'X': models.MarketResult.draw_winner_choice, '2': models.MarketResult.away_winner_choice}

                elif market_type_name == models.MarketType.double_chance_market_type:
                    double_chance_market_name = market_type_name
                    double_chance_market_choices = {'home_draw': models.MarketResult.home_draw, 'draw_away': models.MarketResult.draw_away, 'away_home': models.MarketResult.away_home}

                elif market_type_name.find("Goals Over Under") != -1:
                    threshold_per_over_under_market_type[market_type] = threshold_1
                    over_under_market_choices = {'over': models.MarketResult.over, 'under': models.MarketResult.under}

                elif market_type_name.find("Handicap") != -1 and market_type_name.find("Asian") == -1:
                    threshold_per_handicap_market_type[market_type] = threshold_1
                    handicap_market_choices = {'home': models.MarketResult.home, 'draw': models.MarketResult.draw, 'away': models.MarketResult.away}

                elif market_type_name.find("Asian Handicap") != -1:
                    # Maybe its better to have an empty string instead of None for thresholds. Maybe useful for template
                    threshold_1_per_asian_handicap_market_type[market_type] = threshold_1
                    threshold_2_per_asian_handicap_market_type[market_type] = threshold_2
                    asian_handicap_market_choices = {'home': models.MarketResult.home, 'away': models.MarketResult.away}

                else:
                    logger.error("Unknown market_type")
    else:
        logger.error("The event_id variable of the GET request doesn't exist or it is not an integer")
        raise Http404("Event not found")

    bookmakers = models.Bookmaker.objects.all()
    context = {
        'odds_per_market_type_for_event': odds_per_market_type_for_event,
        'market_types_with_order_per_event': market_types_with_order_per_event,
        'winner_market_name': winner_market_name,
        'winner_market_choices': winner_market_choices,
        'over_under_market_choices': over_under_market_choices,
        'double_chance_market_name': double_chance_market_name,
        'double_chance_market_choices': double_chance_market_choices,
        'handicap_market_choices': handicap_market_choices,
        'asian_handicap_market_choices': asian_handicap_market_choices,
        'threshold_per_over_under_market_type': threshold_per_over_under_market_type,
        'threshold_per_handicap_market_type': threshold_per_handicap_market_type,
        'threshold_1_per_asian_handicap_market_type': threshold_1_per_asian_handicap_market_type,
        'threshold_2_per_asian_handicap_market_type': threshold_2_per_asian_handicap_market_type,

        'selected_bookmaker_name': selected_bookmaker_name,
        'bookmakers': bookmakers,

        'session': request.session,
        'object': event,
    }
    return TemplateResponse(request, 'games/all_markets_for_event.html', context)


def update_bookmaker_name_in_session(request):
    if request.method == 'POST':
        selected_bookmaker, selected_bookmaker_name, bookmaker_added, bookmaker_updated = zakanda.utils.get_selected_bookmaker(request)
        if bookmaker_updated:
            bet_slip_events_list = sync_session_bet_slip_with_bookmaker(request, selected_bookmaker)
        return HttpResponse(selected_bookmaker_name)
    raise Http404('')


def determine(item, selected_bookmaker):
    """
    if there is an odd from the given bookmaker then it returns the choice specific odd value or None
    """
    event_id = item.get('event_id', None)
    market_type_id = item.get('market_type_id', None)
    choice = item.get('choice', None)
    # original_odd = item.get('original_odd', None)
    # selected_button_text = item.get('selected_button_text', None)
    # home_team = item.get('home_team', None)
    # away_team = item.get('away_team', None)
    odd_value = None
    event = None
    market_type = None
    if event_id:
        try:
            event = models.Event.objects.get(id=event_id)
        except models.Event.DoesNotExist:
            logger.error("Event_id from session bet_slip doesn't correspond to an Event entry")
    if market_type_id:
        try:
            market_type = models.MarketType.objects.get(id=market_type_id)
        except models.MarketType.DoesNotExist:
            logger.error("market_type_id from session bet_slip doesn't correspond to a MarketType entry")
    if event and market_type and choice:
        odds = market_type.get_market_odds(event, selected_bookmaker)
        try:
            latest_market_odd = odds[-1]
            odd_value = latest_market_odd.get_odd_value(choice)
        except Exception as e:
            return odd_value
        if odd_value:
            item['original_odd'] = odd_value
    return odd_value


def sync_session_bet_slip_with_bookmaker(request, selected_bookmaker):
    """
    It updates the bet_slip items in session so that their odds are the odds of the given bookmaker
    If there is no odd available from the selected bookmaker then this item is removed from the bet_slip
    """
    logger.info("synchronizing session bet slip with bookmaker... ")
    bet_slip_events_list = request.session.get('bet_slip', [])
    if selected_bookmaker:
        bet_slip_events_list[:] = [item for item in bet_slip_events_list if determine(item, selected_bookmaker)]
        request.session['bet_slip'] = bet_slip_events_list
        # logger.debug('bet_slip in session was updated with: %s', bet_slip_events_list)
    else:
        logger.error("No bookmaker received")
    return bet_slip_events_list


