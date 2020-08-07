# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import skrill.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('skrill', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransferRequest',
            fields=[
                ('transaction_id', models.AutoField(help_text='Reference or identification number provided by the Merchant. MUST be unique for each transfer', serialize=False, verbose_name='Transaction ID', primary_key=True)),
                ('test', models.BooleanField(default=False, verbose_name='Is test')),
                ('submitted', models.BooleanField(default=False, help_text='If Skrill has created a session id for a specific transfer request, thetransfer request is marked as submitted in the database. It has beensubmitted to Skrill and a session id has been created for it.', verbose_name='Is submitted', editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(default='prepare', max_length=7, choices=[('prepare', 'prepare'), ('transfer', 'transfer')])),
                ('email', models.EmailField(default=b'dimgeows@yahoo.com', help_text='Your Merchant account', max_length=50, verbose_name='Merchant account')),
                ('password', models.CharField(default=skrill.models.password_hash, help_text='The MD5 hash of your API/MQI password', max_length=32)),
                ('amount', models.DecimalField(help_text="Amount to be transferred. Note: Do not include the trailing zeroes if the amount is a natural number. For example: '23' (not '23.00')", verbose_name='Amount', max_digits=19, decimal_places=2)),
                ('currency', models.CharField(default=b'EUR', help_text='3-letter code of the currency of the amount according to ISO 4217', max_length=3, verbose_name='Currency', choices=[(b'EUR', b'Euro'), (b'TWD', b'Taiwan Dollar'), (b'USD', b'U.S. Dollar'), (b'THB', b'Thailand Baht'), (b'GBP', b'British Pound'), (b'CZK', b'Czech Koruna'), (b'HKD', b'Hong Kong Dollar'), (b'HUF', b'Hungarian Forint'), (b'SGD', b'Singapore Dollar'), (b'SKK', b'Slovakian Koruna'), (b'JPY', b'Japanese Yen'), (b'EEK', b'Estonian Kroon'), (b'CAD', b'Canadian Dollar'), (b'BGN', b'Bulgarian Leva'), (b'AUD', b'Australian Dollar'), (b'PLN', b'Polish Zloty'), (b'CHF', b'Swiss Franc'), (b'ISK', b'Iceland Krona'), (b'DKK', b'Danish Krone'), (b'INR', b'Indian Rupee'), (b'SEK', b'Swedish Krona'), (b'LVL', b'Latvian Lat'), (b'NOK', b'Norwegian Krone'), (b'KRW', b'South-Korean Won'), (b'ILS', b'Israeli Shekel'), (b'ZAR', b'South-African Rand'), (b'MYR', b'Malaysian Ringgit'), (b'RON', b'Romanian Leu New'), (b'NZD', b'New Zealand Dollar'), (b'HRK', b'Croatian Kuna'), (b'TRY', b'New Turkish Lira'), (b'LTL', b'Lithuanian Litas'), (b'AED', b'Utd. Arab Emir. Dirham'), (b'JOD', b'Jordanian Dinar'), (b'MAD', b'Moroccan Dirham'), (b'OMR', b'Omani Rial'), (b'QAR', b'Qatari Rial'), (b'RSD', b'Serbian dinar'), (b'SAR', b'Saudi Riyal'), (b'TND', b'Tunisian Dinar')])),
                ('bnf_email', models.EmailField(max_length=50, verbose_name='Recipients email')),
                ('subject', models.CharField(default='Money Received', help_text='Subject of the notification email. Up to 250 1-byte characters.', max_length=250)),
                ('note', models.CharField(default='zakanda just sent you money through Skrill', help_text='Comment to be included in the notification email. Up to 2000 1-byte characters.', max_length=2000)),
                ('sid', models.CharField(default=None, max_length=50, blank=True, help_text='The latest received session id', null=True, verbose_name='Session Id')),
                ('user', models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='TransferStatusReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('mb_amount', models.DecimalField(help_text='Amount paid in the currency of your Skrill account.', verbose_name='MB Amount', max_digits=19, decimal_places=2)),
                ('mb_currency', models.CharField(help_text='Currency of your Skrill account', max_length=3, verbose_name='MB Currency', choices=[(b'EUR', b'Euro'), (b'TWD', b'Taiwan Dollar'), (b'USD', b'U.S. Dollar'), (b'THB', b'Thailand Baht'), (b'GBP', b'British Pound'), (b'CZK', b'Czech Koruna'), (b'HKD', b'Hong Kong Dollar'), (b'HUF', b'Hungarian Forint'), (b'SGD', b'Singapore Dollar'), (b'SKK', b'Slovakian Koruna'), (b'JPY', b'Japanese Yen'), (b'EEK', b'Estonian Kroon'), (b'CAD', b'Canadian Dollar'), (b'BGN', b'Bulgarian Leva'), (b'AUD', b'Australian Dollar'), (b'PLN', b'Polish Zloty'), (b'CHF', b'Swiss Franc'), (b'ISK', b'Iceland Krona'), (b'DKK', b'Danish Krone'), (b'INR', b'Indian Rupee'), (b'SEK', b'Swedish Krona'), (b'LVL', b'Latvian Lat'), (b'NOK', b'Norwegian Krone'), (b'KRW', b'South-Korean Won'), (b'ILS', b'Israeli Shekel'), (b'ZAR', b'South-African Rand'), (b'MYR', b'Malaysian Ringgit'), (b'RON', b'Romanian Leu New'), (b'NZD', b'New Zealand Dollar'), (b'HRK', b'Croatian Kuna'), (b'TRY', b'New Turkish Lira'), (b'LTL', b'Lithuanian Litas'), (b'AED', b'Utd. Arab Emir. Dirham'), (b'JOD', b'Jordanian Dinar'), (b'MAD', b'Moroccan Dirham'), (b'OMR', b'Omani Rial'), (b'QAR', b'Qatari Rial'), (b'RSD', b'Serbian dinar'), (b'SAR', b'Saudi Riyal'), (b'TND', b'Tunisian Dinar')])),
                ('mb_transaction_id', models.BigIntegerField(help_text="Moneybookers' unique transaction ID for the transfer.", verbose_name='Skrill transaction ID')),
                ('status', models.IntegerField(help_text='Status of the transaction.', verbose_name='Status', choices=[(1, 'scheduled'), (2, 'processed')])),
                ('status_msg', models.CharField(max_length=50, verbose_name='Status message')),
                ('claimed', models.BooleanField(default=True, help_text="This flag is taken under consideration only for 'scheduled' transfers. If the user doesn't claim the funds within the skrill timeframe (14 days?)then the funds are returned to the sender (zakanda) and must appear in users zakanda wallet. In this case the transfer_status obj is marked as unclaimed and the status remains 'scheduled'. Skrill docs don't mention any other possible status (like cancelled) so in order to identify a cancelled scheduled transfer we mark it with the flag unclaimed. So a 'scheduled' transfer with claim=False is a cancelled one.(The unclaimed funds do not participate in the withdraws calculation)")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transfer_request', models.ForeignKey(help_text='The TransferRequest object the execution request of which, returned this Status Report', to='skrill.TransferRequest')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='transferstatusreport',
            unique_together=set([('mb_transaction_id', 'status')]),
        ),
    ]
