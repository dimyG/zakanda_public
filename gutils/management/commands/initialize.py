import logging
from django.core.management.base import BaseCommand
import games.models
import games.naming
import gutils.utils
import data_sources.utils
from zakanda.db import create_initial_data


logger = logging.getLogger(__name__)

# have in mind: a new database can't be created from scratch by "migrate" if there are global variables
# and default parameter values that make database reads to get specific database entries that don't exist yet
# since the new database is empty. Exceptions are raised. I avoid this by catching these exceptions


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
            '-se'
            '--season_string',
            action='store',
            dest='season_string',
            help='Comma separated seasons for which competitions will be created for',
        )

    def handle(self, *args, **options):
        source_names = gutils.utils.get_command_sources(*args, **options)
        # season_names = gutils.utils.get_command_seasons(*args, **options)

        create_initial_data()

        football_gname = games.naming.sport_names.get('football')  # only for xmlsoccer
        seasons = games.models.Season.objects.all()[49:79]  # only for xmlsoccer
        data_sources.utils.get_and_create_lncs(source_names, football_gname, seasons, mapping=False)

        # todo keep summer leagues map updated  # only for xmlsoccer?
        # todo create rounds, stages

        season_names = ["12/13", "13/14", '14/15', '15/16', '16/17', '17/18',
                        '2012', '2013', '2014', '2015', '2016', '2017', '2018']
        season_names = ['16/17', '17/18', '2016', '2017', '2018']
        data_sources.utils.get_and_create_teams(source_names, season_names=season_names, mapping=False)

        self.stdout.write('Done!\n')