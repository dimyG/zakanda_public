# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0014_auto_20180221_1201'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='public',
            field=models.BooleanField(default=True),
        ),
    ]
