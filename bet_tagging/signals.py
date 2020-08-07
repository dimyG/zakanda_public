import logging
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
# from django_rq import job
import models
import bet_statistics.signals
import bet_tagging.utils
# import bet_tagging.models
import gutils.utils

logger = logging.getLogger(__name__)
# TODO update the cache when user changes bet_tags (a feature to be added)


# @job('default', result_ttl=0, timeout=2*60)
# def pre_del_sequence(user_id, bet_tag_id_to_delete):
#     user = User.objects.get(id=user_id)
#     bet_tag = bet_tagging.models.BetTag.objects.get(id=bet_tag_id_to_delete)
#     bet_tagging.utils.set_tbs_to_default_tag(bet_tag)
#     bet_statistics.signals.update_user_cache(user_id)


# @receiver(pre_save, sender=models.BetTag, dispatch_uid="bet_tag_pre_save")
# def bet_tag_pre_save(sender, instance, **kwargs):
    # only if the name was updated is the cache update necessary,
    # since the total bet json bet_tags key, contains only the names of the bet tags
    # try:
    #     existing_bet_tag = models.BetTag.objects.get(pk=instance.pk)
    # except models.BetTag.DoesNotExist:
    #     return  # new bet tag is to be created
    # if not existing_bet_tag.name == instance.name:
    #     # bet tag exists and it's name is to be updated. Notice that since this is a pre_save
    #     # the delayed execution might happen before saving, so the new value would not be used!
    #     user_id = instance.owner.id
    #     bet_statistics.signals.update_user_cache.delay(user_id)


@receiver(post_save, sender=models.BetTag, dispatch_uid="bet_tag_post_save")
def bet_tag_post_save(sender, instance, created, **kwargs):
    if created:
        if not instance.type == models.BetTag.free:
            # for premium they are created on bet_group subscribe (follow), private have none
            return
        models.bet_group_create_handle_job.delay(instance.id)


@receiver(post_delete, sender=models.BetTag, dispatch_uid="bet_tag_post_delete")
def bet_tag_post_delete(sender, instance, **kwargs):
    user_id = instance.owner.id
    bet_statistics.signals.update_user_cache.delay(user_id)


# @receiver(pre_delete, sender=models.BetTag, dispatch_uid="bet_tag_pre_delete")
# def bet_tag_pre_delete(sender, instance, **kwargs):
#     user = instance.owner
#     logger.debug("pre delete - user %s to delete bet tag %s", user, instance)
#     bet_tagging.utils.set_to_default_tag(user, instance)

@gutils.utils.disable_for_loaddata
@receiver(post_save, sender=models.Deposit, dispatch_uid="deposit_made")
def deposit_made(sender, instance, created, **kwargs):
    if instance.is_calculated:
        # If the deposit is a calculated one, then the balance must not be updated
        # since it is already set to 0
        return
    if created:
        # actually the update balance just adds the deposit amount to the bet group balance, so it's
        # not a real update. if you modify the amount of an existing deposit, you need to really update the
        # bet_groups balance. Never modify the amount od a deposit (you would need to subtract the amount
        # from balance and add the new value). Make a withdrawal instead.
        instance.update_balance()


@gutils.utils.disable_for_loaddata
@receiver(post_save, sender=models.Withdrawal, dispatch_uid="withdrawal_made")
def withdrawal_made(sender, instance, created, **kwargs):
    if created:
        # Never modify the amount of a withdraw (or deposit). If it is an old entry that has subsequent
        # bets, then the bet_tag_balance_snapshot of subsequent total bets must be updated too.
        instance.update_balance()
