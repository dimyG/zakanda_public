# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0004_auto_20170926_1011'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asianhandicapofferodd',
            name='asian_handicap_odd',
            field=models.ForeignKey(related_name='offer_odds', to='games.AsianHandicapOdd'),
        ),
        migrations.AlterField(
            model_name='doublechanceofferodd',
            name='double_chance_odd',
            field=models.ForeignKey(related_name='offer_odds', to='games.DoubleChanceOdd'),
        ),
        migrations.AlterField(
            model_name='handicapofferodd',
            name='handicap_odd',
            field=models.ForeignKey(related_name='offer_odds', to='games.HandicapOdd'),
        ),
        migrations.AlterField(
            model_name='overunderofferodd',
            name='over_under_odd',
            field=models.ForeignKey(related_name='offer_odds', to='games.OverUnderOdd'),
        ),
        migrations.AlterField(
            model_name='winnerofferodd',
            name='winner_odd',
            field=models.ForeignKey(related_name='offer_odds', to='games.WinnerOdd'),
        ),
    ]
