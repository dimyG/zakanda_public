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

    def handle(self, *args, **kwargs):
        user_id = kwargs.get('user_id')
        if not user_id:
            users = User.objects.all()
        else:
            users = User.objects.filter(id=user_id)
        for user in users:
            user.profile.transfer_due_funds()

        self.stdout.write('Done!\n')
