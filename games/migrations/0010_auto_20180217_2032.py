# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0009_auto_20180217_2010'),
    ]

    operations = [
        migrations.RenameField(
            model_name='winnerofferodd',
            old_name='winner_offer',
            new_name='offer',
        ),
        migrations.AlterUniqueTogether(
            name='winnerofferodd',
            unique_together=set([('odd', 'offer', 'bookmaker', 'source', 'timestamp')]),
        ),
    ]
