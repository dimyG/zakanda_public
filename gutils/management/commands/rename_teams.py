# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
import games.models
import gutils.utils


logger = logging.getLogger(__name__)


def rename(source_name, sid, existing_sname, new_sname, new_gname):
    team_info = games.models.TeamInfo.objects.get(source__name=source_name, sid=sid, sname=existing_sname)
    team = team_info.team
    team.generic_name = new_gname
    team.save()
    team_info.sname = new_sname
    team_info.save()


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

    def handle(self, *args, **kwargs):
        source_names = gutils.utils.get_command_sources(*args, **kwargs)
        source_name = source_names[0]

        # t1 = [15064, "", "Everton S.A.D.P", "Everton S.A.D.P"]
        # t2 = [13, '', "Everton", "Everton"]
        #
        # t3 = [976, '', "Liverpool Montevideo", "Liverpool Montevideo"]
        # t4 = [8, '', "Liverpool", "Liverpool"]

        t3 = [526, 'Aris Limassol', "Aris", "Aris Limassol"]
        t4 = [9848, 'Aris Women', "Aris Women", "Aris"]

        for team_data in [t3, t4]:
            sid = team_data[0]
            existing_sname = team_data[1]
            new_sname = team_data[2]
            new_gname = team_data[3]
            rename(source_name, sid=sid, existing_sname=existing_sname, new_sname=new_sname, new_gname=new_gname)

        self.stdout.write('Done!\n')
