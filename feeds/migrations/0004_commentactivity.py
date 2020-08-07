# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import stream_django.activity


class Migration(migrations.Migration):

    dependencies = [
        ('django_comments', '0003_add_submit_date_index'),
        ('feeds', '0003_auto_20171206_1621'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommentActivity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('comment', models.OneToOneField(related_name='comment_activity', to='django_comments.Comment')),
            ],
            bases=(models.Model, stream_django.activity.Activity),
        ),
    ]
