# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0008_userprofile_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='wallet_balance',
            field=models.FloatField(default=0, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
