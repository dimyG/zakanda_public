import logging
# from django.shortcuts import render
# from django.contrib.auth.models import User
from django.template.response import TemplateResponse
from djpjax import pjaxtend
from django.contrib.auth.decorators import login_required
# from skrill import api_client
# from django.http import HttpResponse, HttpResponseRedirect, Http404
# from django.contrib import messages
# from django.utils import timezone
# from django.utils.translation import ugettext_lazy as _
# from django.core.urlresolvers import reverse
# from bet_tagging.models import Service


logger = logging.getLogger(__name__)


@login_required
@pjaxtend()
def dashboard(request):

    # raise 404 for the case that someone finds a way to call the view despite the fact that its links are disabled
    from django.http import Http404
    raise Http404

    # todo handle this asynchronous status creation:
    # during the skrill 10 times reposting, let the user know that that the transaction is currently
    # processed (waiting confirmation) so that he doesn't repay. At successful completion inform him
    # and do what is needed (show that he is subscribed) easiest way to do this currently is to
    # reload the page (??redirect to it in signal??) You can check it by turning the WIFI off and On

    # todo If even after the 10 times reposting the transaction is still shady, handle it
    # get users latest payment_request and if it is a shady one resubmit it. This is to handle the rare case
    # in which a payment has been completed but we got no status report for it due to some error.
    # this action must be initiated (before) the page the user is redirected to after a payment, so that
    # he sees the updated information

    # user = request.user
    # time_delta = timezone.now() - timezone.timedelta(minutes=3)
    # try:
    #     latest_payment_request = user.paymentrequest_set.filter(created_at__gt=time_delta).latest('created_at')
    #     if latest_payment_request and latest_payment_request.is_shady():
    #         logger.debug("asking a status repost of shady payment request %s...", latest_payment_request)
    #         client = api_client.MerchantQueryInterface()
    #         client.status_repost(latest_payment_request.transaction_id)
    # except Exception as e:  # there are no requests
    #     logger.debug("%s", e)
    #     pass

    wallet_history = request.user.profile.wallet_history()
    context = {"wallet_history": wallet_history}
    return TemplateResponse(request, 'wallet/dashboard.html', context=context)
