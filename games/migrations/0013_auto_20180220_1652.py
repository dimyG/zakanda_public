# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0012_auto_20180217_2242'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asianhandicapofferodd',
            name='bookmaker',
            field=models.ForeignKey(related_name='as_handicap_offer_odds', to='games.Bookmaker'),
        ),
        migrations.AlterField(
            model_name='asianhandicapofferodd',
            name='offer',
            field=models.ForeignKey(related_name='offer_odds', to='games.AsianHandicapOffer'),
        ),
        migrations.AlterField(
            model_name='asianhandicapofferodd',
            name='source',
            field=models.ForeignKey(related_name='as_handicap_offer_odds', to='games.Source'),
        ),
        migrations.AlterField(
            model_name='doublechanceofferodd',
            name='bookmaker',
            field=models.ForeignKey(related_name='dc_offer_odds', to='games.Bookmaker'),
        ),
        migrations.AlterField(
            model_name='doublechanceofferodd',
            name='offer',
            field=models.ForeignKey(related_name='offer_odds', to='games.DoubleChanceOffer'),
        ),
        migrations.AlterField(
            model_name='doublechanceofferodd',
            name='source',
            field=models.ForeignKey(related_name='dc_offer_odds', to='games.Source'),
        ),
        migrations.AlterField(
            model_name='handicapofferodd',
            name='bookmaker',
            field=models.ForeignKey(related_name='handicap_offer_odds', to='games.Bookmaker'),
        ),
        migrations.AlterField(
            model_name='handicapofferodd',
            name='offer',
            field=models.ForeignKey(related_name='offer_odds', to='games.HandicapOffer'),
        ),
        migrations.AlterField(
            model_name='handicapofferodd',
            name='source',
            field=models.ForeignKey(related_name='handicap_offer_odds', to='games.Source'),
        ),
        migrations.AlterField(
            model_name='overunderofferodd',
            name='bookmaker',
            field=models.ForeignKey(related_name='ovun_offer_odds', to='games.Bookmaker'),
        ),
        migrations.AlterField(
            model_name='overunderofferodd',
            name='offer',
            field=models.ForeignKey(related_name='offer_odds', to='games.OverUnderOffer'),
        ),
        migrations.AlterField(
            model_name='overunderofferodd',
            name='source',
            field=models.ForeignKey(related_name='ovun_offer_odds', to='games.Source'),
        ),
        migrations.AlterField(
            model_name='winnerofferodd',
            name='bookmaker',
            field=models.ForeignKey(related_name='winner_offer_odds', to='games.Bookmaker'),
        ),
        migrations.AlterField(
            model_name='winnerofferodd',
            name='offer',
            field=models.ForeignKey(related_name='offer_odds', to='games.WinnerOffer'),
        ),
        migrations.AlterField(
            model_name='winnerofferodd',
            name='source',
            field=models.ForeignKey(related_name='winner_offer_odds', to='games.Source'),
        ),
    ]
