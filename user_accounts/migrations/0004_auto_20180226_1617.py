# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0003_auto_20180226_1551'),
    ]

    operations = [
        migrations.AddField(
            model_name='basicstats',
            name='num_followers',
            field=models.PositiveIntegerField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='basicstats',
            name='num_following',
            field=models.PositiveIntegerField(default=None, null=True),
        ),
    ]
