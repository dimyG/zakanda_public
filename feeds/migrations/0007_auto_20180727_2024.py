# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0006_auto_20180725_1936'),
    ]

    operations = [
        migrations.AlterField(
            model_name='betgroupfollowactivity',
            name='verb',
            field=models.CharField(default='bet_group_follow', max_length=25),
        ),
    ]
