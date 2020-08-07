# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0003_auto_20180228_1623'),
    ]

    operations = [
        migrations.AddField(
            model_name='bettag',
            name='type',
            field=models.CharField(default='Free', max_length=8, choices=[('Free', 'Free'), ('Premium', 'Premium'), ('Private', 'Private'), ('Archived', 'Archived')]),
        ),
    ]
