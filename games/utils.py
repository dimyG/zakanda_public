from __future__ import unicode_literals
import json
from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone
from django.db import IntegrityError
import logging
import models
import naming
import deleting_entries
from django.contrib.sites.models import Site
from django.template.defaultfilters import pluralize
from zakanda.db import get_bet_events
import emails.utils

logger = logging.getLogger(__name__)


# ------------------------------------------------------
# TESTS
# ------------------------------------------------------
# maybe I can delete it or add it in unit tests eventually
def test_team_creation(request):
    team_xmlsoccer_name = 'Aberdeen'
    team, team_created = models.Team.objects.get_or_create(generic_name=team_xmlsoccer_name)
    team_info, team_info_created = models.TeamInfo.objects.create(
        team=team,
        source=models.Source.objects.get(name=naming.source_names[0]),
        sname=team_xmlsoccer_name,
        sid=45,
        timestamp=timezone.now()
    )
    team_info.save()
    context = {}
    return render(request, 'gutils/index.html', context)


def test_wrong_choice(request):
    season = models.Season.objects.get_or_create(name='55555')
    context = deleting_entries.collect_entries()
    return render(request, 'gutils/index.html', context)


def simple_test(request):
    try:
        latest_event = models.Event.objects.latest('date')
    except models.Event.DoesNotExist:
        latest_event = 'DoesNotExist'
    return HttpResponse(latest_event)
# ------------------------------------------------------
# END TESTS
# ------------------------------------------------------


def create_bookmakers_info():
    source_name = 'xmlSoccer'
    source = models.Source.objects.get(name=source_name)
    bookmakers = models.Bookmaker.objects.all()
    for bookmaker in bookmakers:
        bookmaker_name = bookmaker.name
        try:
            bookmaker_info = models.BookmakerInfo(bookmaker=bookmaker, source=source, sname=bookmaker_name)
            bookmaker_info.save()
        except IntegrityError:
            print("Integrity error on bookmaker {} used for the current OfferTree creation".format(bookmaker))


def create_countries_info():
    source_name = 'xmlSoccer'
    source = models.Source.objects.get(name=source_name)
    countries = models.Country.objects.all()
    for country in countries:
        country_name = country.name
        try:
            country_info = models.CountryInfo(country=country, source=source, sname=country_name)
            country_info.save()
        except IntegrityError:
            print("Integrity error on country {}".format(country))


def create_sports_info():
    source_name = 'xmlSoccer'
    source = models.Source.objects.get(name=source_name)
    sports = models.Sport.objects.all()
    for sport in sports:
        sport_name = sport.name
        try:
            sport_info = models.SportInfo(sport=sport, source=source, sname=sport_name)
            sport_info.save()
        except IntegrityError:
            print("Integrity error on country {}".format(sport))


# REMOVE RESULT FROM EVENT (in case of decision result removal more actions are needed)
def remove_result():
    source = models.Source.objects.get(name=naming.source_names[0])
    event = models.Event.latest_event_from_sid(event_sid=360080, source=source)
    print(event)
    print('results', event.results.all())
    for result in event.results.all():
        print(result, 'id', result.id, 'ft', result.ft_result, 'et', result.et_result, 'pen', result.pen_result, 'f', result.final)
        event.results.remove(result)
        event.status = models.Event.not_started
        event.save()
        # handle its marketTypes (reassign then an Open MarketResult)
        # handle its bet events (reassign them an Open selection)
        # handle its bets (status open, return 0)
        # handle its total_bets (status open, return 0)
        # probably the best option is to return the values in event's pre-processing state, and then run the event
        # processing normally with the new result)
    print(event)


def add_decision_date():
    total_bets = models.TotalBet.objects.all()
    for total_bet in total_bets:
        decision_date = total_bet.calculate_decision_date(method="Passive")
        total_bet.decision_date = decision_date
        print(decision_date)
        total_bet.save()


def get_tb_email_notification_mailgun_params(total_bet_id):
    """
    The given total_bet is to be send as email to the tipster followers. The function calculates
    the parameters for mailgun sending. Notice that we add some temp attributes to the total_bet and
    tipster model instances
    """
    from_arg, sender, to_list, subject, text, html, text_template, html_template, context, recipient_variables = \
        None, None, None, None, None, None, None, None, None, None

    total_bet = models.TotalBet.get(total_bet_id)
    if not total_bet:
        logger.error("Email notifications weren't send! (invoked for total bet id: %s)", total_bet_id)
        return from_arg, sender, to_list, subject, text, html, text_template, html_template, context, recipient_variables
    total_bets = [total_bet, ]
    num_tbs_to_send = len(total_bets)

    bet_tag = total_bet.bet_tag
    tipster = total_bet.user
    tipster.tbs_to_send = total_bets
    logger.debug("tipsters tbs to sent: %s ", len(tipster.tbs_to_send))
    bet_events = get_bet_events(total_bets, distinct=False, exclude_open=False)
    total_bet.bet_events = bet_events
    total_bet.expected_profit = total_bet.calculate_expected_profit()

    # user_tbs, user_tbs_df = bet_statistics.views.calc_user_total_bets_df(tipster, exclude_open=False, start_date=None, end_date=None)
    # temp_tag_per_tag_names, total_balance = bet_statistics.utils.calc_balance_per_tags(user_tbs_df)
    # ## stats = bet_statistics.views.calculate_total_bets_stats(user_tbs_df)
    # ## temp_tag_per_tag_names = stats.get("temp_tag_per_tag_names", None)
    # tag_balance = temp_tag_per_tag_names[bet_tag.name].total_balance

    tag_balance = bet_tag.balance
    if tag_balance > 0:
        tag_balance_before_current_tb = tag_balance + total_bet.amount
        total_bet.amount_per_cent = (total_bet.amount / tag_balance_before_current_tb)*100
    else:
        # if the balance is 0 then it means that the current bet amount was bigger than the available balance
        # and this is currently translated as 100% of the balance (it means that the user deposit an amount
        # and bet it all). I can present these cases using normalized units instead of per cent
        total_bet.amount_per_cent = 100

    recipients = bet_tag.get_recipients(email=True)
    if not recipients:
        return from_arg, sender, to_list, subject, text, html, text_template, html_template, context, recipient_variables
    if len(recipients) >= 1000:
        # split list or use mailing lists
        # TODO IMPORTANT The maximum number of recipients allowed for Batch Sending is 1,000.
        logger.error("maximum number of recipients for batch sending reached!")
        recipients = recipients[:1000]

    to_list = []
    recipient_variables = {}
    for follower in recipients:
        to_list.append(follower.email)
        recipient_values = {
            "username": follower.username,
            "id": follower.id,
        }
        recipient_variables[follower.email] = recipient_values
    recipient_variables = json.dumps(recipient_variables)

    subject = '%recipient.username% you have {} new tip{}'.format(len(total_bets), pluralize(len(total_bets)))
    text_template = 'emails/tbs_submitted.txt'
    html_template = 'emails/tbs_submitted_styled.html'
    domain = Site.objects.get_current().domain
    context = {'tipsters': [tipster, ], 'num_tbs_to_send': num_tbs_to_send, 'domain': domain}
    # logger.debug("mailgun parameters created: %s", (from_arg, sender, to_list, subject, text, html, text_template, html_template, context, recipient_variables))
    return from_arg, sender, to_list, subject, text, html, text_template, html_template, context, recipient_variables


def send_tb_mails(total_bet_id, to_list_arg=None, recipient_variables_arg=None):
    logger.info("sending emails for total bet %s ...", total_bet_id)
    from_arg, sender, to_list, subject, text, html, text_template, html_template, context, recipient_variables = \
        get_tb_email_notification_mailgun_params(total_bet_id)
    if to_list_arg:
        to_list = to_list_arg  # just for testing
    if recipient_variables_arg:
        recipient_variables = recipient_variables_arg  # just for testing
    if not to_list:
        logger.debug('There is no recipients, no emails will be sent')
        return
    # logger.debug('email to list: %s', to_list)
    # res = None
    res = emails.utils.mailgun_send(
        to_list, subject, text_template, html_template, context, recipient_variables, from_arg, sender, text, html)
    logger.debug("send mailgun mails function returned %s", res)
