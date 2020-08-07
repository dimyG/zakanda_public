# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0013_auto_20180220_1652'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asianhandicapoffer',
            name='event',
            field=models.ForeignKey(related_name='asian_handicap_offers', to='games.Event'),
        ),
        migrations.AlterField(
            model_name='asianhandicapoffer',
            name='market_result',
            field=models.ForeignKey(related_name='asian_handicap_offers', to='games.MarketResult'),
        ),
        migrations.AlterField(
            model_name='doublechanceoffer',
            name='market_result',
            field=models.ForeignKey(related_name='double_chance_offers', to='games.MarketResult'),
        ),
        migrations.AlterField(
            model_name='handicapoffer',
            name='event',
            field=models.ForeignKey(related_name='handicap_offers', to='games.Event'),
        ),
        migrations.AlterField(
            model_name='handicapoffer',
            name='market_result',
            field=models.ForeignKey(related_name='handicap_offers', to='games.MarketResult'),
        ),
        migrations.AlterField(
            model_name='overunderoffer',
            name='event',
            field=models.ForeignKey(related_name='over_under_offers', to='games.Event'),
        ),
        migrations.AlterField(
            model_name='overunderoffer',
            name='market_result',
            field=models.ForeignKey(related_name='over_under_offers', to='games.MarketResult'),
        ),
        migrations.AlterField(
            model_name='winneroffer',
            name='market_result',
            field=models.ForeignKey(related_name='winner_offers', to='games.MarketResult'),
        ),
    ]
