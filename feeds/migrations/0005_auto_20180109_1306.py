# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0004_commentactivity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commentactivity',
            name='comment',
            field=models.OneToOneField(related_name='comment_activity', to='django_comments_xtd.XtdComment'),
        ),
    ]
