# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import json
import bet_tagging.models
import games.models
from zakanda.settings import SessionKeys


logger = logging.getLogger(__name__)


def create_default_bet_tag(user):
    # name = user.username+'_'+bet_tagging.models.BetTag.default_name
    name = user.username
    description = "This Bet Group has been created by zakanda. All bets for which you haven't defined a Bet Group " \
                  "belong to this Bet Group. You can rename it and change the description, but you can not delete it."
    try:
        default_bet_tag, created = bet_tagging.models.BetTag.objects.get_or_create(
            owner=user, name=name, description=description, is_default=True
        )
        if not created:
            logger.error("Default Bet Tag %s for user %s already exist!", default_bet_tag, user)
        logger.debug("default bet tag created: %s", default_bet_tag)
    except bet_tagging.models.BetTag.MultipleObjectsReturned:
        logger.error("User $s has more than one default Bet Tags! The fist one is used", user)
        default_bet_tag = bet_tagging.models.BetTag.objects.filter(owner=user, name=name,
                                                                   description=description, is_default=True).first()
    return default_bet_tag


def get_default_bet_tag(user):
    try:
        default_bet_tag = bet_tagging.models.BetTag.objects.get(owner=user, is_default=True)
    except bet_tagging.models.BetTag.MultipleObjectsReturned:
        logger.error("User $s has more than one default Bet Tags! The fist one is used", user)
        default_bet_tag = bet_tagging.models.BetTag.objects.filter(owner=user, is_default=True).first()
    except bet_tagging.models.BetTag.DoesNotExist:
        logger.error("User %s has no default Bet Tag!", user)
        default_bet_tag = create_default_bet_tag(user)
    return default_bet_tag


def add_balance_to_default_tag(bet_tag_to_change):
    user = bet_tag_to_change.owner
    default_bet_tag = get_default_bet_tag(user)
    balance_to_add = bet_tag_to_change.balance
    current_def_balance = default_bet_tag.balance
    default_bet_tag.balance = current_def_balance + balance_to_add
    default_bet_tag.save()


def set_tbs_to_default_tag(bet_tag_to_change):
    """ The bet tag of the total bets that are related with the given tag are set to user's default bet tag """
    user = bet_tag_to_change.owner
    default_bet_tag = get_default_bet_tag(user)
    total_bets = games.models.TotalBet.objects.filter(bet_tag=bet_tag_to_change)
    total_bets.update(bet_tag=default_bet_tag)


def get_request_bet_tags(request):
    """
    if the request is POST the bet tag is extracted from the POST data. If there are no selected tags in the post
    data then bet tag is extracted from the session. In get it is extracted from the session. I can
    remove the selected bet tag ids form the post data and just get it from session. No reason to have them.
    """
    bet_tags = bet_tagging.models.BetTag.objects.none()
    bet_tag_ids = []
    if request.method == 'POST':
        # Notice that if the user has not pressed the bet details the modal is not shown and no bet tag is selected
        # In this case I get the bet tag from the session
        bet_tag_ids = json.loads(request.POST.get('selected_bet_tag_ids'), None)
        if not bet_tag_ids:
            active_bet_tag_id = request.session.get(SessionKeys.active_bet_tag_id, None)
            bet_tag_ids.append(active_bet_tag_id)
    else:
        active_bet_tag_id = request.session.get(SessionKeys.active_bet_tag_id, None)
        bet_tag_ids.append(active_bet_tag_id)

    if bet_tag_ids:
        bet_tags = bet_tagging.models.BetTag.objects.filter(id__in=bet_tag_ids)
        # logger.debug("selected bet tags: %s", bet_tags)
    return bet_tags


class BetTagTemp():
    def __init__(self, user_id, bet_tag_name, bank_growth, total_balance, bet_deposits, user_deposits, real_deposits, open_tbs_amount):
        self.user_id = user_id
        self.bet_tag_name = bet_tag_name
        self.closed_bet_deposits = bet_deposits
        self.user_deposits = user_deposits
        self.real_deposits = real_deposits
        self.open_tbs_amounts = open_tbs_amount
        self.bank_growth = bank_growth
        self.total_balance = total_balance

    def __unicode__(self):
        return 'BetTagTemp {0}'.format(self.bet_tag_name)
