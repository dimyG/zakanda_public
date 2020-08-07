# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0015_event_public'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='round',
            field=models.PositiveIntegerField(default=None, null=True, blank=True),
        ),
    ]
