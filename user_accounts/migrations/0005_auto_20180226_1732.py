# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0004_auto_20180226_1617'),
    ]

    operations = [
        migrations.AddField(
            model_name='basicstats',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 2, 26, 15, 32, 21, 984000, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='basicstats',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 2, 26, 15, 32, 35, 372000, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
