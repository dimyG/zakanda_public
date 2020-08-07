# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from actstream.models import following, followers

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
        user_id = kwargs.get('user_id')
        if not user_id:
            users = User.objects.all()
        else:
            users = User.objects.filter(id=user_id)

        for user in users:
            follower_users = followers(user)
            following_users = following(user, User)

            if follower_users:
                num_followers = len(follower_users)
            else:
                num_followers = 0  # initially default value was None instead of 0, so update the db with 0
            if following_users:
                num_following = len(following_users)
            else:
                num_following = 0

            user.basic_stats.num_followers = num_followers
            user.basic_stats.num_following = num_following
            user.basic_stats.save()

        self.stdout.write('Done!\n')
