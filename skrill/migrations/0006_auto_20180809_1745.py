# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('skrill', '0005_auto_20180724_1744'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transferrequest',
            name='prepared',
            field=models.BooleanField(default=False, help_text="If a 'prepare' transfer request has been send for this transfer_request. This flag has a meaning of existence despite the fact that there is also an 'action' flag since you know if a prepare request has been sent", verbose_name='Is prepared', editable=False),
        ),
        migrations.AlterField(
            model_name='transferrequest',
            name='user',
            field=models.ForeignKey(related_name='transfer_requests', verbose_name='User', to=settings.AUTH_USER_MODEL),
        ),
    ]
