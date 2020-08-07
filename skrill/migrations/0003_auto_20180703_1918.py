# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('skrill', '0002_auto_20180703_1630'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transferrequest',
            name='action',
            field=models.CharField(default='prepare', max_length=8, choices=[('prepare', 'prepare'), ('transfer', 'transfer')]),
        ),
    ]
