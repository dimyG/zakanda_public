# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0007_auto_20180217_1953'),
    ]

    operations = [
        migrations.RenameField(
            model_name='overunderofferodd',
            old_name='over_under_odd',
            new_name='odd',
        ),
        migrations.AlterUniqueTogether(
            name='overunderofferodd',
            unique_together=set([('odd', 'over_under_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
    ]
