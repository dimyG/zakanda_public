from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
from register_history.views import register_history_bets


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '-b',
            '--s3_bucket_name',
            action='store',
            # type=str,
            dest='s3_bucket_name',
            # default=False,
            help='The s3 bucket that contains the filename',
        )
        parser.add_argument(
            '-f',
            '--filename',
            action='store',
            dest='filename',
            # default=False,
            help='The filename',
        )
        parser.add_argument(
            '-u',
            '--user_id',
            action='store',
            # type=str,
            dest='user_id',
            # default=False,
            help='The user id of the user',
        )
        parser.add_argument(
            '-tz',
            '--tz_string',
            action='store',
            # type=str,
            dest='tz_string',
            # default=False,
            help='The timezone string that the file uses. All dates in the file must be in this timezone',
        )
        parser.add_argument(
            '-c',
            '--commit',
            action='store_true',
            dest='commit',
            help='It will commit the data to the database, ie it will create the zakanda bet trees',
        )
        parser.add_argument(
            '-nc',
            '--no-commit',
            action='store_true',
            dest='no-commit',
            help='It will not commit the data to the database. It will just check the validity of the data',
        )

    def handle(self, *args, **options):
        s3_bucket_name = options.get('s3_bucket_name', None)
        filename = options.get('filename', None)
        user_id = options.get('user_id', None)
        tz_string = options.get('tz_string', None)

        commit_arg = options.get('commit', None)
        no_commit_arg = options.get('no-commit', None)
        commit = False
        if commit_arg:
            if not no_commit_arg:
                commit = True
        else:
            if not no_commit_arg:
                logger.info('commit argument was not defined. --no-commit is assumed')

        register_history_bets(s3_bucket_name, filename, user_id, tz_string, commit)

        self.stdout.write('Done!\n')
