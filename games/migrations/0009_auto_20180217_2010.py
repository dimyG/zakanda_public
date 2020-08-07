# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0008_auto_20180217_1959'),
    ]

    operations = [
        migrations.RenameField(
            model_name='asianhandicapofferodd',
            old_name='asian_handicap_odd',
            new_name='odd',
        ),
        migrations.RenameField(
            model_name='handicapofferodd',
            old_name='handicap_odd',
            new_name='odd',
        ),
        migrations.AlterUniqueTogether(
            name='asianhandicapofferodd',
            unique_together=set([('odd', 'asian_handicap_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='handicapofferodd',
            unique_together=set([('odd', 'handicap_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
    ]
