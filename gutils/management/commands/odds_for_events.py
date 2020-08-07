from __future__ import unicode_literals
from django.core.management.base import BaseCommand
import games.models
import gutils.utils
import data_sources.utils
from django.db.models import Count


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
            help='if no d1 and d2, then d1=now and d2=d1+d days, if no d, d=3',
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
            '--competition_gids',
            action='store',
            dest='competition_gids',
            help='comma separated list of competition gids (zakanda ids), for xmlsoccer it can also be the competition sname',
        )
        parser.add_argument(
            '--no_odds_only',
            action='store_true',
            dest='no_odds_only',
            default=False,
            help='get only those events that have no odds yet',
        )

    def handle(self, *args, **options):
        status = games.models.Event.not_started

        source_names = gutils.utils.get_command_sources(*args, **options)
        start_date, end_date = gutils.utils.get_command_dates(*args, **options)
        season_name = options.get('season_string', None)
        competition_gids_string = options.get('competition_gids', None)

        competition_seasons = None
        competition_gids = gutils.utils.get_command_competition_gids(competition_gids_string)
        if competition_gids:
            competition_seasons = games.models.CompetitionSeason.objects.filter(
                competition__id__in=competition_gids, season__name=season_name)

        # events = games.models.Event.objects.filter(id=1000)
        events = games.models.Event.filter_events(competition_seasons=competition_seasons,
                                                  start_date=start_date, end_date=end_date, status=status)

        if options.get('no_odds_only'):
            winner_offers = games.models.WinnerOffer.objects.filter(event__in=events).\
                annotate(num_winner_odds=Count('odds')).filter(num_winner_odds=1)
            events = events.filter(winneroffer__in=winner_offers)

        event_ids = events.values_list("id", flat=True)
        print ('Getting odds for ', len(event_ids), ' events')
        odds, offers, offer_odds = data_sources.utils.get_and_create_odd_trees(source_names, event_ids)
        self.stdout.write('Done!\n')
