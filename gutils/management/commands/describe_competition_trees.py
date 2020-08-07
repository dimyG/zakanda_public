# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
from django.db.models import Count
import games.models


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            dest='verbose',
            default=False,
            help='',
        )

    def handle(self, *args, **kwargs):

        verbose = kwargs.get('verbose')

        # competitions connected with more than one competition infos (for example due to sid change)
        competitions = games.models.Competition.objects.annotate(num=Count('competitioninfo')).filter(num__gt=1)
        print ('num competitions connected with more than one competition infos (for example due to sid change)', competitions.count())
        if verbose:
            for competition in competitions:
                print competition

        # comp_info connected to more than one competitions (should be 0)
        competition_infos = games.models.CompetitionInfo.objects.annotate(num_competitions=Count('competition')).filter(
            num_competitions__gt=1)
        print ('num competition_infos connected to more than one competitions (should be 0)', len(competition_infos))
        if verbose:
            for competition_info in competition_infos:
                print competition_info

        # comp_seas_info connected with more than one com_seasons. (Check models for details)
        comp_seas_infos = games.models.CompetitionSeasonInfo.objects.annotate(num=Count('competition_seasons')).filter(
            num__gt=1)
        print ('num comp_seas_info connected with more than one comp_seasons (source changes)', len(comp_seas_infos))
        if verbose:
            for comp_seas_info in comp_seas_infos:
                print comp_seas_info

        # (for example due to sid or sname change)
        comp_seas = games.models.CompetitionSeason.objects.annotate(num_infos=Count('infos')).filter(num_infos__gt=1)
        print('num comp_seasons connected with more than one comp_season_info (due to sid or sname change)', comp_seas.count())
        if verbose:
            for comp_sea in comp_seas:
                print comp_sea

        self.stdout.write('Done!\n')


