# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
import games.models
import gutils.utils


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--source',
            action='store',
            dest='source',
            help='Comma separated data source names . '
                 'On unknown names the default source will be used',
        )
        parser.add_argument(
            '-home',
            '--home_team',
            action='store',
            dest='home_team',
            help='',
        )
        parser.add_argument(
            '-visitor',
            '--away_team',
            action='store',
            dest='away_team',
            help='',
        )
        parser.add_argument(
            '-l',
            '--competition_gname',
            action='store',
            dest='competition_gname',
            help='',
        )
        parser.add_argument(
            '-d',
            '--season_name',
            action='store',
            dest='season_name',
            help='',
        )

    def handle(self, *args, **kwargs):
        source_names = gutils.utils.get_command_sources(*args, **kwargs)
        # source_name = source_names[0]
        ht = kwargs.get('home_team')
        at = kwargs.get('away_team')
        ln = kwargs.get("competition_gname")
        sn = kwargs.get("season_name")

        events = games.models.Event.filter_events(competition_gname=ln, home_team_gname=ht, away_team_gname=at, season=sn)
        logger.info("%s events were found", len(events))
        for event in events:
            event.describe()

        self.stdout.write('Done!\n')