# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawal',
            name='is_calculated',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='deposit',
            name='amount',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(0.01), django.core.validators.MaxValueValidator(999999)]),
        ),
        migrations.AlterField(
            model_name='withdrawal',
            name='amount',
            field=models.FloatField(validators=[django.core.validators.MinValueValidator(0.01)]),
        ),
    ]
