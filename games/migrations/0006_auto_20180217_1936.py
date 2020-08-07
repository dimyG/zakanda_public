# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0005_auto_20180217_1836'),
    ]

    operations = [
        migrations.RenameField(
            model_name='winnerofferodd',
            old_name='winner_odd',
            new_name='odd',
        ),
        migrations.AlterUniqueTogether(
            name='winnerofferodd',
            unique_together=set([('odd', 'winner_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
    ]
