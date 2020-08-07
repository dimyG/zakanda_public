# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bet_tagging', '0004_bettag_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationSubscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.BooleanField(default=True)),
                ('in_app', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bet_group', models.ForeignKey(related_name='notification_subscriptions', to='bet_tagging.BetTag')),
                ('user', models.ForeignKey(related_name='notification_subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='notificationsubscription',
            unique_together=set([('user', 'bet_group')]),
        ),
    ]
