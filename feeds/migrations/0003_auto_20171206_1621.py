# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0002_auto_20171205_1957'),
    ]

    operations = [
        migrations.RenameField(
            model_name='followactivity',
            old_name='object',
            new_name='target_user',
        ),
        migrations.RenameField(
            model_name='followactivity',
            old_name='actor',
            new_name='user',
        ),
        migrations.AlterUniqueTogether(
            name='followactivity',
            unique_together=set([('user', 'target_user')]),
        ),
    ]
