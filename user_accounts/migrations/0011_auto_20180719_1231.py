# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0010_legalsellerinfo_personsellerinfo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='legalsellerinfo',
            name='tax_number',
            field=models.CharField(help_text='Tax Identification Number (TIN)', unique=True, max_length=15),
        ),
        migrations.AlterField(
            model_name='personsellerinfo',
            name='tax_number',
            field=models.CharField(help_text='Tax Identification Number (TIN)', unique=True, max_length=15),
        ),
    ]
