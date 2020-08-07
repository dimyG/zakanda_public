import logging
# from django.dispatch import receiver
# from django.http import HttpResponseRedirect
# from django.utils import timezone
from actstream.actions import follow
from skrill.signals import *
import bet_tagging.models


logger = logging.getLogger(__name__)


@receiver(skrill_status_chargeback, dispatch_uid="skrill_status_chargeback")
def status_chargeback(sender, instance, **kwargs):
    logger.debug("skrill_status_chargeback")
    # remove the amount from user's wallet.
    # (since it is charged back from zakanda skrill account to the user's skrill account)
    # If the money has been already spent by the user, then zakanda takes the loss
    # (or we can remove the amount from tipster's reward, so that the tipster takes the loss)
    return


@receiver(skrill_status_failed, dispatch_uid="skrill_status_failed")
def status_failed(sender, instance, **kwargs):
    logger.debug("skrill_status_failed")
    return


@receiver(skrill_status_cancelled, dispatch_uid="skrill_status_cancelled")
def status_cancelled(sender, instance, **kwargs):
    logger.debug("skrill_status_cancelled")
    return


@receiver(skrill_status_pending, dispatch_uid="skrill_status_pending")
def status_pending(sender, instance, **kwargs):
    logger.debug("skrill_status_pending")
    # schedule call to get the status again? Or skrill will send a post request when is processed?
    return


@receiver(skrill_status_processed, dispatch_uid="skrill_status_processed")
def status_processed(sender, instance, **kwargs):
    logger.debug("skrill_status_processed")
    # user = instance.payment_request.user
    # user.profile.deposit_to_wallet(instance)
    # user.profile.spend_from_wallet(instance)
    subscription = bet_tagging.models.Subscription.create_subscription_tree(instance)
    if not subscription:
        logger.error('subscription was not created [status report: %s]', instance)
        return
    follow_obj = follow(subscription.user, subscription.service.bet_group.owner)
    return


# Transfer Status Report Start
@receiver(skrill_transfer_status_processed, dispatch_uid="skrill_transfer_status_processed")
def transfer_status_processed(sender, instance, **kwargs):
    logger.debug("skrill_transfer_status_processed")
    # user = instance.transfer_request.user
    # user.profile.withdraw_from_wallet(instance)
    # todo make django commands to withdraw and deposit to wallet (without the actual skrill transactions)
    # to deal with the case of processed transactions that have not been properly processed by zakanda
    # no wallet functionality so not necessary
    return


@receiver(skrill_transfer_status_scheduled, dispatch_uid="skrill_transfer_status_scheduled")
def transfer_status_scheduled(sender, instance, **kwargs):
    logger.debug("skrill_transfer_status_scheduled")
    # user = instance.transfer_request.user
    # user.profile.withdraw_from_wallet(instance)
    return
# Transfer Status Report End


withdraw_excess_wallet_balance = django.dispatch.Signal(providing_args=["withdraw_amount", "excess_amount"])


@receiver(withdraw_excess_wallet_balance, dispatch_uid="withdraw_excess_wallet_balance")
def excess_withdraw(sender, instance, withdraw_amount, excess_amount, **kwargs):
    logger.debug("withdraw_excess_wallet_balance")
    # Instance can be either transfer_status or payment_status
    # Normally this should never happen
    # todo wallet create a DB entry for the excess amount,
    # referencing the transfer_status_report (instance) that created it
