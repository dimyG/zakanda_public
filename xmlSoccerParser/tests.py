import logging

import vcr
import pytest
import games.models
import games.naming
import xmlSoccerParser.views
import xmlSoccerParser.utils
from xmlSoccer import XmlSoccer
import zakanda.settings
from data_sources.pre_models import NameMappedEntity


logger = logging.getLogger(__name__)
global_XMLSOCCER_API_KEY = zakanda.settings.XMLSOCCER_API_KEY
global_use_demo = zakanda.settings.xmlsoccer_demo
source_name = games.naming.source_names[0]

pytestmark = pytest.mark.django_db  # so that the tests can access the database


# @pytest.fixture(scope='module')
# def django_db_setup(django_db_setup, django_db_blocker):
#     """ Add data to the database that are available for all module tests """
#     with django_db_blocker.unblock():
#         test_source, created = games.models.Source.objects.get_or_create(name=games.naming.test_source_name)


def create_zakanda_models(pre_models, mapping=True):
    zak_ents = []
    for pre_model in pre_models:
        zak_ent = pre_model.get_or_create(mapping)
        zak_ents.append(zak_ent)
    return zak_ents


@pytest.mark.source_data
def test_get_all_leagues_response():
    xmlsoccer = XmlSoccer(api_key=global_XMLSOCCER_API_KEY, use_demo=global_use_demo)
    response = xmlsoccer.call_api(method='GetAllLeagues')
    assert isinstance(response, list)
    for res in response:
        assert isinstance(res, dict)
    # assert set(leagues_keys).issubset(response[][0].keys())


@vcr.use_cassette('vcr_cassetes/get_leagues_and_countries.yaml')
@pytest.fixture()
def create_lnc_pre_models():
    """ since I use a conftest.py in project level, I must place the vcr path
    relative to the project's level """
    test_source = games.models.Source.objects.get(name=games.naming.test_source_name)
    football_gname = games.naming.sport_names.get('football', None)
    season = games.models.Season.objects.get(name='16/17')
    seasons = [season]
    pre_countries, pre_competitions = xmlSoccerParser.views.get_leagues_and_countries(
        football_gname, seasons, source=test_source)
    return pre_countries, pre_competitions, test_source


def assert_competitions(pre_competitions):
    assert pre_competitions
    for pre_competition in pre_competitions:
        pre_competition.map()  # all competition exist and their gname with the same name
        assert pre_competition.exists
        assert pre_competition.existing_entity
    new_entities, existing_entities, to_be_remapped_entities = NameMappedEntity.describe(pre_competitions)
    assert not new_entities
    assert existing_entities
    assert not to_be_remapped_entities

    comp_ents = create_zakanda_models(pre_competitions, mapping=False)
    del_comps, created_comps = xmlSoccerParser.utils.process_special_leagues()
    # assert del_comps
    # assert not created_comps
    for comp_ent in comp_ents:
        competition = comp_ent[0]
        competition_seasons = comp_ent[1]
        assert isinstance(competition, games.models.Competition)
        for competition_season in competition_seasons:
            assert isinstance(competition_season, games.models.CompetitionSeason)
            competition_gname = competition_season.competition.generic_name
            if competition_gname in games.naming.four_year_leagues:
                seasons = competition_season.competition.seasons.all()
                assert len(seasons) == 1
                assert seasons[0].name == games.naming.four_year_leagues_per_season[competition_gname]
                # len(competition_season.infos.all()) == 0 if special league is not for the given season for
                # which the test is run (16/17). If it is, then it is 2
            else:
                assert len(competition_season.infos.all()) == 2


@pytest.mark.mapping
def test_lnc_pre_01(create_lnc_pre_models):
    # todo high update tests (these tests 01, 02, 03, 04 test the mapping process. They are not source specific
    # so they must be generalized and moves to the data_sources tests
    """
    checks the case in which pre-entities exist with the same name.
    (Only the countries are checked for all mapping cases)
    """
    pre_countries, pre_competitions, test_source = create_lnc_pre_models
    assert pre_countries

    for pre_country in pre_countries:
        pre_country.map()
        assert pre_country.exists
        assert pre_country.existing_entity

    new_entities, existing_entities, to_be_remapped_entities = NameMappedEntity.describe(pre_countries)
    assert not new_entities
    assert existing_entities
    assert not to_be_remapped_entities

    countries = create_zakanda_models(pre_countries, mapping=False)
    for country in countries:
        assert country
        assert country.sources.filter(name=test_source.name)
        assert len(country.sources.all()) == 2
    assert_competitions(pre_competitions)


@pytest.fixture
def modify_existing_entities(names=('Germany',)):
    # 703 germany, 704 Italy
    ents = []
    new_names = []
    for name in names:
        ent = games.models.Country.objects.get(name=name)
        prefix = 'test_'
        name = ent.name
        new_name = prefix + name
        ent.name = new_name
        ent.save()
        ents.append(ent)
        new_names.append(new_name)
    return ents, names, new_names


@pytest.mark.mapping
def test_lnc_pre_02(create_lnc_pre_models, modify_existing_entities):
    """ checks the case in which a pre-entity exists with a different name and
    user gives a valid existing entity id """
    pre_countries, pre_competitions, test_source = create_lnc_pre_models
    assert pre_countries
    assert pre_competitions
    existing_ents, existing_old_names, existing_new_names = modify_existing_entities

    for pre_country in pre_countries:
        pre_country.map(define_entity_fun=lambda: '1', define_id_fun=lambda: '703')
        assert pre_country.exists
        assert pre_country.existing_entity
        if pre_country.sname == 'Germany':
            assert pre_country.existing_entity == existing_ents[0]
            assert pre_country.existing_entity.name == existing_new_names[0]

    new_entities, existing_entities, to_be_remapped_entities = NameMappedEntity.describe(pre_countries)
    assert not new_entities
    assert existing_entities
    assert not to_be_remapped_entities

    countries = create_zakanda_models(pre_countries, mapping=False)  # countries is a generator
    for country in countries:
        assert country
        new_source = country.sources.filter(name=test_source.name)
        assert new_source
        assert len(country.sources.all()) == 2
        if country == existing_ents[0]:
            assert country.id == 703
            country_info = games.models.CountryInfo.objects.get(country=country, source=new_source)
            assert country_info.sname == 'Germany'


@pytest.mark.mapping
def test_lnc_pre_03(create_lnc_pre_models, modify_existing_entities):
    """ checks the case in which an entity exists with a different name
    and user gives an invalid existing entity id """

    pre_countries, pre_competitions, test_source = create_lnc_pre_models
    assert pre_countries
    assert pre_competitions
    existing_ents, existing_old_names, existing_new_names = modify_existing_entities

    for pre_country in pre_countries:
        pre_country.map(define_entity_fun=lambda: '1', define_id_fun=lambda: '0')
        assert pre_country.exists
        if pre_country.sname == 'Germany':
            assert not pre_country.existing_entity
        else:
            assert pre_country.existing_entity
    new_entities, existing_entities, to_be_remapped_entities = NameMappedEntity.describe(pre_countries)
    assert not new_entities
    assert existing_entities
    assert to_be_remapped_entities

    countries = create_zakanda_models(pre_countries, mapping=False)  # countries is a generator
    assert None in countries
    # assert countries.count(None) == 1


@pytest.fixture
def delete_existing_entities(names=('Germany',)):
    for name in names:
        games.models.Country.objects.get(name=name).delete()
    return names


@pytest.mark.mapping
def test_lnc_pre_04(create_lnc_pre_models, delete_existing_entities):
    """ checks the case in which an entity doesn't exists """
    pre_countries, pre_competitions, test_source = create_lnc_pre_models
    assert pre_countries
    assert pre_competitions
    deleted_ent_name = delete_existing_entities

    for pre_country in pre_countries:
        pre_country.map(define_entity_fun=lambda: '2', define_id_fun=lambda: 'not_used')
        if pre_country.sname == 'Germany':
            assert not pre_country.exists
            assert not pre_country.existing_entity
        else:
            assert pre_country.exists
            assert pre_country.existing_entity

    new_entities, existing_entities, to_be_remapped_entities = NameMappedEntity.describe(pre_countries)
    assert new_entities
    assert existing_entities
    assert not to_be_remapped_entities


def test_lnc_creation(create_lnc_pre_models):
    pre_countries, pre_competitions, test_source = create_lnc_pre_models
    countries, competitions, competition_seasons, del_comp_seasons, created_comp_seasons = \
        xmlSoccerParser.utils.create_pre_lncs(pre_countries, pre_competitions)
    assert countries
    assert competitions
    assert competition_seasons
    assert del_comp_seasons
    assert len(pre_competitions) - len(del_comp_seasons) == len(competition_seasons)
    assert not created_comp_seasons
    for country in countries:
        assert isinstance(country, games.models.Country)
    for competition in competitions:
        assert isinstance(competition, games.models.Competition)
    for competition_season in competition_seasons:
        assert isinstance(competition_season, games.models.CompetitionSeason)


def test_lnc_zakanda_models(create_lnc_pre_models):
    pre_countries, pre_competitions, test_source = create_lnc_pre_models
    assert pre_countries
    assert pre_competitions
    for pre_country in pre_countries:
        country = pre_country.get_or_create()[0]
        assert isinstance(country, games.models.Country)
    for pre_competition in pre_competitions:
        competition, competition_seasons = pre_competition.get_or_create()
        assert isinstance(competition, games.models.Competition)
        for competition_season in competition_seasons:
            assert isinstance(competition_season, games.models.CompetitionSeason)