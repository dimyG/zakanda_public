# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import stream_django.activity


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('feeds', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FollowActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('verb', models.CharField(default='follow', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('actor', models.ForeignKey(related_name='follow_activities', to=settings.AUTH_USER_MODEL)),
                ('object', models.ForeignKey(related_name='followed_activities', to=settings.AUTH_USER_MODEL)),
            ],
            bases=(models.Model, stream_django.activity.Activity),
        ),
        migrations.AlterUniqueTogether(
            name='followactivity',
            unique_together=set([('actor', 'object')]),
        ),
    ]
