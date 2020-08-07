# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.views.decorators.cache import never_cache

import json

import utils
# from games import models as games_models
import games.models
import games.views
import forms
import logging
import zakanda.utils
import games.signals
import bet_tagging.models
import bet_tagging.utils

logger = logging.getLogger(__name__)


# TODO low create a mechanism to show a message in the bet slip
def is_event_in_bet_slip(bet_slip_event, bet_slip_events_list):
    for existing_bet_slip_event in bet_slip_events_list:
        if bet_slip_event['event_id'] == existing_bet_slip_event['event_id']:
            return True


def max_num_events_reached(bet_slip_events_list):
    if len(bet_slip_events_list) >= utils.max_num_events:
        return True


def is_event_allowed(bet_slip_event, bet_slip_events_list):
    if is_event_in_bet_slip(bet_slip_event, bet_slip_events_list):
        return False
    if max_num_events_reached(bet_slip_events_list):
        return False
    return True


# TODO HIGH You add some events to bet slip. Then you change the bookmaker.
# The events in bet slip and in session must be
# updated to match the new bookmaker who will have different odds.
# TODO LOW use cached sessions
def add_to_bet_slip(request):
    # from xmlSoccerParser import my_test
    # my_test.read()

    if request.is_ajax():
        if request.method == 'POST':
            # TODO LOW Check if the data are clean (even if there are no user input data?). Create a form for these data
            event_id = request.POST.get('event_id')
            market_type_id = request.POST.get('market_type_id')
            choice = request.POST.get('choice')
            selected_odd = request.POST.get('selected_odd')
            selected_odd = float(selected_odd)
            selected_button_text = request.POST.get('selected_button_text')
            home_team = request.POST.get('home_team')
            away_team = request.POST.get('away_team')

            # The request.session['bet_slip'] is a list of dictionaries. Each of these dictionaries contains the user
            # selected event and the related data
            # [ {'event_id':1, 'market_id': 1, 'choice':1, 'bookmaker':1, 'odd':1}, {}, {} ... {} ]
            if not request.session.get('bet_slip', None):
                bet_slip_events_list = []
            else:
                bet_slip_events_list = request.session['bet_slip']

            bet_slip_event = {}
            bet_slip_event.update({
                'event_id': event_id,
                'market_type_id': market_type_id,
                'choice': choice,
                'original_odd': selected_odd,  # it must be selected_odd in session bet slip
                'selected_button_text': selected_button_text,
                'home_team': home_team,
                'away_team': away_team,
            })

            if is_event_allowed(bet_slip_event, bet_slip_events_list):
                bet_slip_events_list.append(bet_slip_event)

            request.session['bet_slip'] = bet_slip_events_list
            # logger.debug("list to become json for response %s", bet_slip_events_list)
            return HttpResponse(json.dumps(bet_slip_events_list), content_type="application/json")
        else:
            logger.error('add to basket AJAX request is not a POST method')
    # TODO handle the non AJAX requests (probably this is for cases that the user has deactivated javascript)
    logger.error('add to basket Not an AJAX request')
    return HttpResponse('add to basket Not an AJAX request', content_type="application/json")


def remove_from_bet_slip(request):
    if request.is_ajax():
        if request.method == 'POST':
            # TODO LOW Check if the data are clean (even if there are no user input data?). Create a form for these data
            data_list = request.POST.get('data_list')
            data_list = json.loads(data_list)
            if not data_list:
                return HttpResponse('Empty')

            for item in data_list:
                event_id = item.get('event_id')
                market_type_id = item.get('market_type_id')
                choice = item.get('choice')
                original_odd = item.get('original_odd')
                original_odd = float(original_odd)
                selected_button_text = item.get('selected_button_text')
                home_team = item.get('home_team')
                away_team = item.get('away_team')

                if not request.session.get('bet_slip'):
                    logger.error("Session has no bet_slip")
                    return HttpResponse('Error! Session has no bet_slip')
                else:
                    bet_slip_events_list = request.session['bet_slip']

                bet_slip_event_for_remove = {'event_id': event_id, 'market_type_id': market_type_id, 'choice': choice,
                                             'original_odd': original_odd,'selected_button_text': selected_button_text,
                                             'home_team': home_team, 'away_team': away_team}
                logger.debug("bet slip item to remove: %s", bet_slip_event_for_remove)
                if bet_slip_event_for_remove in bet_slip_events_list:
                    bet_slip_events_list.remove(bet_slip_event_for_remove)
                    request.session['bet_slip'] = bet_slip_events_list
                    if not len(bet_slip_events_list):
                        del request.session['bet_slip']
                else:
                    logger.error('Selected bet item for removal is not in session')
            return HttpResponse('bet slip items removed from session')

        else:
            logger.error('remove from bet slip AJAX request is not POST')
            return HttpResponse('Error! remove from bet slip AJAX request is not POST')
    logger.error('remove from bet slip request is not AJAX')
    return HttpResponse('Error! remove from bet slip request is not AJAX')


@never_cache
def get_bet_slip(request):
    # never cache, so when we change the bookmaker we want the new bet_slip to be shown, not the cached one that refers
    # to the previous bookmaker
    if request.is_ajax():
        logger.debug('getting session bet slip...')
        if request.method == 'GET':
            bet_slip_events_list = []
            if request.session.get('bet_slip', None):
                bet_slip_events_list = request.session['bet_slip']
            # logger.debug("bets on bet slip: len:%d %s", len(bet_slip_events_list), bet_slip_events_list)
            return HttpResponse(json.dumps(bet_slip_events_list), content_type="application/json")
            # # patch_cache_control(response, no_cache='no-cache', no_store='no-store', must_revalidate='must-revalidate')
            # # response['Pragma'] = 'no-cache'
            # return response
        else:
            logger.error("get the bet slip only with GET")
            return HttpResponse('get the bet slip only with GET', content_type="application/json")
    else:
        logger.error("get the bet slip only with Ajax")
    return HttpResponse("get the bet slip only with Ajax", content_type="application/json")


def one_step_up_from_uri(uri):
    splitted_uri = uri.split('/')
    print('splitted_uri', splitted_uri)
    one_step_up_uri = splitted_uri[:-2]
    one_step_up_uri = '/'.join(one_step_up_uri)+'/'
    print('one_step_up_uri', one_step_up_uri)
    return one_step_up_uri


def return_empty_bet_form(request, success=None, bookmaker_name=None, template='bet_slip/place_bet_form.html'):
    # We pre-populate the form with a bookmaker name, in case the user presses the place bet in a page that doesn't
    # contain the form selection list to get the bookmaker name from. Notice that it is not a bound form. They are
    # just initial data
    if not bookmaker_name:
        selected_bookmaker, bookmaker_name, bookmaker_added, bookmaker_updated = zakanda.utils.get_selected_bookmaker(request, get_bookmaker=False)
    bet_amount_form = forms.BetAmountForm(initial={'bookmaker_name': bookmaker_name})
    context = {'bet_amount_form': bet_amount_form, 'saved_successfully': success}
    return render(request, template, context)


def create_asian_handicap_bets(bet_slip_events_list, total_bet, bet_amount):
    # function that saves a split asian handicap in 2 single_asian_handicap bets
    return None


def is_there_split_asian_handicap(bet_slip_events_list):
    split_asian_handicap_in_bet_slip = False
    for bet_slip_event_dict in bet_slip_events_list:
        market_type_id = bet_slip_event_dict.get('market_type_id')
        event_id = bet_slip_event_dict.get('event_id')
        market_type = games.models.MarketType.objects.get(id=market_type_id)
        if market_type.name.find('Asian Handicap') != -1:
            event = games.models.Event.objects.get(id=event_id)
            market_specific_offer, order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(event)
            if threshold_2:
                split_asian_handicap_in_bet_slip = True
    return split_asian_handicap_in_bet_slip


def get_bet_event(event_id, market_type_id, choice, original_odd, selected_odd):
    """
    Special handling is done for submitting past bets. If the submitted bet event doesn't exist then it is normally
    created. If a same bet event with any status (open, won etc.) exists then this is collected and used. This
    way there is no need to resettle already settled bet events. The total bet will be associated with closed
    bet events. Then only the total bet needs to be settled.
    """
    logger.debug('searching for existing bet event...')
    selections = games.models.Selection.objects.filter(original_odd=original_odd, selected_odd=selected_odd, choice=choice)
    logger.debug('selections: %s', selections)
    if not selections:
        selection = games.models.Selection.objects.create(original_odd=original_odd, selected_odd=selected_odd, choice=choice, status=games.models.Selection.open)
        bet_event, bet_event_created = games.models.BetEvent.objects.get_or_create(event_id=event_id, market_type_id=market_type_id, selection=selection)
        return bet_event, bet_event_created

    bet_event = None
    bet_event_created = False
    for selection in selections:
        try:
            logger.debug('try getting bev..')
            bet_event = games.models.BetEvent.objects.get(event_id=event_id, market_type_id=market_type_id, selection=selection)
            logger.debug('bet event found: %s', bet_event)
            break
        except games.models.BetEvent.DoesNotExist:
            continue
        except games.models.BetEvent.MultipleObjectsReturned:
            logger.warning("many identical bet_events found for event %s! Action is required!", event_id)
            bet_event = games.models.BetEvent.objects.filter(event_id=event_id, market_type_id=market_type_id, selection=selection).first()
            break
    if not bet_event:
        logger.debug('no bev with the existing selections was found, new will be created')
        selection, sel_created = games.models.Selection.objects.get_or_create(original_odd=original_odd, selected_odd=selected_odd, choice=choice, status=games.models.Selection.open)
        bet_event, bet_event_created = games.models.BetEvent.objects.get_or_create(event_id=event_id, market_type_id=market_type_id, selection=selection)
    return bet_event, bet_event_created


def create_bet_events(bet_slip_events_list):
    logger.debug("getting or creating bet events...")
    bet_events = []
    bet_events_created = []
    bet_odd = 1.
    for bet_slip_event_dict in bet_slip_events_list:
        event_id = bet_slip_event_dict.get('event_id')
        market_type_id = bet_slip_event_dict.get('market_type_id')
        choice = bet_slip_event_dict.get('choice')
        selected_odd = bet_slip_event_dict.get('original_odd')
        # Notice that the original odd is currently not stored in session bet_slip!
        original_odd = selected_odd
        bet_event, bet_event_created = get_bet_event(event_id, market_type_id, choice, original_odd, selected_odd)
        bet_odd = bet_odd * selected_odd
        bet_events.append(bet_event)
        bet_events_created.append(bet_event_created)
    return bet_events, bet_events_created, bet_odd


def create_bet(bet_amount, bet_events):
    logger.debug("creating new bet and connecting it with the given bet events...")
    if not bet_events:
        return None, None
    bet = games.models.Bet.objects.create(amount=bet_amount)
    for bet_event in bet_events:
        bet.bet_events.add(bet_event)
    # TODO is there any reason that we need to calculate the odd in bet's creation? By not doing so we can avoid the
    # recalculation of the odd during bets processing in case of void bet_events. Applies also to total_bet
    bet_odd = bet.update_odd()
    return bet, bet_odd


# TODO CLEAR CRON JOB check regularly for empty total_bets and delete them
# TODO CLEAR CRON JOB clear empty bets, total bets call this function, or periodically
def clear_empty_bets(bet, total_bet):
    if bet:
        bet_events = bet.bet_events.all()
        if not bet_events:
            bet.delete()
            # TODO BET SYSTEM check if the total bet has no bets before deleting it
            total_bet.delete()
            logger.warning("Bet %s that was just created has no associated bet_events and was DELETED", bet)
            logger.warning("Total Bet %s that was just created has no associated bets and was DELETED", total_bet)
            bet = None
            total_bet = None
    return bet, total_bet


def create_bet_tree(user, bet_slip_events_list, bookmaker, bet_amount, bet_tag, bet_description,
                    bet_description_url, date, is_past=False):
    logger.info('initiating total bet tree transaction...')
    logger.debug('user: %s, bookmaker: %s, bet_tag: %s, bet_tag_balance_snapshot: %s, date: %s (%s), '
                 'amount: %s, description: %s (%s), url: %s (%s), is_past: %s', user, bookmaker, bet_tag, bet_tag.balance,
                 date, type(date), bet_amount, bet_description, type(bet_description), bet_description_url,
                 type(bet_description_url), is_past)
    try:
        with transaction.atomic():
            current_tag_balance = bet_tag.balance
            total_bet = games.models.TotalBet.objects.create(
                user=user, bookmaker=bookmaker, bet_tag=bet_tag, bet_tag_balance_snapshot=current_tag_balance,
                date=date, amount=bet_amount, description=bet_description, url=bet_description_url, is_past=is_past)

            # TODO BET SYSTEM A function that Checks the bet system and does the following for each individual bet of the
            # "total" bet.It returns a list of "bet_slip_events_list" like lists for each bet. For each list we do the following
            # As it is now: If there is a split asian_handicap then I split the bet in two. I create one total_bet that has two
            # bets with half the bet_amount each. If there are more than one split asian_handicaps then we create multiple bets.
            # If in the future we add bet systems. Then if the user selects a bet system for 3 events (1 triple and 3 doubles)
            # then if there is a split asian_handicap we split the bet that has it in two. So in the previous case the triple
            # bet will split in two with half the amount, and 2 of the doubles will be split in two. So this total bet will have
            # 7 total bets instead of 4. First we extract the bets of the bet_system and on those bets we check for split asian.

            # split_asian_handicap_in_bet_slip = is_there_split_asian_handicap(bet_slip_events_list)
            split_asian_handicap_in_bet_slip = False
            bets = []
            if split_asian_handicap_in_bet_slip:
                # create_asian_handicap_bets(bet_slip_events_list, total_bet, bet_amount)
                bet_events = []  # just to remove the pycharm warning
                pass
            else:
                bet_events, bet_events_created, bet_events_total_odd = create_bet_events(bet_slip_events_list)
                if not bet_events:
                    # So the transaction will roll back
                    raise utils.BetEventsDontExist
                # We create a new bet only if there is no bet already connected with these bet_events
                # (with these bet_events exactly) If it is connected also with some other bet_events then a new one will be used
                bet = None
                if True not in bet_events_created:
                    # if all bet_events already existed
                    bets_with_same_bet_events = utils.get_exact_m2m_match(games.models.Bet, 'bet_events', bet_events)
                    matched_bet = utils.get_instance(games.models.Bet, bets_with_same_bet_events,
                            amount=bet_amount, odd=bet_events_total_odd)
                    bet = matched_bet
                if not bet:
                    # if bet = None or matched_bet = None
                    bet, bet_odd = create_bet(bet_amount, bet_events)
                total_bet.bets.add(bet)
                bets.append(bet)
            total_bet_odd = total_bet.update_odd()
    except Exception as e:
        logger.error("Exception on total bet creation! %s. transaction rolled back", e)
        total_bet, bets, bet_events = (None, None, None)
        return total_bet, bets, bet_events
    return total_bet, bets, bet_events


def is_valid_time(bet_slip_events_list, is_live=False):
    # todo LIVE handle live matches
    event_ids = []
    for bet_slip_event_dict in bet_slip_events_list:
        event_id = bet_slip_event_dict.get('event_id')
        event_ids.append(event_id)
    date = timezone.now()
    events = games.models.Event.objects.filter(id__in=event_ids).filter(date__lte=date)
    if events:
        return False
    return True


def is_valid_amount(bet_amount, bet_tag):
    balance = bet_tag.balance
    if bet_amount > balance:
        return False
    return True


def has_valid_odds(bet_slip_events_list):
    """ It checks if the selected odd is in the list of available odds """
    # todo live, you have to do the comparison with the latest odd before the odd changes
    for bet_slip_event in bet_slip_events_list:
        event_id = bet_slip_event.get('event_id')
        market_type_id = bet_slip_event.get('market_type_id')
        choice = bet_slip_event.get('choice')
        selected_odd = bet_slip_event.get('original_odd')
        selected_odd = float(selected_odd)
        # selected_button_text = bet_slip_event.get('selected_button_text')
        # home_team = bet_slip_event.get('home_team')
        # away_team = bet_slip_event.get('away_team')

        try:
            market_type = games.models.MarketType.objects.get(id=market_type_id)
            event = games.models.Event.objects.get(id=event_id)
        except Exception as e:
            return
        odds = market_type.get_market_odds(event)
        odd_values = []
        for odd in odds:
            odd_value = odd.get_odd_value(choice)
            if not odd_value:
                continue
            odd_values.append(odd.get_odd_value(choice))
        if selected_odd in odd_values:
            return True
    return


def are_events_compliant(bet_slip_events_list):
    events_list = list(bet_slip_events_list)
    for event in bet_slip_events_list:
        events_list.remove(event)
        # logger.debug('removed bet slip events list: %s', events_list)
        if is_event_in_bet_slip(event, events_list):
            return
    return True


def is_tb_data_valid(request, bet_slip_events_list, bet_amount, bet_tag):
    if not is_valid_amount(bet_amount, bet_tag):
        message = 'Not enough balance for this bet, please make a deposit'
        messages.warning(request, message)
        return
    if not is_valid_time(bet_slip_events_list):
        message = "Your bet isn't saved. An event has already started"
        messages.warning(request, message)
        return
    if not has_valid_odds(bet_slip_events_list):
        message = "Your bet isn't saved. Odds are not valid"
        messages.warning(request, message)
        logger.error("Your bet isn't saved. Select valid odds. bet slip events list: %s", bet_slip_events_list)
        return
    if not are_events_compliant(bet_slip_events_list):
        message = "Your bet isn't saved. Events are not compliant with each other"
        messages.warning(request, message)
        logger.error("Your bet isn't saved. Events are not compliant with each other. bet slip events list: %s", bet_slip_events_list)
        return
    return True


def submit_total_bets(request, bet_slip_events_list, bookmaker, bet_amount, bet_description, bet_description_url):
    """
    Tries to save the total bets to the db. Notice that if there are many bet_tags in the request,
    then one total_bet will be saved for each bet_tag.
    returns True is the bet has been saved successfully
    """
    bet_tags = bet_tagging.utils.get_request_bet_tags(request)
    if not bet_tags:
        # logger.warning("Attempt to save a placed total bat failed because no bet_tag was given!")
        logger.debug('no bet tag defined by user, default tag is used')
        default_bet_tag = bet_tagging.utils.get_default_bet_tag(request.user)
        bet_tags = [default_bet_tag]
        # return "Your bet hasn't been placed, please select a Bet Tag!"

    failed_tbs = []
    for bet_tag in bet_tags:
        try:
            if not is_tb_data_valid(request, bet_slip_events_list, bet_amount, bet_tag):
                return
            # todo check verified odds (mark tb as verified so that it can be identified were needed)
            total_bet, bets, bet_events = create_bet_tree(request.user, bet_slip_events_list, bookmaker, bet_amount,
                                                          bet_tag, bet_description, bet_description_url, date=timezone.now())
            signal_result = games.signals.total_bet_tree_done.send_robust(sender=games.models.TotalBet,
                                                                          total_bet=total_bet)
            logger.debug("signal_result %s", signal_result)
            if not total_bet:
                failed_tbs.append(bet_tag.name)
        except utils.BetEventsDontExist:
            logger.warning("No Bet Events could be extracted from bet slip events list in session. "
                           "The total bet transaction has been rolled back!")
            form_message = "Your bet hasn't been saved, please reload the page and try again!"
            messages.warning(request, form_message)
            return

    if not failed_tbs:
        form_message = "Your bet has been saved successfully"
        if len(bet_tags) > 1:
            form_message = "Your bets have been saved successfully"
        messages.success(request, form_message)
        return True
    else:
        failed_names = ", ".join(failed_tbs)
        form_message = "Oops, bets {} aren't saved. Please submit them again!".format(failed_names)
        messages.warning(request, form_message)
    return


# TODO login_required or user.is_authenticated check?
# TODO HIGH BOOKMAKERS FORM the bookmaker name is saved in the session like the bet_slip_items. So it might not be
# necessary to get it from the form. I can get it from the session as I do with the other bet slip item values
def save_bet_slip(request, cleaned_data):
    logger.info("saving bet using bet slip from session, amount and bookmaker from form data...")
    bet_amount = cleaned_data.get('bet_amount', None)
    bookmaker_name = cleaned_data.get('bookmaker_name', None)
    # json.loads(request.POST.get('selected_bet_tag_ids'), None)
    logger.debug("bet descr: %s, url: %s", request.POST.get("bet_description", None), request.POST.get("bet_description_url", None))
    bet_description = json.loads(request.POST.get("bet_description", None))
    bet_description_url = json.loads(request.POST.get("bet_description_url", None))
    logger.debug('  cleaned form data: bet_amount: %s, bookmaker_name: %s', bet_amount, bookmaker_name)
    try:
        bookmaker = games.models.Bookmaker.objects.get(name=bookmaker_name)
        # We take the needed values from the session
        if request.session.get('bet_slip', None):
            bet_slip_events_list = request.session['bet_slip']
            # logger.debug("  session bets slip of user [%s] %s ", request.user, bet_slip_events_list)
            if request.user.is_authenticated():
                res = submit_total_bets(request, bet_slip_events_list, bookmaker, bet_amount, bet_description, bet_description_url)
                response = return_empty_bet_form(request, success=res, bookmaker_name=bookmaker_name)
                return response
            else:
                form_message = "Please Login to place a bet!"
                messages.warning(request, form_message)
                response = return_empty_bet_form(request, bookmaker_name=bookmaker_name)
                return response
        else:
            logger.warning("There is no bet_slip in session, Bet can't be created")
            form_message = "Bet Slip is empty!"
            messages.warning(request, form_message)
            response = return_empty_bet_form(request, bookmaker_name=bookmaker_name)
            return response
    except games.models.Bookmaker.DoesNotExist:
        logger.warning("Bookmaker %s send with POST doesn't exist", bookmaker_name)
        form_message = "Bookmaker doesn't exist, Bet isn't saved"
        messages.warning(request, form_message)
        response = return_empty_bet_form(request, bookmaker_name=bookmaker_name)
        return response


# deactivate the html check to see a django not valid form
def place_bet(request):
    # from the bet slip in session I get the: event id, market id, choice and original odd to create the tb_tree
    if request.method == 'POST':
        bet_amount_form = forms.BetAmountForm(request.POST)
        if bet_amount_form.is_valid():
            # logger.debug("form data: %s", bet_amount_form.cleaned_data)
            # logger.debug("post data: %s", request.POST)
            # for k, v in request.POST.iteritems():
            #     logger.debug('%s: %s', k, v)
            # Notice that even if the bookmaker_name is valid, it doesn't mean that it's one of the existing ones.
            response = save_bet_slip(request, bet_amount_form.cleaned_data)
            return response
        else:
            bookmaker_name = request.POST.get('bookmaker_name', None)
            form_message = "Invalid data! Bet hasn't been saved"
            messages.warning(request, form_message)
            response = render(request, 'bet_slip/place_bet_form.html', {'bet_amount_form': bet_amount_form, 'form_message': form_message})
            return response
    else:
        # This is executed in any page call that the bet slip appears
        logger.debug('serving initial empty bet slip form...')
        response = return_empty_bet_form(request)
        return response