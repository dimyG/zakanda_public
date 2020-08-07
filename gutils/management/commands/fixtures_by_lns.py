from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
import gutils.utils
import data_sources.utils


logger = logging.getLogger(__name__)


def get_first_sid(competition_sids):
    """ xmlsoccer accepts only 1 competition id in its api call. sportmonks supports a comma separated list of sids.
    The given competition_sids parameter can be either of two. If there are more than one sids then the first one
    will be collected and used as input for the xmlsoccer api """
    try:
        sids = competition_sids.split(',')
        return sids[0]
    except Exception as e:
        logger.warning('%s', e)


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
            '-d1',
            '--start_date',
            action='store',
            dest='start_date',
            help='format: 2017-08-17-23:30 in UTC',
        )
        parser.add_argument(
            '-d2',
            '--end_date',
            action='store',
            dest='end_date',
            help='format: 2017-08-17-23:30 in UTC',
        )
        parser.add_argument(
            '-d',
            '--season_string',
            action='store',
            dest='season_string',
            help='',
        )
        parser.add_argument(
            '-c',
            '--competition_sids',
            action='store',
            dest='competition_sids',
            help='comma separated list of competition sids, for xmlsoccer it can also be the competition sname',
        )
        parser.add_argument(
            '--odds',
            action='store_true',
            dest='odds',
            default=False,
            help='Make an extra api call to get the odds for the created events',
        )

    def handle(self, *args, **options):
        source_names = gutils.utils.get_command_sources(*args, **options)
        start_date, end_date = gutils.utils.get_command_dates(*args, days=60, **options)
        # competition_sname_sid = "FA Cup"
        # season_name = "16/17"
        season_name = options.get('season_string', None)
        competition_sids = options.get('competition_sids', None)
        # xmlsoccer only accepts one sid
        first_sid = get_first_sid(competition_sids)

        params = {'leagues': competition_sids}
        events, pre_events = data_sources.utils.get_and_create_events_by_lns(
            # season_name and first_sid are only used by xmlsoccer
            source_names, start_date, end_date, season_name, first_sid, **params)

        if options['odds']:
            event_ids = gutils.utils.ids(events)
            odds, offers, offer_odds = data_sources.utils.get_and_create_odd_trees(source_names, event_ids)

        self.stdout.write('Done!\n')
