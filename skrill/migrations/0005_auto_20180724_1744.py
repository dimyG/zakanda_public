# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('skrill', '0004_auto_20180706_1758'),
    ]

    operations = [
        migrations.AddField(
            model_name='statusreport',
            name='field_1',
            field=models.CharField(default=None, max_length=240, blank=True, help_text='Custom merchant field 1', null=True, verbose_name='Field 1'),
        ),
        migrations.AddField(
            model_name='statusreport',
            name='field_2',
            field=models.CharField(default=None, max_length=240, blank=True, help_text='Custom merchant field 1', null=True, verbose_name='Field 2'),
        ),
        migrations.AddField(
            model_name='statusreport',
            name='field_3',
            field=models.CharField(default=None, max_length=240, blank=True, help_text='Custom merchant field 1', null=True, verbose_name='Field 3'),
        ),
        migrations.AddField(
            model_name='statusreport',
            name='field_4',
            field=models.CharField(default=None, max_length=240, blank=True, help_text='Custom merchant field 1', null=True, verbose_name='Field 4'),
        ),
        migrations.AddField(
            model_name='statusreport',
            name='field_5',
            field=models.CharField(default=None, max_length=240, blank=True, help_text='Custom merchant field 1', null=True, verbose_name='Field 5'),
        ),
    ]
