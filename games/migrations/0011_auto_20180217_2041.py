# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0010_auto_20180217_2032'),
    ]

    operations = [
        migrations.RenameField(
            model_name='asianhandicapofferodd',
            old_name='asian_handicap_offer',
            new_name='offer',
        ),
        migrations.RenameField(
            model_name='doublechanceofferodd',
            old_name='double_chance_offer',
            new_name='offer',
        ),
        migrations.RenameField(
            model_name='handicapofferodd',
            old_name='handicap_offer',
            new_name='offer',
        ),
        migrations.RenameField(
            model_name='overunderofferodd',
            old_name='over_under_offer',
            new_name='offer',
        ),
        migrations.AlterUniqueTogether(
            name='asianhandicapofferodd',
            unique_together=set([('odd', 'offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='doublechanceofferodd',
            unique_together=set([('odd', 'offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='handicapofferodd',
            unique_together=set([('odd', 'offer', 'bookmaker', 'source', 'timestamp')]),
        ),
        migrations.AlterUniqueTogether(
            name='overunderofferodd',
            unique_together=set([('odd', 'offer', 'bookmaker', 'source', 'timestamp')]),
        ),
    ]
