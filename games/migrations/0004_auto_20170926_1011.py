# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0003_auto_20170812_1821'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='status',
            field=models.CharField(default='Not Started', max_length=35, choices=[('Not Started', 'Not Started'), ('Finished', 'Finished'), ('Finished AET', 'Finished AET (Added Extra Time)'), ('Finished AP', 'Finished AP (Added Penalty)'), ('Cancelled', 'Cancelled'), ('Postponed', 'Postponed'), ('Abandoned', 'Abandoned'), ('Interrupted', 'Interrupted'), ('Suspended', 'Suspended'), ('Deleted', 'Deleted'), ('in_play', 'in_play')]),
        ),
        migrations.AlterField(
            model_name='result',
            name='type',
            field=models.CharField(default='IN_PLAY', max_length=15, choices=[('IN_PLAY', 'IN_PLAY'), ('HT', 'HT'), ('FT', 'FT'), ('ET_HT', 'ET_HT'), ('ET', 'ET'), ('PEN', 'PEN'), ('Postponed', 'Postponed'), ('Cancelled', 'Cancelled'), ('Abandoned', 'Abandoned'), ('Interrupted', 'Interrupted'), ('Suspended', 'Suspended'), ('Deleted', 'Deleted')]),
        ),
        migrations.AlterField(
            model_name='totalbet',
            name='description',
            field=models.CharField(default=None, max_length=5000, null=True),
        ),
    ]
