# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0011_auto_20180217_2041'),
    ]

    operations = [
        migrations.RenameField(
            model_name='asianhandicapoffer',
            old_name='asian_handicap_odds',
            new_name='odds',
        ),
        migrations.RenameField(
            model_name='doublechanceoffer',
            old_name='double_chance_odds',
            new_name='odds',
        ),
        migrations.RenameField(
            model_name='handicapoffer',
            old_name='handicap_odds',
            new_name='odds',
        ),
        migrations.RenameField(
            model_name='overunderoffer',
            old_name='over_under_odds',
            new_name='odds',
        ),
        migrations.RenameField(
            model_name='winneroffer',
            old_name='winner_odds',
            new_name='odds',
        ),
    ]
