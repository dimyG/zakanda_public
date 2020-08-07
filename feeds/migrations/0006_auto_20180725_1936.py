# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import stream_django.activity


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bet_tagging', '0008_auto_20180725_1742'),
        ('feeds', '0005_auto_20180109_1306'),
    ]

    operations = [
        migrations.CreateModel(
            name='BetGroupFollowActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('verb', models.CharField(default='bet_group_follow', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('follow_object', models.ForeignKey(related_name='follow_activities', to='bet_tagging.BetTag')),
                ('user', models.ForeignKey(related_name='bet_group_follow_activities', to=settings.AUTH_USER_MODEL)),
            ],
            bases=(models.Model, stream_django.activity.Activity),
        ),
        migrations.AlterUniqueTogether(
            name='betgroupfollowactivity',
            unique_together=set([('user', 'follow_object')]),
        ),
    ]
