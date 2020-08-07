import logging
from django import http
from django.views.generic.base import View
import models
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from zakanda.utils import custom_pjaxtend


logger = logging.getLogger(__name__)


@custom_pjaxtend()
def transfer_request(request):
    # todo wallet If the process takes too long split it in 2 (prepare and execute)
    # to avoid pjax timeout issue or alter timeout for this call
    user_transfer_request = models.TransferRequest.objects.create(
        test=True,
        user=request.user,
        amount=6.00,
        bnf_email='pirosdummys@hotmail.com'  # given by the user
    )
    error_ulr = reverse('wallet:dashboard')
    error_message = _('Oops, something went wrong! Please try again!')
    success_message = _('Funds withdrawn successfully!')
    transfer_status_report = user_transfer_request.prepare_and_execute()
    if not transfer_status_report:
        messages.error(request, error_message)
        return HttpResponseRedirect(error_ulr)
    messages.success(request, success_message)

    wallet_history = request.user.profile.wallet_history()
    # wallet_balance = request.user.profile.wallet_balance
    context = {"wallet_history": wallet_history}
    return TemplateResponse(request, 'wallet/dashboard.html', context)


class StatusReportView(View):
    """ The Skrill server continues to post the status until a response of HTTP OK (200) is received
    from your server or the number of posts exceeds 10 """
    def post(self, request, *args, **kwargs):
        logger.debug("Skrill Transaction Status Report posted data: %s", request.POST)
        error_response = http.HttpResponse(status=406)  # a random non 200 status is used
        try:
            payment_request = models.PaymentRequest.objects.get(pk=request.POST['transaction_id'])
            if not payment_request.status_response_received:
                payment_request.status_response_received = True
                payment_request.save()
        except Exception as e:
            logger.error("Status Report transaction_id error. %s", e)
            return error_response
        report = models.StatusReport()
        try:
            report.pay_to_email = request.POST['pay_to_email']
            report.pay_from_email = request.POST['pay_from_email']
            report.merchant_id = request.POST['merchant_id']
            report.customer_id = request.POST.get('customer_id', None)
            report.mb_transaction_id = request.POST['mb_transaction_id']
            report.mb_amount = request.POST['mb_amount']
            report.mb_currency = request.POST['mb_currency']
            report.status = request.POST['status']
            report.failed_reason_code = request.POST.get('failed_reason_code', None)
            report.md5sig = request.POST['md5sig']
            report.sha2sig = request.POST.get('sha2sig', None)
            report.amount = request.POST['amount']
            report.currency = request.POST['currency']
            report.neteller_id = request.POST.get('neteller_id', None)
            report.payment_type = request.POST.get('payment_type', None)
            report.merchant_fields = request.POST.get('merchant_fields', None)
            report.field_1 = request.POST.get('Field1', None)
            report.field_2 = request.POST.get('Field2', None)
            report.field_3 = request.POST.get('Field3', None)
            report.field_4 = request.POST.get('Field4', None)
            report.field_5 = request.POST.get('Field5', None)
        except Exception as e:
            logger.exception('%s', e)
            return error_response
        report.payment_request = payment_request
        report.valid = report.is_valid()
        try:
            report, created = models.StatusReport.objects.get_or_create(
                payment_request=payment_request,
                pay_to_email=report.pay_to_email,
                pay_from_email=report.pay_from_email,
                merchant_id=report.merchant_id,
                customer_id=report.customer_id,
                # transaction_id=report.transaction_id,
                mb_transaction_id=report.mb_transaction_id,
                mb_amount=report.mb_amount,
                mb_currency=report.mb_currency,
                status=report.status,
                failed_reason_code=report.failed_reason_code,
                md5sig=report.md5sig,
                sha2sig=report.sha2sig,
                amount=report.amount,
                currency=report.currency,
                neteller_id=report.neteller_id,
                payment_type=report.payment_type,
                merchant_fields=report.merchant_fields,
                valid=report.valid,
                field_1=report.field_1,
                field_2=report.field_2,
                field_3=report.field_3,
                field_4=report.field_4,
                field_5=report.field_5,
            )
            if created:
                logger.info("New StatusReport created: %s [for transaction id: %s]", report, payment_request.transaction_id)
                # messages.success(request, _("Payment completed successfully"))  # doesn't have an effect
            else:
                # report.updated_at = timezone.now()
                # report.save()
                logger.debug("StatusReport already exists: %s [for transaction id: %s]", report, payment_request.transaction_id)
        except Exception as e:
            logger.exception('StatusReport get_or_create exception: %s', e)
            # todo payment status additional action is needed (send signal)
            return error_response
        return http.HttpResponse()
