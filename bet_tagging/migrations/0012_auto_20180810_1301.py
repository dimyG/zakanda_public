# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0011_auto_20180810_1259'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='paymentreport',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='paymentreport',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='paymentreport',
            name='object_id',
        ),
    ]
