# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bet_tagging', '0012_auto_20180810_1301'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentreport',
            name='skrill_report',
            field=models.OneToOneField(related_name='generic_report', default=1, to='skrill.StatusReport'),
            preserve_default=False,
        ),
    ]
