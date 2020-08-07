# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('skrill', '0003_auto_20180703_1918'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transferrequest',
            name='submitted',
        ),
        migrations.AddField(
            model_name='transferrequest',
            name='prepared',
            field=models.BooleanField(default=False, help_text="If a 'prepare' transfer request has been send for this transfer_request. This flag has a meaning of existence despite the fatc that there is also an 'action' flag since you know if a prepare request has been sent", verbose_name='Is prepared', editable=False),
        ),
        migrations.AlterField(
            model_name='transferrequest',
            name='transaction_id',
            field=models.AutoField(help_text="It is the 'frn_trn_id' skrill field. Reference or identification number provided by the Merchant. MUST be unique for each transfer.", serialize=False, verbose_name='Transaction ID', primary_key=True),
        ),
        migrations.AlterField(
            model_name='transferstatusreport',
            name='status',
            field=models.IntegerField(help_text="Status of the transaction. 2 possible values: 'scheduled' (if beneficiary is not yet registered at Skrill) and 'processed' (if beneficiary is registered'", verbose_name='Status', choices=[(1, 'scheduled'), (2, 'processed')]),
        ),
    ]
