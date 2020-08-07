from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
from zakanda.utils import season_from_season_name, competition_ids_from_season_string
from games.models import Competition
import games.naming
import gutils.utils
import data_sources.utils

logger = logging.getLogger(__name__)


# If teams are going to be retrieved, then the api call must be made for a specific season (eg. 17/18)
# so that only the competition_seasons of 17/18 are selected for a call to get their teams.
# The number of all available competition_seasons is too big (many times the api call's limit)
# and that would require scheduling of the excessive competition_seasons.

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
            help='The season for which the received competitions will be created for, ex. 17/18',
        )
        parser.add_argument(
            '-c'
            '--competition_gid',
            action='store',
            dest='competition_gid',
            help='It is the global id of the competition. If defined, the get teams api call will be made '
                 'to get the Teams only of that specific competition. '
                 'By default the get teams call will be made for all the competitions of the given season. '
                 'You can define a random string if you do not want a call for get_teams to be made',
        )
        parser.add_argument(
            '--teams',
            action='store_true',
            dest='teams',
            default=False,
            help='Make an extra api call to get the teams for the given competitions',
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
        mapping = options.get("mapping", False)
        football_gname = games.naming.sport_names.get('football', None)
        competition_gid = options.get('competition_gid', None)

        seasons = []
        season_names = gutils.utils.extract_args(season_string, default_value=[])
        if isinstance(season_names, list):
            for season_name in season_names:
                season = season_from_season_name(season_name)
                if season:
                    seasons.append(season)
        elif season_names:
            seasons = [season_from_season_name(season_names)]

        # Api call. Have in mind that in xmlsoccer get leagues you don't define season. You get all leagues.
        # But a league could not be valid for the season that you will create it for. This is not a big
        # issue since any call for teams or events for it will return nothing. But they will exist in the db
        data_sources.utils.get_and_create_lncs(source_names, football_gname, seasons, mapping=mapping)

        competition_ids = []
        if competition_gid:
            try:
                competition = Competition.objects.get(id=competition_gid)
            except Exception as e:
                # no call to get_teams will be made
                self.stdout.write('No call to get teams was made. Id: {}, Exception: {} '.format(competition_gid, e))
                self.stdout.write('Done!\n')
                return
            competition_id = competition.id
            competition_ids = [competition_id]

        if not season_names:
            season_names = 'All'
        if not competition_ids:
            competition_ids = 'All'
        if options.get('teams'):
            data_sources.utils.get_and_create_teams(source_names, competition_ids=competition_ids, season_names=season_names, mapping=mapping)

        self.stdout.write('Done!\n')
