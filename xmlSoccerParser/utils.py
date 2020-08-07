# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from games import naming, models
import zakanda.db
import games.models
import games.naming
from data_sources.pre_models import NameMappedEntity


logger = logging.getLogger(__name__)


def get_native_source():
    source_name = games.naming.source_names[0]
    try:
        source, source_created = games.models.Source.objects.get_or_create(name=source_name)
    except Exception as e:
        logger.warning('%s Probably the database has no zakanda schema or no data yet', e)
        source = None
    return source


def list_from_season_choices():
    seasons = [season[0] for season in games.models.Season.season_choices]
    return seasons


def update_summer_leagues(summer_leagues, comp_type=games.models.CompetitionSeason.summer):
    # todo select by id not by gname. Competition gname is not unique.
    for summer_league_gname in summer_leagues:
        try:
            competitions = games.models.Competition.objects.filter(generic_name=summer_league_gname)
            for competition in competitions:
                wrong_type_comp_seas = games.models.CompetitionSeason.objects.filter(competition=competition).\
                    exclude(type=comp_type)
                if wrong_type_comp_seas:
                    upd = wrong_type_comp_seas.update(type=comp_type)
                    if upd:
                        logger.info("the type of comp_seasons of the summer competition %s was updated", competition)
                else:
                    logger.debug('comp seas is of the correct type')
        except games.models.Competition.DoesNotExist:
            logger.warning("given summer competition with name %s doesn't exist in the db", summer_league_gname)


def make_season_date_string_from(season):
    """
    this function must always run before an xmlsoccer api call that needs a seasonDateString argument.
    If the seasonDateString is None then the api will raise an error which we will see in the logs

    season: season argument can be either season instance or season name string
    """
    if isinstance(season, basestring):
        season_name = season
    elif isinstance(season, games.models.Season):
        season_name = season.name
    else:
        logger.warning('argument %s is neither season instance nor season name', season)
        return None

    seasonDateString = None
    if season_name in [choice_name[0] for choice_name in games.models.Season.season_choices]:
        if '/' in season_name:
            seasonDateString = season_name.replace('/', '')
    else:
        logger.warning("season name isn't valid")
        # Not needed anymore since I keep 16/17 instead of 2016 (ex. EURO 2016 season now is 16/17)
        # first_year = season_name[-2:]
        # second_year = int(first_year)+1
        # seasonDateString = str(first_year)+str(second_year)
        # logger.debug("season name %s converted to seasonString %s for the xmlsoccer api call", season_name, seasonDateString)
    return seasonDateString


def sids_from_events_and_source(events, source):
    event_sids = []
    if not events or not source:
        logger.warning("There are no events or source to get event_sids from.")
        return event_sids
    for event in events:
        # todo check if there are other occurencies that need to be replaced with the get_sid() function
        # sid = event.event_infos.all().get(source=source).sid
        sids = event.get_sids(source_name=source.name)
        for sid in sids:
            event_sids.append(sid)
    return event_sids


def make_integers(result_time, home_goals, away_goals):
    # intargs = []
    # for arg in args:
    #     try:
    #         arg = int(arg)
    #     except ValueError:
    #         pass
    #     intargs.append(arg)
    try:
        result_time = int(result_time)
    except Exception as e:
        result_time = result_time
    try:
        home_goals = int(home_goals)
    except Exception as e:
        logger.warning('%s', e)
        home_goals = home_goals
    try:
        away_goals = int(away_goals)
    except Exception as e:
        logger.warning('%s', e)
        away_goals = away_goals
    return result_time, home_goals, away_goals


def get_events_from_bets():
    user = games.models.User.objects.filter(email='example@test.com')
    # user = games.models.User.objects.filter(email=test_mail_01)
    user_bets = games.models.Bet.objects.filter(totalbet__user=user)
    user_bet_events = games.models.BetEvent.objects.filter(bet__in=user_bets)
    bet_events = user_bet_events

    # bet_events = games.models.BetEvent.objects.distinct('event')
    distinct_events = []
    for bet_event in bet_events:
        distinct_events.append(bet_event.event)
    return distinct_events


def create_pre_lncs(pre_countries, pre_competitions):
    # returned countries and competitions are the entities that have been created or they
    # have been selected (if they already existed)
    countries, competitions, competition_seasons = [], [], []
    deleted_comp_seasons, created_comp_seasons = [], []
    if pre_countries and pre_competitions:
        for pre_country in pre_countries:
            countries.append(pre_country.get_or_create()[0])
        for pre_competition in pre_competitions:
            competition, rel_competition_seasons = pre_competition.get_or_create()
            competitions.append(competition)
            competition_seasons.extend(rel_competition_seasons)

        pre_models_group = [pre_countries, pre_competitions]
        for pre_models in pre_models_group:
            NameMappedEntity.exhaustive_unmapped_mapping(pre_models)

        deleted_comp_seasons, created_comp_seasons = process_special_leagues()

        logger.debug('deleted comps: %s', len(deleted_comp_seasons))
        logger.debug('created comps: %s', len(created_comp_seasons))
        logger.debug('COMPETITIONS SEASONS INIT: %s', len(competition_seasons))
        # logger.debug('COMPETITIONS SEASONS INIT: %s',
        #              ['{} {}'.format(competition_season.competition.generic_name, competition_season.season.name)
        #               for competition_season in competition_seasons])
        for comp in deleted_comp_seasons:
            logger.debug('del comp: %s', comp)
            if comp in competition_seasons:
                logger.debug('removing')
                competition_seasons.remove(comp)
        for comp in created_comp_seasons:
            if comp not in competition_seasons:
                competition_seasons.append(comp)
        logger.debug('COMPETITION SEASONS: %s', len(competition_seasons))
        # logger.debug('COMPETITIONS SEASONS INIT: %s',
        #              ['{} {}'.format(competition_season.competition.generic_name, competition_season.season.name)
        #               for competition_season in competition_seasons])
    return countries, competitions, competition_seasons, deleted_comp_seasons, created_comp_seasons


def process_special_leagues():
    """
    The need to run this function comes from the fact that xmlsoccer doesn't support leagues per season.
    For sources that they do, it is not necessary since the special leagues will be created only for the
    read seasons

    special leagues are the ones that run every 4 years and the ones that play during the whole year like swedish etc.
    All these are marked with competition_season type: "Summer"
    Some leagues are only every 4 years so I delete them for the other seasons.
    """
    # Have in mind the qualifying events for the per 4 years competitions
    logger.info("processing special leagues...")

    per_4_years_leagues = naming.four_year_leagues_per_season
    # summer_leagues = games.naming.summer_leagues

    deleted_competition_seasons, created_competition_seasons = process_per_4_years_leagues(per_4_years_leagues)
    # update_summer_leagues(summer_leagues)  # we apply the correct type on competition_tree creation
    return deleted_competition_seasons, created_competition_seasons


def process_per_4_years_leagues(per_4_years_leagues):
    """ deletes the unnecessary competition seasons and updates the type of the remaining ones
    It can be safely re-run at any point in time. It only makes changes if it is necessary. """

    deleted_competition_seasons = []
    correct_type = models.CompetitionSeason.summer
    created_competition_seasons = []
    for generic_league_name, season_name in per_4_years_leagues.iteritems():
        season, created = models.Season.objects.get_or_create(name=season_name)
        try:
            # todo select by id (or gname and country) not by gname. gname is not unique
            competitions = models.Competition.objects.filter(generic_name=generic_league_name)
            for competition in competitions:
                distinct_competition_season_infos = zakanda.db.get_distinct_comp_seas_info_list_from(competition=competition, season='All')
                competition_seasons = models.CompetitionSeason.objects.filter(competition=competition).exclude(season=season)

                # val = str()
                # for competition_season in competition_seasons:
                #     val += "{} {}, ".format(competition_season.competition, competition_season.season)
                # deleted_competition_seasons.append(val)

                if competition_seasons:
                    deleted_competition_seasons.extend(competition_seasons)
                    competition_seasons.delete()
                    logger.info("unnecessary competition_seasons %s was deleted", competition_seasons)

                correct_comp_seas = models.CompetitionSeason.objects.filter(competition=competition, season=season, type=correct_type)
                # logger.debug('correct_comp_seas: %s, %s, %s', correct_comp_seas, correct_comp_seas[0].type, distinct_competition_season_infos)
                if not correct_comp_seas:
                    # update the type only if it is necessary
                    wrong_type_comp_seas = models.CompetitionSeason.objects.filter(competition=competition).exclude(type=correct_type)
                    if wrong_type_comp_seas:
                        try:
                            upd = wrong_type_comp_seas.update(type=correct_type)
                            if upd:
                                logger.info("the type of comp_seasons of the per_4_years competition %s was updated: %s",
                                            competition, wrong_type_comp_seas)
                            else:
                                logger.error("the type of comp_seasons of the per_4_years competition %s "
                                             "was not updated: %s", competition, wrong_type_comp_seas)
                        except Exception as e:
                            logger.error('%s, competition season %s %s type was not updated with the correct type', e, competition, season)
                # if the competition_season for the correct season exists, then it will not be deleted and no further
                # action is needed. But if it doesn't exist, then we need to create it. And assign to it its infos.
                try:
                    models.CompetitionSeason.objects.get(competition=competition, season=season)
                except models.CompetitionSeason.DoesNotExist:
                    competition_season, competition_season_created = models.CompetitionSeason.objects.get_or_create(
                        competition=competition, season=season, type=models.CompetitionSeason.summer)
                    for distinct_competition_info in distinct_competition_season_infos:
                        competition_season.infos.add(distinct_competition_info)
                    logger.info("special competition_season for %s %s wasn't in db and was created successfully", competition, season)
                    created_competition_seasons.append(competition_season)
                except models.CompetitionSeason.MultipleObjectsReturned as e:
                    logger.error('%s for competition %s and season %s', e, competition, season)

        except models.Competition.DoesNotExist:
            logger.warning("given per_4_years competition with name %s doesn't exist in the db", generic_league_name)
    return deleted_competition_seasons, created_competition_seasons