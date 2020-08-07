# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0005_auto_20180226_1732'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basicstats',
            name='bet_yield',
            field=models.FloatField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='num_bet_groups',
            field=models.PositiveIntegerField(default=1, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='num_bets',
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='num_followers',
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='num_following',
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='num_losses',
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='num_opens',
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='num_wins',
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='roi',
            field=models.FloatField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name='basicstats',
            name='score',
            field=models.FloatField(default=0, null=True),
        ),
    ]
