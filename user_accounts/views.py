# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator
from django.views.decorators.http import last_modified
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.contrib.auth.models import User
from django.template.response import TemplateResponse, HttpResponse
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.utils.http import http_date
import time
# from zakanda.settings import cache_time
import models
import games.models
from zakanda.utils import cbv_pjaxtend
from zakanda.settings import SessionKeys, old_date
import forms
import utils

import logging
from djpjax import pjaxtend
from django_rq import job
from actstream.models import following, followers
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger(__name__)


def profile(request):
    context = {}
    return render(request, 'user_accounts/profile.html', context)


class UsersList(ListView):
    template_name = 'user_accounts/users_list.html'
    model = User
    context_object_name = 'users'
    # paginate_by = 4

    def get_queryset(self):
        relation = self.kwargs.get('relation', None)  # this way we are defining a default value for an argument
        user_pk = self.kwargs.get('user_pk', None)
        if user_pk:
            user = get_object_or_404(User, pk=user_pk)
            if relation == 'Followers':
                users = followers(user)
            elif relation == 'Following':
                users = following(user, User)
            else:
                users = User.objects.all().select_related('basic_stats')
        else:
            users = User.objects.all().select_related('basic_stats')
        return users

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(UsersList, self).get(request, *args, **kwargs)
        return resp


class Leaderboard(ListView):
    """ Identical to UsersList changed only for caching. It would probably change more for datatables performance """
    template_name = 'user_accounts/users_list.html'
    model = User
    context_object_name = 'users'

    @classmethod
    def get_users(cls):
        users = User.objects.all().exclude(total_bets=None).exclude(id=360).exclude(
            basic_stats__score__lte=0).select_related('basic_stats')
        return users

    def dispatch(self, request, *args, **kwargs):
        def latest_entry(request, *args, **kwargs):
            """ last-modified header: basic stats latest update (basic stats are updated in submit bet, close bet, follow etc.)
            Notice that if you place a bet and instantly visit the leaderboard there is a chance that the cached stats
            have not been updated yet by the worker so that the new response contains the cached old data. Then there
            must be a new bet so that the last-modified changes and the user gets the new response"""
            try:
                latest_update = models.BasicStats.objects.latest('updated_at').updated_at
            except Exception as e:
                latest_update = timezone.now()
            return latest_update

        @last_modified(latest_entry)
        def _dispatch(request, *args, **kwargs):
            return super(Leaderboard, self).dispatch(request, *args, **kwargs)
        return _dispatch(request, *args, **kwargs)

    def get_queryset(self):
        users = self.get_users()
        # this approach was replaced with a db table
        # stats = UserProfile.users_stats()
        # # import sys
        # # logger.debug('size of stats: %s, users list: %s', sys.getsizeof(stats), sys.getsizeof(users))
        # for user in users:
        #     user.stats = stats[user.id]
        return users

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(Leaderboard, self).get(request, *args, **kwargs)
        cache_duration = 60 * 2
        # with expires and must-revalidate the browser returns the cached page within expires
        # and after that, it asks the server (gets 304 or new response).
        # resp['Expires'] = http_date(time.time() + cache_duration)
        # Expires not set because Follow/Unfollow actions added and they modify the html so the cached
        # version is not valid
        resp['Cache-Control'] = "must-revalidate"
        return resp


@job
def long_calc():
    res = 0
    logger.debug('start long calculation...')
    for i in range(int(1e5)):
        for j in range(int(1e3)):
            res += 1
    logger.debug('done. result: %s' % res)
    return res


class UserDetailView(DetailView):
    template_name = 'user_accounts/user_detail.html'
    model = games.models.User
    context_object_name = 'user'

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        user = context[self.context_object_name]
        user.res = 0
        # user.res = long_calc()
        job = long_calc.delay()
        # scheduler = django_rq.get_scheduler('default')
        logger.debug('now %s', timezone.datetime.now())
        # job = scheduler.enqueue_at(timezone.datetime.now()+timezone.timedelta(minutes=1), long_calc)
        # r = requests.get('http://www.in.gr')
        # print(r.headers['content-type'], r.status_code)
        return context

    @cbv_pjaxtend()
    def get(self, request, *args, **kwargs):
        resp = super(UserDetailView, self).get(request, *args, **kwargs)
        return resp


@pjaxtend(parent='base.html', pjax_parent='left_sidebar/pjax_left_sidebar_base.html')
def left_sidebar_sports_list(request):
    # url = reverse(left_sidebar_sports_list)
    return TemplateResponse(request, 'left_sidebar/sports_list_left_sidebar.html', context={})


@never_cache
@pjaxtend(parent='base.html', pjax_parent='left_sidebar/pjax_left_sidebar_base.html')
def left_sidebar_user_info(request, user_pk):
    target_user = get_object_or_404(User, pk=user_pk)
    following_list, followers_list = utils.follow_relations(target_user, User)
    premium_bet_groups = target_user.profile.premium_bet_groups()
    for bet_group in premium_bet_groups:
        bet_group.subscribed = False
        if request.user.is_authenticated() and request.user.profile.is_subscribed(bet_group):
            bet_group.subscribed = True
    context = {
        "target_user": target_user,
        "following": following_list,
        "followers": followers_list,
        'premium_bet_groups': premium_bet_groups,
    }
    return TemplateResponse(request, 'left_sidebar/user_info_left_sidebar_only.html', context=context)


@login_required()
@pjaxtend()
def edit_profile(request, user_id):
    # TODO MESSAGE return your profile has been updated message
    if not request.user.id == int(user_id):
        logger.debug("request user %s, user %s", request.user.id, user_id)
        raise Http404
    user = get_object_or_404(User, id=user_id)
    logger.debug("editing profile of user %s", user)
    try:
        user_profile = user.profile
        if request.POST:
            user_prof_form = forms.UserProfileForm(request.POST, instance=user_profile)
            user_prof_form.save()
            messages.success(request, 'Your profile was updated successfully!')
        else:
            user_prof_form = forms.UserProfileForm(instance=user_profile)
    except AttributeError:
        logger.error("user %s has no associated user profile object!", user)
        raise Http404
    context = {'form': user_prof_form}
    return TemplateResponse(request, 'user_accounts/edit_profile.html', context=context)


def handle_seller_settings_request(request, user_profile, form_class):
    try:
        if form_class == forms.LegalSellerForm:
            seller_info = user_profile.legal_seller_info
        elif form_class == forms.PersonSellerForm:
            seller_info = user_profile.person_seller_info
        else:
            raise Http404
        if request.POST:
            seller_form = form_class(request.POST, instance=seller_info)
            if seller_form.is_valid():
                seller_form.save()
                messages.success(request, _('Your profile was updated successfully!'))
            else:
                messages.warning(request, _("Data are missing, profile was not updated!"))
        else:
            seller_form = form_class(instance=seller_info)
    except AttributeError:
        if request.POST:
            seller_form = form_class(request.POST)
            if seller_form.is_valid():
                seller_info = seller_form.save(commit=False)
                seller_info.profile = user_profile  # manually add the user_profile field
                seller_info.save()
                messages.success(request, _('Your profile was updated successfully!'))
            else:
                messages.warning(request, _("Data are missing, profile was not updated!"))
        else:
            seller_form = form_class()
    return seller_form


@login_required()
@pjaxtend()
def seller_settings(request, user_id):
    """ A post request can save either a LegalSellerInfo or a PersonSellerInfo. What will it save is decided
    by what post parameters are posted. """
    if not request.user.id == int(user_id):
        logger.debug("request user %s, user %s", request.user.id, user_id)
        raise Http404
    user = get_object_or_404(User, id=user_id)
    try:
        user_profile = user.profile
    except AttributeError:
        logger.error("user %s has no associated user profile object!", user)
        raise Http404
    try:
        # check if legal seller settings are posted. In this case return the existing person_seller_info
        # or an empty one
        posted_legal_name = request.POST['legal_name']
        legal_seller_form = handle_seller_settings_request(request, user_profile, forms.LegalSellerForm)
        try:
            person_seller_info = user_profile.person_seller_info
            person_seller_form = forms.PersonSellerForm(instance=person_seller_info)
        except AttributeError:
            person_seller_form = forms.PersonSellerForm()
    except Exception:
        person_seller_form = handle_seller_settings_request(request, user_profile, forms.PersonSellerForm)
        try:
            legal_seller_info = user_profile.legal_seller_info
            legal_seller_form = forms.LegalSellerForm(instance=legal_seller_info)
        except AttributeError:
            legal_seller_form = forms.LegalSellerForm()
    context = {'legal_seller_form': legal_seller_form, 'person_seller_form': person_seller_form}
    return TemplateResponse(request, 'user_accounts/seller_settings.html', context=context)


def stats_mode(request):
    """ Sets the money_mode session value """
    if request.is_ajax():
        state = request.GET['state']
        if state == 'true':
            session_value = True
        elif state == 'false':
            session_value = False
        else:
            logger.warning('Unknown stats mode value, value is handled as: true')
            session_value = True
        request.session[SessionKeys.money_mode] = session_value
        return JsonResponse(data={}, status=200)
    return JsonResponse(data={}, status=400)