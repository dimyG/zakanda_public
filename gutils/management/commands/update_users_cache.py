# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
# from feeds.signals import notifications_unfollow_all
from bet_statistics.signals import update_user_cache
# from bet_statistics.views import calc_user_total_bets_df, calculate_total_bets_stats


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '-id',
            '--id',
            action='store',
            dest='user_id',
            help='',
        )

    def handle(self, *args, **kwargs):
        # from user_accounts import utils
        # users = User.objects.filter(id__in=[3, 4, 5])
        # utils.email_user_for_new_followers(target_user_id=1, filtered_followers=users)

        # notifications_unfollow_all()
        user_id = kwargs.get('user_id')
        if not user_id:
            users = User.objects.all()
        else:
            users = User.objects.filter(id=user_id)
        for user in users:
            update_user_cache(user.id)

        self.stdout.write('Done!\n')
