import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
import django.dispatch
from skrill.models import StatusReport, TransferStatusReport
import gutils.utils


logger = logging.getLogger(__name__)


skrill_status_chargeback = django.dispatch.Signal(providing_args=["instance"])
skrill_status_failed = django.dispatch.Signal(providing_args=["instance"])
skrill_status_cancelled = django.dispatch.Signal(providing_args=["instance"])
skrill_status_pending = django.dispatch.Signal(providing_args=["instance"])
skrill_status_processed = django.dispatch.Signal(providing_args=["instance"])


@gutils.utils.disable_for_loaddata
@receiver(post_save, sender=StatusReport, dispatch_uid="status_report_post_save")
def status_report_signal(sender, instance, created, **kwargs):
    logger.debug("status_report_post_save signal received...")
    if created:
        if not instance.valid:
            # todo payment status additional action is needed (send signal)
            # ask for a new status response using the API (critical if status is processed)
            # if processed make a refund? send email to admin to manually invoke the process by sending the signal?
            return
        status = instance.status
        if status == -3 or status == "-3":
            skrill_status_chargeback.send(sender=sender, instance=instance)
        elif status == -2 or status == "-2":
            skrill_status_failed.send(sender=sender, instance=instance)
        elif status == -1 or status == "-1":
            skrill_status_cancelled.send(sender=sender, instance=instance)
        elif status == 0 or status == "0":
            skrill_status_pending.send(sender=sender, instance=instance)
        elif status == 2 or status == "2":
            skrill_status_processed.send(sender=sender, instance=instance)
        else:
            logger.error("unknown status_report status value %s (%s)", str(status), type(status))


skrill_transfer_status_scheduled = django.dispatch.Signal(providing_args=["instance"])
skrill_transfer_status_processed = django.dispatch.Signal(providing_args=["instance"])


@gutils.utils.disable_for_loaddata
@receiver(post_save, sender=TransferStatusReport, dispatch_uid="transfer_status_report_post_save")
def transfer_status_report_signal(sender, instance, created, **kwargs):
    logger.debug("transfer_status_report_post_save signal received...")
    if created:
        status = instance.status
        # transfer_request = instance.transfer_request
        # transfer_request.transferstatusreport_set.exclude(instance).filter()
        if status == 1 or status == "1":
            skrill_transfer_status_scheduled.send(sender=sender, instance=instance)
        elif status == 2 or status == "2":
            skrill_transfer_status_processed.send(sender=sender, instance=instance)
        else:
            logger.error("unknown transfer_status_report status value %s (%s)", str(status), type(status))
