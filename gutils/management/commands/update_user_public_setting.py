# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

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
        parser.add_argument(
            '--public',
            action='store_true',
            default=False,
            dest='public',
            help='',
        )

    def handle(self, *args, **kwargs):
        user_id = kwargs.get('user_id')
        public = kwargs['public']
        if not user_id:
            users = User.objects.all()
        else:
            users = User.objects.filter(id=user_id)

        for user in users:
            try:
                user.profile.public = public
                user.profile.save()
            except Exception as e:
                self.stdout.write(e)
                break
        self.stdout.write('Done!\n')
