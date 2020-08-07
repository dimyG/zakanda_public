# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_auto_20170807_1603'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teaminfo',
            name='team',
            field=models.ForeignKey(related_name='team_infos', to='games.Team'),
        ),
    ]
