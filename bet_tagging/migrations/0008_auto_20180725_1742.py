# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0007_auto_20180725_1724'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentreport',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 7, 25, 14, 42, 12, 962000, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='paymentreport',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(2018, 7, 25, 14, 42, 15, 961000, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
