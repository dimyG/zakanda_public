# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.management.base import BaseCommand
import games.models
import gutils.utils
from sportmonks import constants
import sportmonks.views
from data_sources.utils import realize_pre_results


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
            '-gid',
            '--event_gid',
            action='store',
            dest='event_gid',
            help="event's zakanda id"
        )
        parser.add_argument(
            '-fstat'
            '--event_status',
            action='store',
            dest='event_status',
            help='format: sportmonks event status FT, AET, etc. ',
        )
        parser.add_argument(
            '-ft',
            '--ft_score',
            action='store',
            dest='ft_score',
            help='format: 2-2',
        )
        parser.add_argument(
            '-mt'  # couldn't be ht because it starts with h as -h (--help) so it raises an error
            '--ht_score',
            action='store',
            dest='ht_score',
            help='format: 2-2',
        )
        parser.add_argument(
            '-et'
            '--et_score',
            action='store',
            dest='et_score',
            help='format: 2-2 Notice that the score is the extra time score only. If ft is 1-1 and final score'
                 ' after extra time 2-1 the et_score is 1-0. (sportmonks compatibility)',
        )
        parser.add_argument(
            '-pen'
            '--pen_score',
            action='store',
            dest='pen_score',
            help='format: 2-2 Notice that the score is the penalties score only similar with et_score',
        )

    def handle(self, *args, **options):
        # this function manually creates the pre_result instances from the given data and proceeds to results
        # creation as per the function: data_sources.utils.get_and_create_results(source_names, event_ids_sorted)
        source_names = gutils.utils.get_command_sources(*args, **options)
        event_status = options.get('event_status')
        event_gid = options.get('event_gid')
        ft_score = options.get('ft_score')
        ht_score = options.get('ht_score')
        et_score = options.get('et_score')
        pen_score = options.get('pen_score')

        try:
            event = games.models.Event.objects.get(id=event_gid)
            self.stdout.write('Processing event: {}...'.format(event))
        except Exception as e:
            self.stdout.write('Event with id {} not found!\n'.format(event_gid))
            return

        source_name = source_names[0]
        try:
            source = games.models.Source.objects.get(name=source_name)
        except Exception as e:
            self.stdout.write('Source with name {} not found!\n'.format(source_name))
            return

        if event_status not in constants.fetched_status.__members__:
            self.stdout.write('Invalid event status {}'.format(event_status))
            return

        ht_goals = sportmonks.views.goals_from_string(ht_score)
        ft_goals = sportmonks.views.goals_from_string(ft_score)
        et_goals = sportmonks.views.goals_from_string(et_score)
        pen_goals = sportmonks.views.goals_from_string(pen_score)

        pre_results = sportmonks.views.create_pre_results(event, event_status, ht_goals, ft_goals, et_goals, pen_goals, source)
        results, events_with_valid_result = realize_pre_results(pre_results)
        self.stdout.write('{} results created successfully'.format(len(results)))
        games.models.Event.settle_trees(events_with_valid_result, update_cache=True)

        self.stdout.write('Done!\n')
