# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0012_auto_20180719_1744'),
    ]

    operations = [
        migrations.AddField(
            model_name='legalsellerinfo',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 8, 8, 9, 44, 4, 189000, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='legalsellerinfo',
            name='percentage_tier',
            field=models.IntegerField(default=70, help_text='The percent of subscriptions that goes to tipster.', choices=[(40, 40), (50, 50), (60, 60), (70, 70), (80, 80), (90, 90)]),
        ),
        migrations.AddField(
            model_name='legalsellerinfo',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 8, 8, 9, 44, 9, 545000, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='personsellerinfo',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 8, 8, 9, 44, 16, 307000, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='personsellerinfo',
            name='percentage_tier',
            field=models.IntegerField(default=70, help_text='The percent of subscriptions that goes to tipster.', choices=[(40, 40), (50, 50), (60, 60), (70, 70), (80, 80), (90, 90)]),
        ),
        migrations.AddField(
            model_name='personsellerinfo',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 8, 8, 9, 44, 21, 390000, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
