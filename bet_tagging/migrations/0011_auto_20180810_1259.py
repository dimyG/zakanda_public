# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('skrill', '0007_auto_20180809_1746'),
        ('bet_tagging', '0010_auto_20180809_1745'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentreport',
            name='skrill_report',
            field=models.OneToOneField(related_name='generic_report', null=True, default=None, blank=True, to='skrill.StatusReport'),
        ),
        migrations.AlterField(
            model_name='generictransferreport',
            name='skrill_report',
            field=models.OneToOneField(related_name='generic_report', to='skrill.TransferStatusReport'),
        ),
    ]
