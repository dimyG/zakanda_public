# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0006_auto_20180217_1936'),
    ]

    operations = [
        migrations.RenameField(
            model_name='doublechanceofferodd',
            old_name='double_chance_odd',
            new_name='odd',
        ),
        migrations.AlterUniqueTogether(
            name='doublechanceofferodd',
            unique_together=set([('odd', 'double_chance_offer', 'bookmaker', 'source', 'timestamp')]),
        ),
    ]
