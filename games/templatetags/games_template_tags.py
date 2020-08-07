# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from collections import OrderedDict
from django import template
import games.models as models
from gutils.views import try_cache_first
from gutils.utils import get_user

register = template.Library()
logger = logging.getLogger(__name__)


@try_cache_first(timeout=60*60*48)
def get_ordered_competitions():
    hard_order_competitions_by_country = OrderedDict()
    default_order_competitions_by_country = OrderedDict()

    ordered_country_names = ['England', 'Spain', 'Germany', 'Italy', 'France', 'Europe', 'International', 'World',
                             'Greece']
    for country_name in ordered_country_names:
        try:
            country = models.Country.objects.get(name=country_name)
            if country.competitions.count() == 0:
                continue
        except Exception as e:
            logger.warning('%s', e)
            continue
        competitions = list(models.Competition.objects.filter(country=country))
        competitions.sort(key=lambda x: x.generic_name)
        competitions.insert(0, 'dummy_entry')
        hard_order_competitions_by_country[country_name] = competitions

    competitions_by_country = dict()
    countries = models.Country.objects.exclude(competitions=None)
    for country in countries:
        if country.name in ordered_country_names:
            # the ordered countries have already been added to the dictionary
            continue
        competitions = list(models.Competition.objects.filter(country=country))
        competitions.sort(key=lambda x: x.generic_name)
        competitions.insert(0, 'dummy_entry')
        competitions_by_country[country.name] = competitions
    default_order_competitions_by_country = OrderedDict(sorted(competitions_by_country.items()))

    for k, v in default_order_competitions_by_country.iteritems():
        hard_order_competitions_by_country[k] = v

    return hard_order_competitions_by_country


# The left_sidebar inclusion tag is used to render the sports_list.html template. This was done in order to simplify
# the creation of the sidebar. If we didn't use this custom tag, then every time that the sports_list.html template was
# rendered it would need the "competitions_by_country" dictionary on the context of the view that calls it. And since
# the template was included in the base.html, every time the base was extended by another template, the
# "competitions_by_country" dictionary would have to be passed to the respective context
@register.inclusion_tag('left_sidebar/sports_list.html', takes_context=True)
def sports_list(context):
    # the first entries of the lists are dummy entries added due to a bug in the template

    hard_order_competitions_by_country = get_ordered_competitions()

    # TODO default bookmaker from user settings or sponsored default bookmaker
    request = context.get('request')
    selected_bookmaker_name = context.get('selected_bookmaker_name')
    # note that the request object is the full page load request. Subsequent pjax/ajax requests will not
    # update the request object that is available to the side bar template.
    session = request.session
    logger.debug("SESSION: %s", session.items())
    return {
        'competitions_by_country': hard_order_competitions_by_country,
        'request': request,
        'selected_bookmaker_name': selected_bookmaker_name,
    }


# Notice: The right sidebar is loaded after the left and after the content block because it follows them in the base.
# Have this in mind in case you add the bookmakers list in the right sidebar. If you do it then have in mind the
# sequence of events when you change a selection. Check if the content that you see in the left and main content are
# for the updated selected bookmaker.
# @register.inclusion_tag('right_sidebar.html', takes_context=True)
# def right_sidebar(context):
#     request = context['request']
#     # bookmakers = models.Bookmaker.objects.all()
#     # selected_bookmaker, selected_bookmaker_name = zakanda.generic_functions.get_selected_bookmaker(request, get_bookmaker=False)
#     # we return the "original" request to the right_sidebar, because we want to use it there
#     # tags_context = {'request': request, 'bookmakers': bookmakers, 'selected_bookmaker_name': selected_bookmaker_name}
#     tags_context = {'request': request}
#     return tags_context

@register.simple_tag
def url_replace(request, field, value):
    """
    # It creates or replaces a query string parameter of a GET request
    # I used this template tag for the bookmaker selection. When you change a bookmaker from the list, it calls the planned
    # events view.We need to show the odds from the new bookmaker so we change the GET selected_bookmaker_name query string
    # parameter. I think that it isn't used anymore since the bookmaker list is now a POST request
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.assignment_tag
def user_from_id(user_id):
    try:
        obj = get_user(int(user_id))
    except Exception as e:
        logger.warning('%s', e)
        obj = None
    return obj


@register.assignment_tag
# todo django 1.9 replace assignment_tag with simple_tag
def total_bet_from_id(tb_id):
    try:
        obj = models.TotalBet.objects.get(id=int(tb_id))
    except Exception as e:
        logger.warning('%s', e)
        obj = None
    return obj
