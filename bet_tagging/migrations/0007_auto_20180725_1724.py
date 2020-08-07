# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bet_tagging', '0006_auto_20180510_1652'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('price', models.PositiveIntegerField(choices=[(10, 10), (15, 15), (20, 20), (25, 25), (30, 30), (35, 35), (40, 40), (45, 45), (50, 50), (60, 60), (70, 70), (80, 80), (90, 90), (100, 100), (120, 120), (140, 140), (160, 160), (180, 180), (200, 200), (220, 220), (240, 240), (260, 260), (280, 280), (300, 300), (350, 350), (400, 400), (450, 450), (500, 500), (600, 600), (700, 700), (800, 800), (900, 900), (1000, 1000), (1250, 1250), (1500, 1500)])),
                ('duration', models.PositiveIntegerField(choices=[(30, 30), (90, 90)])),
                ('subscribers_limit', models.PositiveIntegerField(default=1000)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active', models.BooleanField(default=True)),
                ('recurring', models.BooleanField(default=False)),
                ('end_date', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('payment_report', models.OneToOneField(related_name='subscription', to='bet_tagging.PaymentReport')),
                ('service', models.ForeignKey(related_name='subscriptions', to='bet_tagging.Service')),
                ('user', models.ForeignKey(related_name='subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='bettag',
            name='type',
            field=models.CharField(default='Free', max_length=8, choices=[('Free', 'Free'), ('Premium', 'Premium'), ('Private', 'Private')]),
        ),
        migrations.AddField(
            model_name='service',
            name='bet_group',
            field=models.ForeignKey(related_name='services', to='bet_tagging.BetTag'),
        ),
        migrations.AddField(
            model_name='service',
            name='subscribers',
            field=models.ManyToManyField(related_name='services', through='bet_tagging.Subscription', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='service',
            unique_together=set([('bet_group', 'duration')]),
        ),
        migrations.AlterUniqueTogether(
            name='paymentreport',
            unique_together=set([('content_type', 'object_id')]),
        ),
    ]
