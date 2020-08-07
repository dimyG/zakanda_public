from __future__ import unicode_literals
import cProfile
import functools
import json
import logging
from datetime import datetime
import games.models
# import games.views  # There was import errors if I used the games.views due to circular dependencies
import games.naming
import pytz
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.utils import timezone
from settings import Dummies
from storages.backends.s3boto3 import S3Boto3Storage

# from user_accounts.views import follow_relations

logger = logging.getLogger(__name__)

StaticRootS3Boto3Storage = lambda: S3Boto3Storage(location='static')  # bucket_name/static
MediaRootS3Boto3Storage = lambda: S3Boto3Storage(location='media')  # bucket_name/static
# # ProtectedRootS3Boto3Storage = lambda: S3Boto3Storage(location='protected')  # my_bucket_name/protected


def datetime_format(start_date, end_date, to_timezone, to_format):
    pytz_timezone = pytz.timezone(to_timezone)
    start_date_in_tz = start_date.astimezone(pytz_timezone)
    start_date_in_tz_formatted = start_date_in_tz.strftime(to_format)
    end_date_in_tz = end_date.astimezone(pytz_timezone)
    end_date_in_tz_formatted = end_date_in_tz.strftime(to_format)
    return start_date_in_tz_formatted, end_date_in_tz_formatted


def get_winter_season_name(datetime_obj):
    month = datetime_obj.month
    year = datetime_obj.year

    final_months = [6, 7, 8, 9, 10, 11, 12]
    if month in final_months:
        init_year_season = str(year)[2:4]
        final_year_season = str(year+1)[2:4]
    else:
        init_year_season = str(year-1)[2:4]
        final_year_season = str(year)[2:4]
    winter_season_name = init_year_season+'/'+final_year_season
    return winter_season_name


def get_summer_season_name(datetime_obj):
    year = datetime_obj.year
    # init_year_season = str(year)[2:4]
    # final_year_season = str(year+1)[2:4]
    # summer_season_name = init_year_season+'/'+final_year_season  # for when I used double seasons for summer leagues
    summer_season_name = str(year)
    return summer_season_name


def season_names_from_datetime(datetime_obj=None):
    if not datetime_obj:
        logger.debug("no datetime object given so 'now()' will be used for season names calculation")
        datetime_obj = timezone.now()
    winter_season_name = get_winter_season_name(datetime_obj)
    summer_season_name = get_summer_season_name(datetime_obj)
    return winter_season_name, summer_season_name


def season_from_season_name(season_name):
    season = None
    # I could create a generic function that checks if a choice model is valid for any model with choices
    if season_name in [choice_name[0] for choice_name in games.models.Season.season_choices]:
        try:
            season = games.models.Season.objects.get(name=season_name)
        except games.models.Season.DoesNotExist:
            logger.warning("Season with name [%s] doesn't exist in the database", season_name)
    else:
        logger.warning("Season name [%s] isn't in the allowed season choices.", season_name)
    return season


def competition_ids_from_season_string(season_string):
    season = season_from_season_name(season_string)
    competition_ids = []
    if season:
        competition_seasons = games.models.CompetitionSeason.objects.filter(season=season)
        for comp_season in competition_seasons:
            competition_id = comp_season.competition.id
            competition_ids.append(competition_id)
    return competition_ids


def competition_season_by_datetime_and_competition(datetime_obj, competition):
    winter_name, summer_name = season_names_from_datetime(datetime_obj)
    winter_season = season_from_season_name(winter_name)
    summer_season = season_from_season_name(summer_name)
    seasons = [winter_season, summer_season]
    for season in seasons:
        try:
            # notice that by source mistake a comp_seas can have both a winter and a summer for the
            # given date. In this case the winter type will be returned. This might not be what you want
            competition_season = games.models.CompetitionSeason.objects.get(competition=competition, season=season)
            # competition_season_type = competition_season.type
            return competition_season
        except Exception as e:
            continue
    logger.info('competition_season for competition %s and season of date %s does not exist', competition,
                   datetime_obj)
    return None


# --------- SESSION RELATED -------------
def add_or_update_session(request, variable_name, variable_value):
    logger.debug('adding/updating session variable %s with value %s', variable_name, variable_value)
    added = False
    updated = False
    if not request.session.get(variable_name, None):
        request.session[variable_name] = variable_value
        added = True
    else:
        if request.session[variable_name] != variable_value:
            request.session[variable_name] = variable_value
            updated = True
    return added, updated


def remove_from_session(request, variable_name):
    if request.session.get(variable_name, None):
        del request.session[variable_name]
        logger.debug("Variable %s was removed from the session. New session is %s", variable_name, request.session)
    else:
        logger.warning("The variable %s that was to be deleted from the session, does not exist in the session", variable_name)
    return request.session


def get_session_variable(request, variable_name):
    if request.session.get(variable_name, None):
        variable_value = request.session.get(variable_name)
    else:
        variable_value = None
    return variable_value


# We check for it first in the session and then if there is no selected bookmaker in the session we define it to be
# the default one
def get_selected_bookmaker_name_from_session(request):
    selected_bookmaker_name = get_session_variable(request, 'selected_bookmaker_name')
    if not selected_bookmaker_name:
        selected_bookmaker_name = games.naming.default_bookmaker_name
    return selected_bookmaker_name


def get_selected_bookmaker(request, get_bookmaker=True):
    """
    In GET requests it just returns the bookmaker from the session.
    In POST requests it updates the bookmaker in session if its different from the existing one and returns the new one
    It is called any time that we want to get or update the selected bookmaker from the session:
    it is called a) from planned event views, b) after a PlaceBet action (either GET or POST), c) after a bookmaker_list
    selection action (POST), d) after a back/forward button, e) after a league selection f) and others?
    """
    logger.debug("getting/updating session bookmaker...")
    logger.debug('request method: %s', request.method)
    existing_selected_bookmaker_name = get_selected_bookmaker_name_from_session(request)
    selected_bookmaker_name = existing_selected_bookmaker_name

    # If the request is from the bookmakers list then we get the bookmaker from there. If there is no
    # 'selected_bookmaker_name' which means that the request is not from the bookmakers list we get the bookmaker
    # from the bet_slip bookmaker form (in this case the request comes from the bet_slip form - place_bet).
    # We update the session in both cases
    selected_bookmaker = None
    added = False
    updated = False
    if request.method == 'POST':
        logger.debug('POST request')
        new_selected_bookmaker_name = request.POST.get('selected_bookmaker_name', request.POST.get('bookmaker_name', None))
        logger.debug("adding new bookmaker %s to session...", new_selected_bookmaker_name)
        if new_selected_bookmaker_name:
            try:
                # in POST we get the bookmaker to test if the name that came from the POST request is valid. Maybe I
                # could use a modelForm for this
                selected_bookmaker = games.models.Bookmaker.objects.get(name=new_selected_bookmaker_name)
                selected_bookmaker_name = new_selected_bookmaker_name
                added, updated = add_or_update_session(request, 'selected_bookmaker_name', new_selected_bookmaker_name)
            except games.models.Bookmaker.DoesNotExist:
                logger.error("Selected bookmaker  with name %s doesn't exist in the database", new_selected_bookmaker_name)
        return selected_bookmaker, selected_bookmaker_name, added, updated

    # If the request is a GET then again we just read the selected bookmaker from the session or return the default one.
    # In get request you can select to get the bookmaker from the db or not
    if get_bookmaker:
        logger.debug('Not a POST request')
        try:
            selected_bookmaker = games.models.Bookmaker.objects.get(name=selected_bookmaker_name)
        except games.models.Bookmaker.DoesNotExist:
            logger.warning("Selected bookmaker with name %s doesn't exist in the database", selected_bookmaker_name)
            try:
                # if there is no bookmaker in db get the dummy one which is created during db initialization
                selected_bookmaker_name = Dummies.name
                selected_bookmaker = games.models.Bookmaker.objects.get(name=Dummies.name)
            except games.models.Bookmaker.DoesNotExist:
                logger.error('No bookmaker (not even the Dummy one) exists in db. Create the dummy and retry')
    return selected_bookmaker, selected_bookmaker_name, added, updated


def do_cprofile(func):
    """
    decorator that prints (to the console) the cprofile of the decorated function
    """
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats()
    return profiled_func


def get_pjax_context(request, parent='base.html', pjax_parent='pjax.html', context_var='parent'):
    """
    Creates the parent context variable which defaults to base.html if not PJAX, or pjax.html if PJAX
    this function is used for transforming 3rd party app views to pjax views. These views can't be decorated
    and the wrapper view can't be either, so this is the solution.

    In this case: The template that the original view returns has been overriden to support pjax, and
    it extends the parent context variable. Even if you decorate the wrapper view, the original view
    will use the pjax template but it's context doesn't have the parent variable and you get an error.
    You have to provide the parent variable as extra context.
    """
    pjax_context = {}
    try:
        if request.META.get('HTTP_X_PJAX', False):
            pjax_context[context_var] = pjax_parent
        elif parent:
            pjax_context[context_var] = parent
    except AttributeError:
        # if the resp is HttpResponseRedirect object, it has no context_data attribute
        pass
    return pjax_context


def cbv_pjaxtend(parent='base.html', pjax_parent='pjax.html', context_var='parent'):
    """
    decorator that creates the parent context variable which defaults to base.html if not PJAX, or pjax.html if PJAX
    It is the modified pjaxtend decorator. It must decorate the get method of the class based view.
    It is used instead of the PJAXResponseMixin (similar with the pjaxtend which is used instead of pjax decorator)
    when you don't want to define a separate pjax template.
    """
    def cbv_pjaxtend_decorator(view):
        @functools.wraps(view)
        def _view(self, request, *args, **kwargs):
            resp = view(self, request, *args, **kwargs)
            # this is lame. what else though?
            # if not hasattr(resp, "is_rendered"):
            #     logger.warning("@pjax used with non-template-response view")
            #     return resp
            try:
                if request.META.get('HTTP_X_PJAX', False):
                    resp.context_data[context_var] = pjax_parent
                elif parent:
                    resp.context_data[context_var] = parent
            except AttributeError:
                # if the resp is HttpResponseRedirect object, it has no context_data attribute
                pass
            return resp
        return _view
    return cbv_pjaxtend_decorator


def custom_pjaxtend(parent='base.html', pjax_parent='pjax.html', context_var='parent'):
    # it handles also non-template-response views (by uncommenting a few lines)
    def pjaxtend_decorator(view):
        @functools.wraps(view)
        def _view(request, *args, **kwargs):
            resp = view(request, *args, **kwargs)
            # this is lame. what else though?
            if not hasattr(resp, "is_rendered"):
                logger.warning("@pjax used with non-template-response view")
                return resp

            # try:
            if request.META.get('HTTP_X_PJAX', False):
                resp.context_data[context_var] = pjax_parent
            elif parent:
                resp.context_data[context_var] = parent
            # except AttributeError:
            #     # if the resp is HttpResponseRedirect object, it has no context_data attribute
            #     pass
            return resp
        return _view
    return pjaxtend_decorator


class DatetimeEncoder(json.JSONEncoder):
    # todo have in mind this DatetimeEncoder
    def default(self, obj):
        """
        In order for a string to be parsed as date object in javascript by json.parse() function the string
        must be in this format: 2012-04-23T18:25:43.511Z
        """
        if isinstance(obj, datetime):
            # in this case the datetimes are in utc but I "express" them in utc in order to be able to handle also
            # other tzinfo in the same way: producing the format as javascript expects it (with Z for utc)
            obj = obj.astimezone(pytz.UTC)
            serialized = obj.strftime('%Y-%m-%dT%H:%M:%S.%f')
            serialized = serialized[:-3]  # remove 3 of the 6 digits of milliseconds
            serialized += 'Z'  # adding the Z 'manually'. The datetimes are in utc so its ok
            return serialized
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def paginate(request, paginator_obj, pag_list):
    page = request.GET.get('page')
    try:
        pag_list = paginator_obj.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        pag_list = paginator_obj.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        pag_list = paginator_obj.page(paginator_obj.num_pages)
    return pag_list


