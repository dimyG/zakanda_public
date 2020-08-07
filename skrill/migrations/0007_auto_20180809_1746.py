# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('skrill', '0006_auto_20180809_1745'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentrequest',
            name='user',
            field=models.ForeignKey(related_name='payment_requests', verbose_name='User', to=settings.AUTH_USER_MODEL),
        ),
    ]
