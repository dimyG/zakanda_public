# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BetEventActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('verb', models.CharField(default='submit_bet_event', max_length=20)),
                ('num_bet_events', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('actor', models.ForeignKey(related_name='bev_activities', to=settings.AUTH_USER_MODEL)),
                ('bet_event', models.ForeignKey(related_name='bev_activities', to='games.BetEvent')),
                ('event', models.ForeignKey(related_name='bev_activities', to='games.Event')),
            ],
        ),
        migrations.CreateModel(
            name='RawBetEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('choice', models.CharField(max_length=15)),
                ('event', models.ForeignKey(to='games.Event')),
                ('market_type', models.ForeignKey(to='games.MarketType')),
            ],
        ),
        migrations.CreateModel(
            name='TotalBetActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('verb', models.CharField(default='submit_total_bet', max_length=20)),
                ('num_bet_events', models.IntegerField()),
                ('time', models.DateTimeField(default=None, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('actor', models.ForeignKey(related_name='total_bet_activities', to=settings.AUTH_USER_MODEL)),
                ('object', models.OneToOneField(related_name='activities', to='games.TotalBet')),
            ],
        ),
        migrations.AddField(
            model_name='beteventactivity',
            name='object',
            field=models.ForeignKey(related_name='bev_activities', to='feeds.RawBetEvent'),
        ),
        migrations.AddField(
            model_name='beteventactivity',
            name='total_bet',
            field=models.ForeignKey(related_name='bev_activities', to='games.TotalBet'),
        ),
        migrations.AlterUniqueTogether(
            name='rawbetevent',
            unique_together=set([('event', 'market_type', 'choice')]),
        ),
    ]
