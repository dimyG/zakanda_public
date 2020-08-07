# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0002_auto_20180228_1326'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deposit',
            name='user',
        ),
        migrations.RemoveField(
            model_name='withdrawal',
            name='user',
        ),
    ]
