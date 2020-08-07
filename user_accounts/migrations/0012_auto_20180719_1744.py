# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_accounts', '0011_auto_20180719_1231'),
    ]

    operations = [
        migrations.AddField(
            model_name='personsellerinfo',
            name='first_name',
            field=models.CharField(default='dimi', max_length=30, verbose_name='first name'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='personsellerinfo',
            name='last_name',
            field=models.CharField(default='geo', max_length=30, verbose_name='last name'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='legalsellerinfo',
            name='payment_method',
            field=models.CharField(default='skrill', help_text='The payment method the tipster wants to be paid with.', max_length=15),
        ),
        migrations.AlterField(
            model_name='legalsellerinfo',
            name='payments_email',
            field=models.EmailField(help_text='The email the funds will be paid to. It must be connected to the sellers account on the selected payment method', max_length=254),
        ),
        migrations.AlterField(
            model_name='personsellerinfo',
            name='payment_method',
            field=models.CharField(default='skrill', help_text='The payment method the tipster wants to be paid with.', max_length=15),
        ),
        migrations.AlterField(
            model_name='personsellerinfo',
            name='payments_email',
            field=models.EmailField(help_text='The email the funds will be paid to. It must be connected to the sellers account on the selected payment method', max_length=254),
        ),
    ]
