# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0008_auto_20180725_1742'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='fully_paid',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='subscription',
            name='paid_installments',
            field=models.IntegerField(default=0, help_text='Number of monthly payments made to the tipster.'),
        ),
        migrations.AlterField(
            model_name='service',
            name='price',
            field=models.PositiveIntegerField(choices=[(15, 15), (20, 20), (25, 25), (30, 30), (35, 35), (40, 40), (45, 45), (50, 50), (60, 60), (70, 70), (80, 80), (90, 90), (100, 100), (120, 120), (140, 140), (160, 160), (180, 180), (200, 200), (220, 220), (240, 240), (260, 260), (280, 280), (300, 300), (350, 350), (400, 400), (450, 450), (500, 500), (600, 600), (700, 700), (800, 800), (900, 900), (1000, 1000), (1250, 1250), (1500, 1500), (2000, 2000), (2500, 2500), (3000, 3000)]),
        ),
    ]
