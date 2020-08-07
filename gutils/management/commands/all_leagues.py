from __future__ import unicode_literals

import logging
from django.core.management.base import BaseCommand
import games.models
import games.naming
import games.utils
import gutils.utils
import data_sources.utils

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '-s',
            '--source',
            action='store',
            dest='source',
            help='Comma separated data source names . '
                 'On unknown names the default source will be used',
        )
        parser.add_argument(
            '-m'
            '--mapping',
            action='store',
            dest='mapping',
            help='',
        )

    def handle(self, *args, **kwargs):
        sources = gutils.utils.get_command_sources(*args, **kwargs)

        football_gname = games.naming.sport_names.get('football', None)
        # seasons = games.models.Season.objects.all()[49:79]  # Seasons: currently position 49 is Season 93/94
        seasons = games.models.Season.objects.filter(name__in=['16/17', '2016'])

        mapping = kwargs.get("mapping", False)
        if mapping:
            mapping = True

        pre_countries, pre_comps, countries, comps = data_sources.utils.get_and_create_lncs(sources, football_gname, seasons, mapping=mapping)

        self.stdout.write('Done!\n')