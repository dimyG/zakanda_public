import vcr
import pytest
from django.core.management import call_command
import utils
import games.models
import games.naming

pytestmark = pytest.mark.django_db  # so that the tests can access the database


@pytest.mark.commands
@vcr.use_cassette('vcr_cassetes/get_leagues_and_countries.yaml')
def test_all_leagues():
    call_command('all_leagues', '-s xmlsoccer')


@pytest.mark.commands
def test_get_command_sources():
    kwargs_01 = {'source': 'xmlsoccer'}
    kwargs_02 = {'source': 'wrong_input'}
    kwargs_03 = {}
    kwargs_04 = {'source': 'xmlsoccer, xmlsoccer'}
    list_kwargs = [kwargs_01, kwargs_02, kwargs_03, kwargs_04]
    for kwargs in list_kwargs:
        args = []
        sources = utils.get_command_sources(*args, **kwargs)
        assert len(sources) == 1
        assert sources[0] == games.naming.source_names[0]

    kwargs_05 = {'source': ' xmlsoccer , ' + games.naming.test_source_name}
    kwargs_06 = {'source': 'xmlsoccer, ' + games.naming.test_source_name + ', ' + 'xmlsoccer'}
    list_kwargs = [kwargs_05, kwargs_06]
    for kwargs in list_kwargs:
        args = []
        sources = utils.get_command_sources(*args, **kwargs)
        assert len(sources) == 2
        assert games.naming.source_names[0] in sources
        assert games.naming.test_source_name in sources