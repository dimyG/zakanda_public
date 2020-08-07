# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='competition',
            name='country',
            field=models.ForeignKey(related_name='competitions', to='games.Country'),
        ),
        migrations.AlterField(
            model_name='competition',
            name='sport',
            field=models.ForeignKey(related_name='competitions', to='games.Sport'),
        ),
    ]
