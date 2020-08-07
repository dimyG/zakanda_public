from __future__ import unicode_literals
from django.core.management.base import BaseCommand
import games.naming
import games.models
import gutils.utils
import data_sources.utils
from zakanda.utils import season_from_season_name, competition_ids_from_season_string


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-s'
            '--source',
            action='store',
            dest='source',
            help="Comma separated data source names",
        )
        parser.add_argument(
            '-d'
            '--season_string',
            action='store',
            dest='season_string',
            help='Comma separated. The user defined seasons and competitions will determine the competition_seasons '
                 'for which the teams will be get',
        )
        parser.add_argument(
            '-l'
            '--competition_gid',
            action='store',
            dest='competition_gid',
            help='It is the global id of the competition. The user defined seasons and competitions will '
                 'determine the competition_seasons for which the teams will be get'
                 'By default the get teams call will be made for all the competitions of the given season',
        )
        parser.add_argument(
            '-c'
            '--country_names',
            action='store',
            dest='country_names',
            help='A comma separated list of countries for which the competition ids will be extracted and used. '
                 'It will override other competition ids',
        )
        parser.add_argument(
            '--mapping',
            action='store_true',
            dest='mapping',
            default=False,
            help='',
        )

    def handle(self, *args, **options):
        source_names = gutils.utils.get_command_sources(*args, **options)

        season_string = options.get('season_string', None)
        season_names = gutils.utils.extract_args(season_string)

        competition_id_string = options.get('competition_gid', None)
        competition_ids = gutils.utils.extract_args(competition_id_string)

        country_names = options.get("country_names", None)
        names_list = gutils.utils.extract_args(country_names, default_value=None)

        if country_names:
            competition_ids = []
            if names_list:
                for country_name in names_list:
                    ids = games.models.Country.get_competition_ids(country_name)
                    if ids:
                        competition_ids.extend(ids)

        mapping = options.get("mapping", False)

        # season_names = ['16/17']
        # competition_ids = []
        # try:
        #     competitions = games.models.Competition.objects.filter(generic_name="Champions League", country__name="Europe")
        #     for competition in competitions:
        #         competition_ids.append(competition.id)
        # except Exception as e:
        #     competition_ids = 'All'

        data_sources.utils.get_and_create_teams(source_names, competition_ids=competition_ids, season_names=season_names, mapping=mapping)