# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0005_auto_20180427_1335'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bettag',
            name='type',
            field=models.CharField(default='Free', max_length=8, choices=[('Free', 'Free'), ('Private', 'Private')]),
        ),
    ]
