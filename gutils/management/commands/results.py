# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.management.base import BaseCommand
import games.models
import zakanda.db
import data_sources.utils
import gutils.utils


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
            '-l'
            '--competition_gid',
            action='store',
            dest='competition_gid',
            help='comma separated zakanda ids of competitions',
        )
        parser.add_argument(
            '-c'
            '--country_names',
            action='store',
            dest='country_names',
            help='A comma separated list of country names',
        )

    def handle(self, *args, **options):
        source_names = gutils.utils.get_command_sources(*args, **options)

        start_date = options.get("start_date")
        end_date = options.get("end_date")
        dates = [start_date, end_date]
        dates = gutils.utils.to_datetime(dates)
        if None in dates:
            start_date, end_date = None, None
        else:
            start_date = dates[0]
            end_date = dates[1]

        events = games.models.Event.filter_events(start_date=start_date, end_date=end_date)
        event_ids_sorted, ingredients = games.models.Event.order_for_result_call(events)
        # events = games.models.Event.objects.filter(event_infos__sid__in=[360075])
        # events = zakanda.db.filter_events(competition_gname="EURO 2016", start_date=start_date, end_date=end_date)
        # events = zakanda.db.filter_events(competition_id=11178, start_date=start_date, end_date=end_date)
        # events = games.models.Event.objects.filter(status=games.models.Event.not_started)[:2]

        # from django.contrib.auth.models import User
        # events = dict()
        # for user in User.objects.all():
        #     bet_events = user.profile.distinct_bet_events()
        #     for bet_event in bet_events:
        #         events[bet_event.event] = bet_event.event
        # events = events.keys()

        # source = games.models.Source.objects.get(name='xmlSoccer')
        # event = zakanda.db.event_from_sid('370889', source)
        # events = [event]

        # user = User.objects.get(id=9)
        # bet_events = user.profile.distinct_bet_events()
        # events = games.models.Event.objects.filter(bet_events__in=bet_events)

        # print(events)
        # for event in events:
        #     zakanda.db.remove_results(event)

        data_sources.utils.get_and_create_results(source_names, event_ids_sorted)
        self.stdout.write('Done!\n')
