# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0006_auto_20180302_1721'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='public',
            field=models.BooleanField(default=False),
        ),
    ]
