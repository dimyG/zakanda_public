from __future__ import unicode_literals
from django.core.management.base import BaseCommand
from django.utils import timezone
import data_sources.utils
import gutils.utils

# import pytz


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
            '-nd',
            '--days',
            action='store',
            dest='days',
            help='if no d1 and d2, then d1=now and d2=d1+nd days, if no d1, d2 and nd, nd=3',
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
        start_date, end_date = gutils.utils.get_command_dates(*args, **options)

        # start_date = timezone.datetime(2017, 3, 10, 13, tzinfo=pytz.timezone("UTC"))
        # end_date = timezone.datetime(2017, 3, 10, 19, tzinfo=pytz.timezone("UTC"))

        events, pre_events = data_sources.utils.get_and_create_events_by_date(source_names, start_date, end_date)
        if options['odds']:
            event_ids = gutils.utils.ids(events)
            odds, offers, offer_odds = data_sources.utils.get_and_create_odd_trees(source_names, event_ids)

        self.stdout.write('Done!\n')
