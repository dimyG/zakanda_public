import pytest
import logging
import games.naming
import models
import zakanda.db
from data_sources import pre_models
import sportmonks.views

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.django_db  # so that the tests can access the database
default_source_names = [games.naming.default_source_name]


@pytest.fixture(scope='module')
def django_db_setup(django_db_setup, django_db_blocker):
    """ Add data to the database that are available for all module tests. Comps and countries
     need to exist in order for teams to be created """
    with django_db_blocker.unblock():
        test_source, created = games.models.Source.objects.get_or_create(name=games.naming.test_source_name)
        competition_gname = 'English Premier League'
        country = models.Country.objects.get(name='England')
        sport = models.Sport.objects.get(name=games.naming.sport_names['football'])
        season = models.Season.objects.get(name='16/17')
        seasons = [season]
        test_sid = 77776666
        competition_season_type = sportmonks.views.get_competition_season_type(season)
        competition_season_util = pre_models.CompetitionSeasonUtil(season, test_sid, competition_gname, competition_season_type)
        competition, competition_seasons = zakanda.db.create_competition_tree(
            competition_season_utils=[competition_season_util], competition_gname=competition_gname, country=country,
            sport=sport, source=test_source, competition_sgname=competition_gname, competition_sid=test_sid
        )


@pytest.mark.comp_seas_sid
def test_comp_seas_by_sid():
    # todo update test
    source_name = games.naming.source_names[0]
    xmlsoccer_source = models.Source.objects.get(name=source_name)
    season = models.Season.objects.get(name='16/17')
    competition = models.Competition.objects.filter(generic_name='English Premier League')[0]
    competition_season = models.CompetitionSeason.objects.get(season=season, competition=competition)
    assert competition_season
    infos = competition_season.infos.all()
    assert len(infos) == 2
    logger.debug(infos)

    xmlsoccer_sid = 1
    competition_seasons = models.CompetitionSeason.by_sid(xmlsoccer_sid, xmlsoccer_source)
    logger.debug(competition_seasons)
    assert len(competition_seasons) > 1  # it exists for many seasons
    season_specific_competition_seasons = models.CompetitionSeason.by_sid(xmlsoccer_sid, xmlsoccer_source, season)
    assert len(season_specific_competition_seasons) == 1

    test_sid = 77776666
    test_source = models.Source.objects.get(name=games.naming.test_source_name)
    competition_seasons = models.CompetitionSeason.by_sid(test_sid, test_source)
    logger.debug(competition_seasons)
    assert len(competition_seasons) == 1
