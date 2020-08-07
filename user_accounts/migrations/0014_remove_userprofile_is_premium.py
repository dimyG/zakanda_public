# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0013_auto_20180808_1244'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='is_premium',
        ),
    ]
