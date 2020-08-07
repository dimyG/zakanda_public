# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.dispatch import Signal
from django.db.models.signals import post_save
from django.dispatch import receiver
import django_rq
import games.models
import games.utils
from zakanda.db import get_bet_events
from bet_statistics.signals import update_user_cache
from feeds.signals import create_total_bet_tree_related_activities
import feeds.models
import gutils.utils


logger = logging.getLogger(__name__)

total_bet_tree_done = Signal(providing_args=["total_bet"])


# @receiver(post_save, sender=games.models.TotalBet, dispatch_uid="create_total_bet")
# def total_bet_signal(sender, instance, created, **kwargs):
#     """
#     Have in mind that the post_save signal will be emitted even if the total_bet tree transaction rolls back
#     """
#     if created:
#         user = instance.user
#         update_cached_user_tbs_df_with_open_tbs.delay(user)


@receiver(gutils.utils.total_bet_closed, sender=games.models.TotalBet, dispatch_uid="total_bet_closed")
def total_bet_closed_signal(sender, total_bet, **kwargs):
    logger.debug('total bet %s was settled, post settlement actions will follow...', total_bet.id)
    total_bet.update_balance()
    # user cache is not updated by the signal. The cache of all users whose the total bets were settled is
    # updated in bulk by the settlement function.
    # user_id = total_bet.user.id
    # update_user_cache(user_id)


def ordered_execution_actions(total_bet_id):
    """
    if the total bet is a "past bet" then followers are not notified
    Some functions need to wait for some other function to finish
    """
    logger.debug("ordered execution actions...")
    total_bet = games.models.TotalBet.get(total_bet_id)
    if not total_bet:
        logger.error("total bet %s doesn't exist, no emails will be sent", total_bet_id)
        return
    if total_bet.is_past:
        logger.info("total bet %s is a past one, no emails will be sent", total_bet_id)
        return
    email_queue = django_rq.get_queue("emails")  # it can't be pickled so can't be stored in redis as argument
    email_queue.enqueue(games.utils.send_tb_mails, total_bet_id, result_ttl=0)


@receiver(total_bet_tree_done, sender=games.models.TotalBet, dispatch_uid="total_bet_tree_done")
def tb_tree_done_signal(sender, total_bet, **kwargs):
    """
    If the total_bet is not None, then the total_bet_tree transaction has been committed.
    If tb transaction is committed the related activities must be created.
    """
    # TODO django version on_commit django 1.9 use the on_commit to do things after the transaction has been
    # successfully committed now I do it with a custom total_bet_tree_done signal
    if not total_bet:
        logger.warning("no total_bet tree created, no post action is executed!")
        return
    # user = total_bet.user
    user_id = total_bet.user.id
    total_bet_id = total_bet.id
    logger.info("user %s submitted total_bet %s tree successfully", user_id, total_bet_id)
    total_bets = [total_bet]
    bet_events = get_bet_events(total_bets).select_related('event', 'market_type', 'selection__choice')
    default_queue = django_rq.get_queue("default")

    total_bet.update_balance()
    # TODO django version rq pickles the job, but it doesn't add a django version key when it does so.
    # Django doesn't guarantee
    # that unpickling in another version will work. So I need to check if manually pickling the job arguments works
    # default_queue.enqueue(create_total_bet_activity, user_id, total_bet, result_ttl=0)
    # default_queue.enqueue(create_bet_event_activities, user_id, total_bet, bet_events, result_ttl=0)
    default_queue.enqueue(update_user_cache, user_id, result_ttl=0)
    default_queue.enqueue(create_total_bet_tree_related_activities, user_id, total_bet, bet_events, result_ttl=0)
    default_queue.enqueue(ordered_execution_actions, total_bet_id, result_ttl=0)


@gutils.utils.disable_for_loaddata
@receiver(post_save, sender=games.models.BetEvent, dispatch_uid="create_bet_event")
def bet_event_signal(sender, instance, created, **kwargs):
    """
    Have in mind that the post_save signal will be emitted even if the total_bet tree transaction rolls back.
    This means that the RawBetEvent will be created no matter if the BetEvent has been created or not.
    """
    event = instance.event
    market_type = instance.market_type
    choice = instance.selection.choice
    raw_bet_event, raw_created = feeds.models.RawBetEvent.objects.get_or_create(
        event=event, market_type=market_type, choice=choice
    )
    if not raw_created:
        return
    logger.debug("raw bet event %s was created successfully", raw_bet_event)