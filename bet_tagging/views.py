
import logging
import json
from django.utils import timezone
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, DeleteView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.template.response import TemplateResponse
from django.db import IntegrityError
from zakanda.utils import cbv_pjaxtend, custom_pjaxtend
from zakanda.settings import NormalizationMethods
import bet_tagging.utils
import bet_statistics.utils
import gutils.utils
import models
import forms
from zakanda.settings import SessionKeys, GetParams
# from djpjax import pjaxtend
# from django.template.response import TemplateResponse, HttpResponseRe
from django.http import Http404, HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
import skrill.models
from skrill.settings import skrill_to_skrill_fees

logger = logging.getLogger(__name__)


class BetTagsList(ListView):
    template_name = 'bet_tagging/bet_tags_list.html'
    model = models.BetTag
    context_object_name = 'bet_tags'
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        # it's better to do the initialization here (since the request is assigned to self in the  dispatch method)
        # Prior to dispatch (in init) request is not available.
        target_user_id = self.kwargs.get('target_user_id', None)
        target_user = get_object_or_404(User, pk=target_user_id)
        self.target_user = target_user
        self.show_in_money_mode = gutils.utils.show_in_money_mode(request, target_user)
        return super(BetTagsList, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        target_user = self.target_user
        if not target_user.is_authenticated():
            return models.BetTag.objects.none()
        bet_tags = models.BetTag.objects.filter(owner=target_user)
        for bet_tag in bet_tags:
            if not self.show_in_money_mode:
                unit = bet_statistics.utils.calc_user_unit(target_user)
                norm_values = bet_statistics.utils.normalize_values(unit, bet_tag.balance)
                bet_tag.balance = norm_values[0]
            try:
                nc = bet_tag.notification_subscriptions.get(user=self.request.user)
                bet_tag.user_notification_subscription = nc
            except Exception as e:
                # if you see your own bet groups or if you see the bet groups of someone that you don't follow
                # or if it is a private bet group
                logger.debug('%s', e)
                bet_tag.user_notification_subscription = None
            bet_tag.subscribed = False
            # logger.debug("%s subscribers: %s", bet_tag, bet_tag.get_active_subscribers())
            if self.request.user.is_authenticated() and self.request.user.profile.is_subscribed(bet_tag):
                bet_tag.subscribed = True
        return bet_tags

    def get_context_data(self, **kwargs):
        context = super(BetTagsList, self).get_context_data(**kwargs)
        context['target_user'] = self.target_user
        context['qs_normalized'] = GetParams.normalized
        if not self.show_in_money_mode:
            context['normalization_method'] = NormalizationMethods.unit
        return context

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(BetTagsList, self).get(request, *args, **kwargs)
        return resp


class SelectBetDetails(BetTagsList):
    # this view populates the Select Bet Tags modal
    template_name = 'bet_tagging/select_bet_details.html'

    def dispatch(self, request, *args, **kwargs):
        logger.debug("dispatching...")
        target_user = self.request.user
        self.target_user = target_user
        self.show_in_money_mode = True  # on bt details modal always show not normalized values
        return super(BetTagsList, self).dispatch(request, *args, **kwargs)


class BetTagDetail(DetailView):
    template_name = 'bet_tagging/bet_tag_detail.html'
    model = models.BetTag
    context_object_name = 'bet_tag'

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(BetTagDetail, self).get(request, *args, **kwargs)
        return resp


# class BetTagCreate(CreateView):
#     template_name = 'bet_tagging/bet_tag_form.html'
#     form_class = forms.BetTagForm
#     # context_object_name = 'bet_group_form'
#
#     @cbv_pjaxtend()
#     def get(self, request, *args, **kwargs):
#         logger.debug("get to bet tag")
#         resp = super(BetTagCreate, self).get(request, *args, **kwargs)
#         return resp
#
#     @cbv_pjaxtend()
#     def post(self, request, *args, **kwargs):
#         logger.debug("post to bet tag")
#         resp = super(BetTagCreate, self).post(request, *args, **kwargs)
#         return resp
#
#     def get_success_url(self):
#         success_url = reverse('bet_tagging:bet_tags_list', kwargs={'target_user_id': self.request.user.id})
#         return success_url
#
#     # def get_form_kwargs(self):
#     #     # Build the keyword arguments required to instantiate the form. Apart from the post data we
#     #     # pass "user" keyword argument with the current user to the form
#     #     kwargs = super(BetTagCreate, self).get_form_kwargs()
#     #     kwargs['owner'] = self.request.user
#     #     return kwargs
#
#     def get_form(self, form_class=None):
#         # instantiates the form with the kwargs from get_form_kwargs
#         bet_group_form = super(BetTagCreate, self).get_form()
#         # Notice that we manually add the attribute owner to the form instance because we want to validate the
#         # unique_together constraint applied on the BetTag model of this modelForm. The owner field is excluded
#         # from the form so the unique_together can't be checked. For this reason we overwritten form's clean method
#         # to check it. The clean method needs the owner field so we add it to the form instance here.
#         bet_group_form.owner = self.request.user
#         return bet_group_form
#
#     def form_valid(self, form):
#         logger.debug("valid form")
#         # saves the form and redirects to get_success_url()
#         # a valid form respects the unique together constraint too, so the bet_tag that will be
#         # created from this form for the specific user will be unique
#         bet_tag = form.save(commit=False)
#         bet_tag.owner = self.request.user
#         bet_tag.save()
#         # bet_tag.add_to_session(self.request)
#         self.object = bet_tag
#         return HttpResponseRedirect(self.get_success_url())


class BetTagDelete(DeleteView):
    # TODO BetTag Close instead of Delete notice that if tbs are moved to another bet tag,
    # then the tbs_bet_tag_amount_snapshot of the tb, will
    # remain the same and the stats that are calc from it will reflect the stats of the bets as they were in their
    # original bet tag. So probably I must replace delete with close action
    # Closed bet Tag: not available for new bets, withdraw
    # in post redirects to success url in get returns the template
    model = models.BetTag
    template_name = 'bet_tagging/bet_tags_list.html'

    def get_context_data(self, **kwargs):
        context = super(BetTagDelete, self).get_context_data(**kwargs)
        target_user = self.request.user
        bet_tags = models.BetTag.objects.filter(owner=target_user)
        context['bet_tags'] = bet_tags
        return context

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)
        # return super(BetTagDelete, self).get(request, *args, **kwargs)

    @cbv_pjaxtend()
    def post(self, request, *args, **kwargs):
        return super(BetTagDelete, self).post(request, *args, **kwargs)

    def get_success_url(self):
        success_url = reverse('bet_tagging:bet_tags_list', kwargs={'target_user_id': self.request.user.id})
        return success_url

    def delete(self, request, *args, **kwargs):
        # self.object.remove_from_session(request)
        tag_to_be_deleted = self.get_object()
        if tag_to_be_deleted.is_default:
            # we protect the default tag from deletion
            success_url = self.get_success_url()
            return HttpResponseRedirect(success_url)
        # Assignment to default tag must be done before the bet_tag is deleted, in order to protect
        # its total_bets (that have a foreign key to this bet_tag). So this action can't be done
        # asynchronously on its own because the deletion of the bet_tag might happen first. So
        # only the whole delete method can be done asynchronously.
        bet_tagging.utils.set_tbs_to_default_tag(tag_to_be_deleted)
        # TODO on bet tag delete create automatically a withdrawal of its balance (or move it to default)
        # now its balance is added to the default tag
        bet_tagging.utils.add_balance_to_default_tag(tag_to_be_deleted)
        return super(BetTagDelete, self).delete(request, *args, **kwargs)


@custom_pjaxtend()
@login_required()
def bet_group_create(request):
    return bet_group_edit(request, pk=None)


@custom_pjaxtend()
@login_required()
def bet_group_edit(request, pk):
    """ Creates or Edits bet groups and services. If the posted data describe a non premium bet group then
    only the bet group is saved (the service related post data are not used). If the posted dara are for
    a premium bet group then the service data are used to save the services. """
    if not pk:
        # bet group create view
        bet_group = None
    else:
        try:
            bet_group = models.BetTag.objects.get(pk=pk)
        except Exception as e:
            raise Http404('%s', e)
        if request.user != bet_group.owner:
            raise Http404('Bet group %s does not belong to user %s', bet_group, request.user)

    duration_30 = models.Service.duration_30
    duration_90 = models.Service.duration_90

    service_30 = None
    service_90 = None
    if bet_group:
        services = bet_group.services.all()
        if services:
            try:
                # if bet_group is premium or was premium then services already exist for it
                # get them to initialize the forms with them
                service_30 = services.get(duration=models.Service.duration_30)
                service_90 = services.get(duration=models.Service.duration_90)
            except Exception as e:
                raise Http404("%s", e)

    if request.method == 'POST':
        logger.debug("form post data: %s", request.POST)
        if bet_group:
            bet_group_form = forms.BetTagForm(request.POST, instance=bet_group)
            bet_group_form.obj_pk = bet_group.pk  # obj_pk is used in form validation
        else:
            # owner is needed by the validation process (by the clean_type specifically). So a temp bet group is used
            temp_bet_group = models.BetTag(owner=request.user)
            bet_group_form = forms.BetTagForm(request.POST, instance=temp_bet_group)
        bet_group_form.owner = request.user
        if request.POST['type'] != models.BetTag.premium:
            # if not Premium (either in create or update process)
            # initialize the service forms just so that they exist in the template in case a user switches to premium
            service_form_30 = forms.ServiceForm(initial={'duration': duration_30}, prefix=duration_30)
            service_form_90 = forms.ServiceForm(initial={'duration': duration_90}, prefix=duration_90)
            if bet_group_form.is_valid():
                bet_group_form.save()
                messages.success(request, _('Your Bet Group was updated successfully'))
            else:
                messages.warning(request, _('Something went wrong!'))
        else:
            # if Premium (either in create or update process)
            # duration field is disabled so it isn't in the posted data
            request.POST['30-duration'] = duration_30
            request.POST['90-duration'] = duration_90
            service_form_30 = forms.ServiceForm(request.POST, instance=service_30, prefix=duration_30)
            service_form_90 = forms.ServiceForm(request.POST, instance=service_90, prefix=duration_90)
            if bet_group_form.is_valid() and service_form_30.is_valid() and service_form_90.is_valid():
                # In creation process bet_group doesn't exist so it must be created to be used in the services
                bet_group = bet_group_form.save()
                service_30 = service_form_30.save(commit=False)
                service_90 = service_form_90.save(commit=False)
                service_30.bet_group = bet_group
                service_90.bet_group = bet_group
                service_30.save()
                service_90.save()
                messages.success(request, _('Your Bet Group and Services were updated successfully'))
            else:
                messages.warning(request, _('Something went wrong!'))

    else:
        if bet_group:
            bet_group_form = forms.BetTagForm(instance=bet_group)
        else:
            # owner is needed by the validation process (by the clean_type specifically). So a temp bet group is used
            temp_bet_group = models.BetTag(owner=request.user)
            bet_group_form = forms.BetTagForm(instance=temp_bet_group)
        bet_group_form.owner = request.user
        if (bet_group and bet_group.type != models.BetTag.premium) or not bet_group:
            service_form_30 = forms.ServiceForm(initial={'duration': duration_30}, prefix=duration_30)
            service_form_90 = forms.ServiceForm(initial={'duration': duration_90}, prefix=duration_90)
        else:  # if bet_group and bet_group.type == models.BetTag.premium:
            service_form_30 = forms.ServiceForm(instance=service_30, prefix=duration_30)
            service_form_90 = forms.ServiceForm(instance=service_90, prefix=duration_90)

    context = {
        'object': bet_group,
        'bet_group_form': bet_group_form,
        'service_form_30': service_form_30,
        'service_form_90': service_form_90,
    }
    return TemplateResponse(request, 'bet_tagging/bet_tag_form.html', context=context)


class ServiceList(ListView):
    template_name = 'bet_tagging/service_list.html'
    model = models.Service
    context_object_name = 'services'

    def dispatch(self, request, *args, **kwargs):
        # it's better to do the initialization here (since the request is assigned to self in the  dispatch method)
        # Prior to dispatch (in init) request is not available.
        bet_group_id = self.kwargs.get('bet_group_id', None)
        try:
            bet_group = models.BetTag.objects.get(pk=bet_group_id)
        except Exception as e:
            raise Http404('%s', e)
        if request.user == bet_group.owner:
            raise Http404("You can't subscribe to your own bet groups")
        bet_group.subscribed = False
        if self.request.user.is_authenticated() and self.request.user.profile.is_subscribed(bet_group):
            bet_group.subscribed = True
        self.bet_group = bet_group
        return super(ServiceList, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        bet_group = self.bet_group
        services = bet_group.services.all()
        return services

    def get_context_data(self, **kwargs):
        context = super(ServiceList, self).get_context_data(**kwargs)
        context['bet_group'] = self.bet_group
        return context

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(ServiceList, self).get(request, *args, **kwargs)
        return resp

# class BetTagEdit(UpdateView):
#     template_name = 'bet_tagging/bet_tag_form.html'
#     model = models.BetTag
#     form_class = forms.BetTagForm
#
#     @method_decorator(login_required)
#     def dispatch(self, *args, **kwargs):
#         if self.get_object().owner != self.request.user:
#             raise Http404
#         return super(BetTagEdit, self).dispatch(*args, **kwargs)
#
#     @cbv_pjaxtend()
#     def get(self, request, *args, **kwargs):
#         logger.debug("get to bet tag")
#         resp = super(BetTagEdit, self).get(request, *args, **kwargs)
#         return resp
#
#     @cbv_pjaxtend()
#     def post(self, request, *args, **kwargs):
#         logger.debug("post to bet tag")
#         resp = super(BetTagEdit, self).post(request, *args, **kwargs)
#         return resp
#
#     def get_success_url(self):
#         success_url = reverse('bet_tagging:bet_tags_list', kwargs={'target_user_id': self.request.user.id})
#         return success_url
#
#     def get_form(self, form_class=None):
#         # instantiates the form with the kwargs from get_form_kwargs
#         form = super(BetTagEdit, self).get_form()
#         # Notice that we manually add the attribute owner to the form instance because we want to validate the
#         # unique_together constraint applied on the BetTag model of this modelForm. The owner field is excluded
#         # from the form so the unique_together can't be checked. For this reason we overwritten form's clean method
#         # to check it. The clean method needs the owner field so we add it to the form instance here.
#         form.owner = self.request.user
#         editing_bet_tag_pk = self.kwargs.get("pk", None)
#         form.obj_pk = editing_bet_tag_pk
#         return form
#
#     def form_valid(self, form):
#         logger.debug("valid form")
#         # saves the form and redirects to get_success_url()
#         # a valid form respects the unique together constraint too, so the bet_tag that will be
#         # created from this form for the specific user will be unique
#         bet_tag = form.save(commit=False)
#         # logger.debug("initial bet tag: %s", bet_tag.name)
#         bet_tag.owner = self.request.user
#         bet_tag.save()
#         self.object = bet_tag
#         # editing_bet_tag_pk = self.kwargs.get("pk")
#         # if editing_bet_tag_pk:
#         #     models.BetTag.objects.filter(pk=editing_bet_tag_pk).update(**form.cleaned_data)
#
#         return HttpResponseRedirect(self.get_success_url())


@custom_pjaxtend()
def make_default_view(request, bet_group_id):
    target_user = request.user
    try:
        bet_group = models.BetTag.objects.get(id=bet_group_id)
        if bet_group.owner != target_user:
            logger.error("user %s wants to change the default bet group %s of user %s", target_user, bet_group_id, bet_group.owner)
            raise Http404
        bet_group.make_default()
    except Exception as e:
        logger.warning("There is no bet group with id: %s, %s", bet_group_id, e)
        raise Http404
    url = reverse('bet_tagging:bet_tags_list', kwargs={'target_user_id': target_user.id})
    if not request.session.get(SessionKeys.money_mode, False):
        url = url + '?' + GetParams.normalized
    return HttpResponseRedirect(url)


def total_balance(request):
    balance = 0
    user = request.user
    if not user.is_authenticated():
        return HttpResponse(json.dumps(balance), content_type="application/json")
    if request.method == 'GET':
        for bet_tag in user.bet_tags.all():
            balance += bet_tag.balance
    jsoned = json.dumps(balance)
    return HttpResponse(jsoned, content_type="application/json")


# class BetTagForm(FormView):
#     template_name = 'bet_tagging/bet_tag_form.html'
#     form_class = forms.BetTagForm
#
#     def get_success_url(self):
#         success_url = reverse('bet_tagging:bet_tags_list', kwargs={'target_user_id': self.request.user.id})
#         return success_url
#
#     def form_valid(self, form):
#         return super(BetTagForm, self).form_valid(form)

def initial_form_data(self):
    bet_tag_id = self.request.GET.get('bet_tag', None)
    if bet_tag_id:
        try:
            bet_group = models.BetTag.objects.get(id=bet_tag_id)
        except:
            bet_group = bet_tagging.utils.get_default_bet_tag(self.request.user)
    else:
        bet_group = bet_tagging.utils.get_default_bet_tag(self.request.user)
    initial = {'bet_tag': bet_group}
    return initial


class DepositWithdrawalCreate(SuccessMessageMixin, CreateView):
    action = None

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(DepositWithdrawalCreate, self).dispatch(*args, **kwargs)

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        logger.debug("get to make %s", self.action)
        resp = super(DepositWithdrawalCreate, self).get(request, *args, **kwargs)
        return resp

    @cbv_pjaxtend()
    def post(self, request, *args, **kwargs):
        logger.debug("post to make %s", self.action)
        resp = super(DepositWithdrawalCreate, self).post(request, *args, **kwargs)
        return resp

    def get_form_kwargs(self):
        # the form will be instantiated using the kwargs. We add user and initial keys in kwargs
        kwargs = super(DepositWithdrawalCreate, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        initial = initial_form_data(self)
        kwargs['initial'] = initial
        return kwargs

    def get_success_url(self):
        # success_url = reverse('bet_tagging:deposits_list', kwargs={'target_user_id': self.request.user.id})
        success_url = reverse('bet_tagging:bet_tags_list', kwargs={'target_user_id': self.request.user.id})
        return success_url

    def form_valid(self, form):
        logger.debug("valid form")
        # saves the form and redirects to get_success_url()
        entry = form.save(commit=False)
        # entry.user = self.request.user
        if entry.bet_tag.owner != self.request.user:
            # it can't be placed in dispatch since the modelform has no queryset and so no get_object() which
            # means that we can'at access the deposit or the withdrawal in order to get the owner. I could
            # move this check in the form validation check (in form's clean method)
            raise Http404
        entry.date = timezone.now()
        entry.save()
        logger.debug("saved entry: %s", entry)
        self.object = entry
        messages.success(self.request, '{} was successful'.format(self.action))
        return HttpResponseRedirect(self.get_success_url())


class DepositCreate(DepositWithdrawalCreate):
    template_name = 'bet_tagging/deposit_form.html'
    form_class = forms.DepositForm
    action = 'Deposit'


class WithdrawalCreate(DepositWithdrawalCreate):
    template_name = 'bet_tagging/withdraw_form.html'
    form_class = forms.WithdrawalForm
    action = 'Withdrawal'


class DepositList(ListView):
    template_name = 'bet_tagging/deposits_list.html'
    model = models.Deposit
    context_object_name = 'bet_tags'
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        # it's better to do the initialization here (since the request is assigned to self in the  dispatch method)
        # Prior to dispatch (in __init__) request is not available.
        target_user_id = self.kwargs.get('target_user_id', None)
        target_user = get_object_or_404(User, pk=target_user_id)
        self.target_user = target_user
        return super(DepositList, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if not self.target_user.is_authenticated():
            return models.Deposit.objects.none()
        # deposits = models.Deposit.objects.filter(user=self.target_user)
        bet_tags = models.BetTag.objects.filter(owner=self.target_user)
        return bet_tags

    def get_context_data(self, **kwargs):
        context = super(DepositList, self).get_context_data(**kwargs)
        target_user = self.target_user
        context['target_user'] = target_user
        if not gutils.utils.show_in_money_mode(self.request, target_user):
            unit = bet_statistics.utils.calc_user_unit(target_user)
            for bet_tag in context['bet_tags']:
                deposits = bet_tag.deposits.all()
                for deposit in deposits:
                    norm_values = bet_statistics.utils.normalize_values(unit, deposit.amount)
                    deposit.amount = norm_values[0]
        return context

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(DepositList, self).get(request, *args, **kwargs)
        return resp


class NotificationSubscriptionEdit(UpdateView):
    template_name = 'bet_tagging/notif_subscription_edit.html'
    model = models.NotificationSubscription
    form_class = forms.NotificationSubscriptionForm

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        if self.get_object().user != self.request.user:
            raise Http404
        return super(NotificationSubscriptionEdit, self).dispatch(*args, **kwargs)

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(NotificationSubscriptionEdit, self).get(request, *args, **kwargs)
        return resp

    @cbv_pjaxtend()
    def post(self, request, *args, **kwargs):
        resp = super(NotificationSubscriptionEdit, self).post(request, *args, **kwargs)
        return resp

    def get_success_url(self):
        success_url = reverse('bet_tagging:bet_tags_list', kwargs={'target_user_id': self.get_object().bet_group.owner.id})
        return success_url


@login_required()
def payment_request(request, service_id):

    # raise 404 for the case that someone finds a way to call the view despite the fact that its links are disabled
    from django.http import Http404
    raise Http404

    try:
        service = models.Service.objects.get(id=service_id)
    except Exception as e:
        logger.error('A service for which a payment was about to be made, does not exist')
        raise Http404('%s', e)
    user = request.user
    bet_group = service.bet_group
    service_onwer = bet_group.owner
    if request.user == service_onwer:
        logger.error("You can't pay for your own service")
        raise Http404

    if user.profile.is_subscribed(bet_group):
        logger.error('User %s is already subscribed to bet group %s', user, bet_group)
        raise Http404(_('You are already subscribed to this Bet Group'))

    user_payment_request = skrill.models.PaymentRequest(
        user=user,
        # pay_from_email='pirosdummys@hotmail.com',
        amount=service.price,
        test=True,
        payment_methods='ACC,WLT,PSC,NTL',
        detail1_description='Tipster: {}, Bet_group: {}'.format(service_onwer.username, bet_group.name),
        detail1_text='Subscription for {} days'.format(service.duration),
        Field1="service",
        Field2=service_id,
    )
    error_url = reverse('bet_tagging:service_list', kwargs={'bet_group_id': bet_group.id})
    error_message = _('Oops, something went wrong! Please try again!')
    try:
        skrill_url = user_payment_request.submit()
        if not skrill_url:
            messages.error(request, error_message)
            return HttpResponseRedirect(error_url)
    except Exception as e:
        logger.exception('Error in skrill payment request. %s', e)
        messages.error(request, error_message)
        return HttpResponseRedirect(error_url)
    return HttpResponseRedirect(skrill_url)


@custom_pjaxtend()
@login_required()
def buyer_dashboard(request):
    user = request.user
    active_subscriptions = user.subscriptions.filter(active=True)
    inactive_subscriptions = user.subscriptions.filter(active=False)
    # payments = user.profile.get_wallet_deposits()
    context = {
        'active_subscriptions': active_subscriptions,
        'inactive_subscriptions': inactive_subscriptions,
        # 'payments': payments,
    }
    return TemplateResponse(request, 'bet_tagging/buyer_dashboard.html', context=context)


@custom_pjaxtend()
@login_required()
def seller_dashboard(request):
    # user = gutils.utils.get_user(user_id)
    # if not user:
    #     raise Http404
    # if user != request.user:
    #     raise Http404
    user = request.user
    bet_groups = user.bet_tags.filter(type=models.BetTag.premium)
    active_services = models.Service.objects.filter(bet_group__in=bet_groups).filter(subscriptions__active=True).distinct()
    for service in active_services:
        service.past_subscribers = service.subscribers.count() - service.active_subscribers().count()
    next_payment_amount = user.profile.due_fuds()
    monthly_turnover = user.profile.monthly_turnover()
    tier = user.profile.seller_info().percentage_tier
    fees = skrill_to_skrill_fees(next_payment_amount)
    # payments = user.profile.get_wallet_withdrawals()
    context = {
        'active_services': active_services,
        'next_payment_amount': next_payment_amount,
        'monthly_turnover': monthly_turnover,
        'tier': tier,
        'fees': fees,
        # 'payments': payments,
    }
    return TemplateResponse(request, 'bet_tagging/seller_dashboard.html', context=context)
