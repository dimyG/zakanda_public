# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('skrill', '0006_auto_20180809_1745'),
        ('bet_tagging', '0009_auto_20180808_1244'),
    ]

    operations = [
        migrations.CreateModel(
            name='GenericTransferReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('skrill_report', models.OneToOneField(related_name='transfer_report', to='skrill.TransferStatusReport')),
            ],
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='fully_paid',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='paid_installments',
        ),
        migrations.AddField(
            model_name='subscription',
            name='transfer_reports',
            field=models.ManyToManyField(related_name='subscriptions', to='bet_tagging.GenericTransferReport'),
        ),
    ]
