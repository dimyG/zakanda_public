# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user_accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BasicStats',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('score', models.FloatField(default=None)),
                ('bet_yield', models.FloatField(default=None)),
                ('roi', models.FloatField(default=None)),
                ('num_bets', models.PositiveIntegerField(default=None)),
                ('num_opens', models.PositiveIntegerField(default=None)),
                ('num_wins', models.PositiveIntegerField(default=None)),
                ('num_losses', models.PositiveIntegerField(default=None)),
                ('num_bet_groups', models.PositiveIntegerField(default=None)),
                ('user', models.OneToOneField(related_name='basic_stats', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
