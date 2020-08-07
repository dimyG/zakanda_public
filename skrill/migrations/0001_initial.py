# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import multiselectfield.db.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentRequest',
            fields=[
                ('test', models.BooleanField(default=False, verbose_name='Is test')),
                ('submitted', models.BooleanField(default=False, help_text='If Skrill has created a session id for a specific payment request, thepayment request is marked as submitted in the database. It has beensubmitted to Skrill and a session id has been created for it.', verbose_name='Is submitted', editable=False)),
                ('status_response_received', models.BooleanField(default=False, help_text="If True then a call to get the status report for this transaction has been made and a status response has been returned. The response can be either a normal status report response with a status value, or a 'transaction doesn't exist' response. These transactions that don't exist in Skrill are the transactions that we want to be able to identify. These transactions would have no associated status report since Skrill doesn't support a status value for these transactions and their status_response_received flag will be True.These are paymentRequests that are never executed. For example the user presses the deposit button, the payment request is submitted, a session id is created for it by Skrill, but the user doesn't complete the payment. If you ask for a status report for such a payment request you will get a 'doesn't exist' response. Since their value will be True will can separate themfrom transaction that don;t have an associated status report and their value is False. For these transactions the status must be asked", verbose_name='Is a status response received')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transaction_id', models.AutoField(help_text='Reference or identification number provided by the Merchant. MUST be unique for each payment', serialize=False, verbose_name='Transaction ID', primary_key=True)),
                ('pay_to_email', models.EmailField(default=b'dimgeows@yahoo.com', help_text="Email address of the Merchant's moneybookers.com account.", max_length=50, verbose_name='Merchant Email')),
                ('recipient_description', models.CharField(default='Zakanda Test', max_length=30, blank=True, help_text=' A description to be shown on the Skrill payment page in the logo area if there is no logo_url parameter. If no value is submitted and there is no logo, the pay_to_email value is shown as the recipient of the payment. ', null=True, verbose_name='Merchant description')),
                ('return_url', models.URLField(default=None, max_length=240, blank=True, help_text='URL to which the customer will be returned when the payment is made. If this field is not filled, the gateway window will simply close automatically at the end of the transaction, so that the customer will be returned to the page on your website from where they were redirected to Skrill. A secure return URL option is available.', null=True, verbose_name='Return URL')),
                ('return_url_text', models.CharField(default='Return to zakanda', max_length=35, blank=True, help_text='The text on the button when the user finishes his payment.', null=True, verbose_name='Return URL text')),
                ('return_url_target', models.SmallIntegerField(default=1, help_text='Specifies a target in which the return_url value will be called upon successful payment from customer.', verbose_name='Return URL target', choices=[(1, b'_top'), (2, b'_parent'), (3, b'_self'), (4, b'_blank')])),
                ('cancel_url', models.URLField(default=None, max_length=240, blank=True, help_text='URL to which the customer is returned if the payment is cancelled or fails. If no cancel URL is provided the Cancel button is not displayed', null=True, verbose_name='Cancel URL')),
                ('cancel_url_target', models.SmallIntegerField(default=1, help_text='Specifies a target in which the cancel_url value will be called upon cancellation of payment from customer.', verbose_name='Cancel URL target', choices=[(1, b'_top'), (2, b'_parent'), (3, b'_self'), (4, b'_blank')])),
                ('status_url', models.CharField(default=None, max_length=400, blank=True, help_text='URL to which the transaction details will be posted after the payment process is complete. Alternatively, you may specify an email address to which you would like to receive the results.', null=True, verbose_name='Status URL')),
                ('status_url2', models.CharField(default=None, max_length=400, blank=True, help_text='Second URL to which the transaction details will be posted after the payment process is complete. Alternatively, you may specify an email address to which you would like to receive the results.', null=True, verbose_name='Status URL 2')),
                ('language', models.CharField(default='EN', help_text="2-letter code of the language used for Skrill (Moneybookers)' pages.", max_length=2, verbose_name='Language', choices=[(b'EN', b'EN'), (b'DE', b'DE'), (b'ES', b'ES'), (b'FR', b'FR'), (b'IT', b'IT'), (b'PL', b'PL'), (b'GR', b'GR'), (b'RO', b'RO'), (b'RU', b'RU'), (b'TR', b'TR'), (b'CN', b'CN'), (b'CZ', b'CZ'), (b'NL', b'NL'), (b'DA', b'DA'), (b'SV', b'SV'), (b'FI', b'FI')])),
                ('logo_url', models.URLField(default=None, max_length=240, blank=True, help_text='The URL of the logo which you would like to appear at the top of the gateway. The logo must be accessible via HTTPS otherwise it will not be shown. For best integration results we recommend that Merchants use logos with dimensions up to 200px in width and 50px in height.', null=True, verbose_name='Logo URL')),
                ('prepare_only', models.BooleanField(default=True, help_text='Forces only the SID to be returned without the actual page. Useful when using the secure method to redirect the customer to Quick Checkout.', verbose_name='Prepare only')),
                ('dynamic_descriptor', models.CharField(default=None, max_length=50, null=True, help_text='When a customer pays through Skrill, Skrill submits a preconfigured descriptor with the transaction, containing your business trading name/ brand name. The descriptor is typically displayed on the bank or credit card statement of the customer. For Klarna and Direct Debit payment methods, you can submit a dynamic_descriptor, which will override the default value stored by Skrill.', blank=True)),
                ('sid', models.CharField(default=None, max_length=32, null=True, help_text='This is an optional parameter containing the Session ID returned by the prepare_only call. If you use this parameter you should not supply any other parameters.', blank=True)),
                ('rid', models.CharField(help_text='Merchants can pass the unique referral ID or email of the affiliate from which the customer is referred. The rid value must be included within the actual payment request.', max_length=100, null=True, verbose_name='Referral ID', blank=True)),
                ('ext_ref_id', models.CharField(help_text='Merchants can pass additional identifier in this field in order to track affiliates. You MUST inform your account manager about the exact value that will be submitted so that affiliates can be tracked.', max_length=100, null=True, verbose_name='Extra Referral ID', blank=True)),
                ('Field1', models.CharField(help_text='Custom merchant field 1', max_length=240, null=True, verbose_name='Field 1', blank=True)),
                ('Field2', models.CharField(help_text='Custom merchant field 1', max_length=240, null=True, verbose_name='Field 2', blank=True)),
                ('Field3', models.CharField(help_text='Custom merchant field 1', max_length=240, null=True, verbose_name='Field 3', blank=True)),
                ('Field4', models.CharField(help_text='Custom merchant field 1', max_length=240, null=True, verbose_name='Field 4', blank=True)),
                ('Field5', models.CharField(help_text='Custom merchant field 1', max_length=240, null=True, verbose_name='Field 5', blank=True)),
                ('pay_from_email', models.EmailField(help_text='Email address of the customer who is making the payment. If provided, this field is hidden on the payment form. If left empty, the customer has to enter their email address', max_length=100, null=True, verbose_name='Pay from Email', blank=True)),
                ('firstname', models.CharField(help_text="Customer's first name.", max_length=20, null=True, verbose_name='First name', blank=True)),
                ('lastname', models.CharField(help_text="Customer's last name.", max_length=50, null=True, verbose_name='Last name', blank=True)),
                ('date_of_birth', models.DateField(help_text='Date of birth of the customer. The format is ddmmyyyy. Only numeric values are accepted. If provided this field will be pre-filled in the Payment form. This saves time for SEPA payments and Skrill Wallet sign-up which require the customer to enter a date of birth', max_length=8, null=True, verbose_name='Date of birth', blank=True)),
                ('address', models.CharField(help_text="Customer's address.", max_length=100, null=True, verbose_name='Address', blank=True)),
                ('address2', models.CharField(help_text="Customer's address.", max_length=100, null=True, verbose_name='Address2', blank=True)),
                ('phone_number', models.PositiveIntegerField(help_text="Customer's phone number. Only numeric values are accepted.", null=True, verbose_name='Phone number', blank=True)),
                ('postal_code', models.CharField(help_text="Customer's postal code/ZIP Code. Only alphanumeric values are accepted (no punctuation marks etc.)", max_length=9, null=True, verbose_name='Postal code', blank=True)),
                ('city', models.CharField(help_text="Customer's city.", max_length=50, null=True, verbose_name='City', blank=True)),
                ('state', models.CharField(help_text="Customer's state or region.", max_length=50, null=True, verbose_name='State', blank=True)),
                ('country', models.CharField(choices=[(b'AFG', b'Afghanistan'), (b'ALA', b'\xc3\x85land Islands'), (b'ALB', b'Albania'), (b'DZA', b'Algeria'), (b'ASM', b'American Samoa'), (b'AND', b'Andorra'), (b'AGO', b'Angola'), (b'AIA', b'Anguilla'), (b'ATA', b'Antarctica'), (b'ATG', b'Antigua and Barbuda'), (b'ARG', b'Argentina'), (b'ARM', b'Armenia'), (b'ABW', b'Aruba'), (b'AUS', b'Australia'), (b'AUT', b'Austria'), (b'AZE', b'Azerbaijan'), (b'BHS', b'Bahamas, The'), (b'BHR', b'Bahrain'), (b'BGD', b'Bangladesh'), (b'BRB', b'Barbados'), (b'BLR', b'Belarus'), (b'BEL', b'Belgium'), (b'BLZ', b'Belize'), (b'BEN', b'Benin'), (b'BMU', b'Bermuda'), (b'BTN', b'Bhutan'), (b'BOL', b'Bolivia'), (b'BIH', b'Bosnia and Herzegovina'), (b'BWA', b'Botswana'), (b'BVT', b'Bouvet Island'), (b'BRA', b'Brazil'), (b'IOT', b'British Indian Ocean Territory'), (b'VGB', b'British Virgin Islands'), (b'BRN', b'Brunei'), (b'BGR', b'Bulgaria'), (b'BFA', b'Burkina Faso'), (b'MMR', b'Burma'), (b'BDI', b'Burundi'), (b'KHM', b'Cambodia'), (b'CMR', b'Cameroon'), (b'CAN', b'Canada'), (b'CPV', b'Cape Verde'), (b'CYM', b'Cayman Islands'), (b'CAF', b'Central African Republic'), (b'TCD', b'Chad'), (b'CHL', b'Chile'), (b'CHN', b'China'), (b'CXR', b'Christmas Island'), (b'CCK', b'Cocos (Keeling) Islands'), (b'COL', b'Colombia'), (b'COM', b'Comoros'), (b'COD', b'Congo, Democratic Republic of the'), (b'COG', b'Congo, Republic of the'), (b'COK', b'Cook Islands'), (b'CRI', b'Costa Rica'), (b'CIV', b"Cote d'Ivoire"), (b'HRV', b'Croatia'), (b'CUB', b'Cuba'), (b'CYP', b'Cyprus'), (b'CZE', b'Czech Republic'), (b'DNK', b'Denmark'), (b'DJI', b'Djibouti'), (b'DMA', b'Dominica'), (b'DOM', b'Dominican Republic'), (b'ECU', b'Ecuador'), (b'EGY', b'Egypt'), (b'SLV', b'El Salvador'), (b'GNQ', b'Equatorial Guinea'), (b'ERI', b'Eritrea'), (b'EST', b'Estonia'), (b'ETH', b'Ethiopia'), (b'FLK', b'Falkland Islands (Islas Malvinas)'), (b'FRO', b'Faroe Islands'), (b'FJI', b'Fiji'), (b'FIN', b'Finland'), (b'FRA', b'France'), (b'GUF', b'French Guiana'), (b'PYF', b'French Polynesia'), (b'ATF', b'French Southern and Antarctic Lands'), (b'GAB', b'Gabon'), (b'GMB', b'Gambia, The'), (b'PSE', b'Gaza Strip'), (b'GEO', b'Georgia'), (b'DEU', b'Germany'), (b'GHA', b'Ghana'), (b'GIB', b'Gibraltar'), (b'GRC', b'Greece'), (b'GRL', b'Greenland'), (b'GRD', b'Grenada'), (b'GLP', b'Guadeloupe'), (b'GUM', b'Guam'), (b'GTM', b'Guatemala'), (b'GGY', b'Guernsey'), (b'GIN', b'Guinea'), (b'GNB', b'GuineaBissau'), (b'GUY', b'Guyana'), (b'HTI', b'Haiti'), (b'HMD', b'Heard Island and McDonald Islands'), (b'VAT', b'Holy See (Vatican City)'), (b'HND', b'Honduras'), (b'HKG', b'Hong Kong'), (b'HUN', b'Hungary'), (b'ISL', b'Iceland'), (b'IND', b'India'), (b'IDN', b'Indonesia'), (b'IRN', b'Iran'), (b'IRQ', b'Iraq'), (b'IRL', b'Ireland'), (b'IMN', b'Isle of Man'), (b'ISR', b'Israel'), (b'ITA', b'Italy'), (b'JAM', b'Jamaica'), (b'JPN', b'Japan'), (b'JEY', b'Jersey'), (b'JOR', b'Jordan'), (b'KAZ', b'Kazakhstan'), (b'KEN', b'Kenya'), (b'KIR', b'Kiribati'), (b'PRK', b'Korea, North'), (b'KOR', b'Korea, South'), (b'KWT', b'Kuwait'), (b'KGZ', b'Kyrgyzstan'), (b'LAO', b'Laos'), (b'LVA', b'Latvia'), (b'LBN', b'Lebanon'), (b'LSO', b'Lesotho'), (b'LBR', b'Liberia'), (b'LBY', b'Libya'), (b'LIE', b'Liechtenstein'), (b'LTU', b'Lithuania'), (b'LUX', b'Luxembourg'), (b'MAC', b'Macau'), (b'MKD', b'Macedonia'), (b'MDG', b'Madagascar'), (b'MWI', b'Malawi'), (b'MYS', b'Malaysia'), (b'MDV', b'Maldives'), (b'MLI', b'Mali'), (b'MLT', b'Malta'), (b'MHL', b'Marshall Islands'), (b'MTQ', b'Martinique'), (b'MRT', b'Mauritania'), (b'MUS', b'Mauritius'), (b'MYT', b'Mayotte'), (b'MEX', b'Mexico'), (b'FSM', b'Micronesia, Federated States of'), (b'MDA', b'Moldova'), (b'MCO', b'Monaco'), (b'MNG', b'Mongolia'), (b'MNE', b'Montenegro'), (b'MSR', b'Montserrat'), (b'MAR', b'Morocco'), (b'MOZ', b'Mozambique'), (b'NAM', b'Namibia'), (b'NRU', b'Nauru'), (b'NPL', b'Nepal'), (b'NLD', b'Netherlands'), (b'ANT', b'Netherlands Antilles'), (b'NCL', b'New Caledonia'), (b'NZL', b'New Zealand'), (b'NIC', b'Nicaragua'), (b'NER', b'Niger'), (b'NGA', b'Nigeria'), (b'NIU', b'Niue'), (b'NFK', b'Norfolk Island'), (b'MNP', b'Northern Mariana Islands'), (b'NOR', b'Norway'), (b'OMN', b'Oman'), (b'PAK', b'Pakistan'), (b'PLW', b'Palau'), (b'PAN', b'Panama'), (b'PNG', b'Papua New Guinea'), (b'PRY', b'Paraguay'), (b'PER', b'Peru'), (b'PHL', b'Philippines'), (b'PCN', b'Pitcairn Islands'), (b'POL', b'Poland'), (b'PRT', b'Portugal'), (b'PRI', b'Puerto Rico'), (b'QAT', b'Qatar'), (b'REU', b'Reunion'), (b'ROU', b'Romania'), (b'RUS', b'Russia'), (b'RWA', b'Rwanda'), (b'BLM', b'Saint Barthelemy'), (b'SHN', b'Saint Helena'), (b'KNA', b'Saint Kitts and Nevis'), (b'LCA', b'Saint Lucia'), (b'MAF', b'Saint Martin'), (b'SPM', b'Saint Pierre and Miquelon'), (b'VCT', b'Saint Vincent and the Grenadines'), (b'WSM', b'Samoa'), (b'SMR', b'San Marino'), (b'STP', b'Sao Tome and Principe'), (b'SAU', b'Saudi Arabia'), (b'SEN', b'Senegal'), (b'SRB', b'Serbia'), (b'SYC', b'Seychelles'), (b'SLE', b'Sierra Leone'), (b'SGP', b'Singapore'), (b'SVK', b'Slovakia'), (b'SVN', b'Slovenia'), (b'SLB', b'Solomon Islands'), (b'SOM', b'Somalia'), (b'ZAF', b'South Africa'), (b'SGS', b'South Georgia and the South Sandwich Islands'), (b'ESP', b'Spain'), (b'LKA', b'Sri Lanka'), (b'SDN', b'Sudan'), (b'SUR', b'Suriname'), (b'SJM', b'Svalbard'), (b'SWZ', b'Swaziland'), (b'SWE', b'Sweden'), (b'CHE', b'Switzerland'), (b'SYR', b'Syria'), (b'TWN', b'Taiwan'), (b'TJK', b'Tajikistan'), (b'TZA', b'Tanzania'), (b'THA', b'Thailand'), (b'TLS', b'TimorLeste'), (b'TGO', b'Togo'), (b'TKL', b'Tokelau'), (b'TON', b'Tonga'), (b'TTO', b'Trinidad and Tobago'), (b'TUN', b'Tunisia'), (b'TUR', b'Turkey'), (b'TKM', b'Turkmenistan'), (b'TCA', b'Turks and Caicos Islands'), (b'TUV', b'Tuvalu'), (b'UGA', b'Uganda'), (b'UKR', b'Ukraine'), (b'ARE', b'United Arab Emirates'), (b'GBR', b'United Kingdom'), (b'USA', b'United States'), (b'UMI', b'United States Minor Outlying Islands'), (b'URY', b'Uruguay'), (b'UZB', b'Uzbekistan'), (b'VUT', b'Vanuatu'), (b'VEN', b'Venezuela'), (b'VNM', b'Vietnam'), (b'VIR', b'Virgin Islands'), (b'WLF', b'Wallis and Futuna'), (b'PSE', b'West Bank'), (b'ESH', b'Western Sahara'), (b'YEM', b'Yemen'), (b'ZMB', b'Zambia'), (b'ZWE', b'Zimbabwe')], max_length=3, blank=True, help_text="Customer's country in the 3-digit ISO Code.", null=True, verbose_name='Country')),
                ('neteller_account', models.CharField(default=None, max_length=150, null=True, help_text='Neteller customer account email or account ID', blank=True)),
                ('neteller_secure_id', models.PositiveIntegerField(default=None, help_text="Secure ID or Google Authenticator One Time Password for the customer's Neteller account", null=True, blank=True)),
                ('amount', models.DecimalField(help_text="The total amount payable. Note: Do not include the trailing zeroes if the amount is a natural number. For example: '23' (not '23.00')", verbose_name='Amount', max_digits=19, decimal_places=2)),
                ('currency', models.CharField(default=b'EUR', help_text='3-letter code of the currency of the amount according to ISO 4217', max_length=3, verbose_name='Currency', choices=[(b'EUR', b'Euro'), (b'TWD', b'Taiwan Dollar'), (b'USD', b'U.S. Dollar'), (b'THB', b'Thailand Baht'), (b'GBP', b'British Pound'), (b'CZK', b'Czech Koruna'), (b'HKD', b'Hong Kong Dollar'), (b'HUF', b'Hungarian Forint'), (b'SGD', b'Singapore Dollar'), (b'SKK', b'Slovakian Koruna'), (b'JPY', b'Japanese Yen'), (b'EEK', b'Estonian Kroon'), (b'CAD', b'Canadian Dollar'), (b'BGN', b'Bulgarian Leva'), (b'AUD', b'Australian Dollar'), (b'PLN', b'Polish Zloty'), (b'CHF', b'Swiss Franc'), (b'ISK', b'Iceland Krona'), (b'DKK', b'Danish Krone'), (b'INR', b'Indian Rupee'), (b'SEK', b'Swedish Krona'), (b'LVL', b'Latvian Lat'), (b'NOK', b'Norwegian Krone'), (b'KRW', b'South-Korean Won'), (b'ILS', b'Israeli Shekel'), (b'ZAR', b'South-African Rand'), (b'MYR', b'Malaysian Ringgit'), (b'RON', b'Romanian Leu New'), (b'NZD', b'New Zealand Dollar'), (b'HRK', b'Croatian Kuna'), (b'TRY', b'New Turkish Lira'), (b'LTL', b'Lithuanian Litas'), (b'AED', b'Utd. Arab Emir. Dirham'), (b'JOD', b'Jordanian Dinar'), (b'MAD', b'Moroccan Dirham'), (b'OMR', b'Omani Rial'), (b'QAR', b'Qatari Rial'), (b'RSD', b'Serbian dinar'), (b'SAR', b'Saudi Riyal'), (b'TND', b'Tunisian Dinar')])),
                ('amount2_description', models.CharField(help_text="Merchant may specify a detailed calculation for the total amount payable. Please note that Skrill (Moneybookers) does not check the validity of these data - they are only displayed in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Amount 2 description', blank=True)),
                ('amount2', models.DecimalField(decimal_places=2, max_digits=19, blank=True, help_text="This amount in the currency defined in field 'currency' will be shown next to amount2_description.", null=True, verbose_name='Amount 2')),
                ('amount3_description', models.CharField(help_text="Merchant may specify a detailed calculation for the total amount payable. Please note that Skrill (Moneybookers) does not check the validity of these data - they are only displayed in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Amount 3 description', blank=True)),
                ('amount3', models.DecimalField(decimal_places=2, max_digits=19, blank=True, help_text="This amount in the currency defined in field 'currency' will be shown next to amount3_description.", null=True, verbose_name='Amount 3')),
                ('amount4_description', models.CharField(help_text="Merchant may specify a detailed calculation for the total amount payable. Please note that Skrill (Moneybookers) does not check the validity of these data - they are only displayed in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Amount 4 description', blank=True)),
                ('amount4', models.DecimalField(decimal_places=2, max_digits=19, blank=True, help_text="This amount in the currency defined in field 'currency' will be shown next to amount4_description.", null=True, verbose_name='Amount 4')),
                ('detail1_description', models.CharField(help_text="Merchant may show up to 5 details about the product or transfer in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Detail 1 description', blank=True)),
                ('detail1_text', models.CharField(help_text='The detail1_text is shown next to the detail1_description in the More Information section in the header of the payment form with the other payment details. The detail1_description combined with the detail1_text is shown in the more information field of the merchant account history CSV file. Using the example values, this would be Product ID: 4509334. Note: If a customer makes a purchase using Skrill Wallet this information will also appear in the same field in their account history', max_length=240, null=True, verbose_name='Detail 1 text', blank=True)),
                ('detail2_description', models.CharField(help_text="Merchant may show up to 5 details about the product or transfer in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Detail 2 description', blank=True)),
                ('detail2_text', models.CharField(help_text="The detail2_text is shown next to the detail2_description. The detail1_text is also shown to the client in his history at Skrill (Moneybookers)' website.", max_length=240, null=True, verbose_name='Detail 2 text', blank=True)),
                ('detail3_description', models.CharField(help_text="Merchant may show up to 5 details about the product or transfer in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Detail 3 description', blank=True)),
                ('detail3_text', models.CharField(help_text="The detail3_text is shown next to the detail3_description. The detail3_text is also shown to the client in his history at Skrill (Moneybookers)' website.", max_length=240, null=True, verbose_name='Detail 3 text', blank=True)),
                ('detail4_description', models.CharField(help_text="Merchant may show up to 5 details about the product or transfer in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Detail 4 description', blank=True)),
                ('detail4_text', models.CharField(help_text="The detail4_text is shown next to the detail4_description. The detail4_text is also shown to the client in his history at Skrill (Moneybookers)' website.", max_length=240, null=True, verbose_name='Detail 4 text', blank=True)),
                ('detail5_description', models.CharField(help_text="Merchant may show up to 5 details about the product or transfer in the 'More information' section in the header of the gateway.", max_length=240, null=True, verbose_name='Detail 5 description', blank=True)),
                ('detail5_text', models.CharField(help_text="The detail5_text is shown next to the detail5_description. The detail5_text is also shown to the client in his history at Skrill (Moneybookers)' website.", max_length=240, null=True, verbose_name='Detail 5 text', blank=True)),
                ('payment_methods', multiselectfield.db.fields.MultiSelectField(choices=[(b'WLT', b'Skrill Digital Wallet'), (b'NTL', b'Neteller'), (b'PSC', b'Paysafecard'), (b'PCH', b'Paysafecash'), (b'RSB', b'Resurs'), (b'ACC', b'All Card Types'), (b'VSA', b'Visa'), (b'MSC', b'MasterCard'), (b'VSE', b'Visa Electron'), (b'MAE', b'Maestro'), (b'AMX', b'American Express'), (b'DIN', b'Diners'), (b'JCB', b'JCB'), (b'GCB', b'Carte Bleue'), (b'DNK', b'Dankort'), (b'PSP', b'PostePay'), (b'CSI', b'CartaSi'), (b'OBT/NGP', b'Online Bank Transfer'), (b'GIR', b'Giropay'), (b'DID', b'Direct Debit / ELV'), (b'SFT', b'Sofortueberweisung'), (b'EBT', b'Nordea Solo'), (b'IDL/GCI', b'iDEAL'), (b'NPY', b'EPS (Netpay)'), (b'PLI', b'POLi'), (b'PWY', b'All Polish Banks'), (b'EPY', b'ePay.gb'), (b'GLU', b'Trustly'), (b'ALI', b'Alipay'), (b'ADB', b'Astropay - Online bank transfer (Direct Bank Transfer)'), (b'AOB', b'Astropay - Offline bank transfer'), (b'ACI', b'Astropay - Cash (Invoice)'), (b'AUP', b'Unionpay (via Astropay)')], max_length=100, blank=True, help_text="Different effect depending on your skrill merchant account (fixed or flexible). Flexible: only a single code is used. Fixed: one or more payment method codes separated by commas. If no value, all payment methods available in the customer's country", null=True, verbose_name='Payment methods')),
                ('user', models.ForeignKey(verbose_name='User', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
                'verbose_name': 'Payment request',
                'verbose_name_plural': 'Payment requests',
            },
        ),
        migrations.CreateModel(
            name='StatusReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('valid', models.BooleanField(default=False, verbose_name='Valid')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('pay_to_email', models.EmailField(default=b'dimgeows@yahoo.com', help_text="Email address of the Merchant's moneybookers.com account.", max_length=50, verbose_name='Merchant Email')),
                ('pay_from_email', models.EmailField(help_text='Email address of the customer who is making the payment, i.e. sending the money.', max_length=50, verbose_name='Customer Email')),
                ('merchant_id', models.BigIntegerField(help_text="Unique ID for the Merchant's moneybookers.com account.", verbose_name='Merchant ID')),
                ('customer_id', models.BigIntegerField(help_text="Unique ID for the customer's moneybookers.com account.", null=True, verbose_name='Customer ID', blank=True)),
                ('mb_transaction_id', models.BigIntegerField(help_text="Moneybookers' unique transaction ID for the transfer.", verbose_name='Skrill transaction ID')),
                ('mb_amount', models.DecimalField(help_text="The total amount of the payment in Merchant's currency.", verbose_name='MB Amount', max_digits=19, decimal_places=2)),
                ('mb_currency', models.CharField(help_text="Currency of mb_amount. Will always be the same as the currency of the beneficiary's account at Skrill (Moneybookers).", max_length=3, verbose_name='MB Currency', choices=[(b'EUR', b'Euro'), (b'TWD', b'Taiwan Dollar'), (b'USD', b'U.S. Dollar'), (b'THB', b'Thailand Baht'), (b'GBP', b'British Pound'), (b'CZK', b'Czech Koruna'), (b'HKD', b'Hong Kong Dollar'), (b'HUF', b'Hungarian Forint'), (b'SGD', b'Singapore Dollar'), (b'SKK', b'Slovakian Koruna'), (b'JPY', b'Japanese Yen'), (b'EEK', b'Estonian Kroon'), (b'CAD', b'Canadian Dollar'), (b'BGN', b'Bulgarian Leva'), (b'AUD', b'Australian Dollar'), (b'PLN', b'Polish Zloty'), (b'CHF', b'Swiss Franc'), (b'ISK', b'Iceland Krona'), (b'DKK', b'Danish Krone'), (b'INR', b'Indian Rupee'), (b'SEK', b'Swedish Krona'), (b'LVL', b'Latvian Lat'), (b'NOK', b'Norwegian Krone'), (b'KRW', b'South-Korean Won'), (b'ILS', b'Israeli Shekel'), (b'ZAR', b'South-African Rand'), (b'MYR', b'Malaysian Ringgit'), (b'RON', b'Romanian Leu New'), (b'NZD', b'New Zealand Dollar'), (b'HRK', b'Croatian Kuna'), (b'TRY', b'New Turkish Lira'), (b'LTL', b'Lithuanian Litas'), (b'AED', b'Utd. Arab Emir. Dirham'), (b'JOD', b'Jordanian Dinar'), (b'MAD', b'Moroccan Dirham'), (b'OMR', b'Omani Rial'), (b'QAR', b'Qatari Rial'), (b'RSD', b'Serbian dinar'), (b'SAR', b'Saudi Riyal'), (b'TND', b'Tunisian Dinar')])),
                ('status', models.IntegerField(help_text='Status of the transaction.', verbose_name='Status', choices=[(-3, b'Chargeback'), (-2, b'Failed'), (-1, b'Cancelled'), (0, b'Pending'), (2, b'Processed')])),
                ('failed_reason_code', models.CharField(choices=[(b'01', b'01 - Referred by Card Issuer'), (b'02', b'02 - Invalid Merchant. Merchant account inactive'), (b'03', b'03 - Pick-up card'), (b'04', b'04 - Declined by Card Issuer'), (b'05', b'05 - Insufficient funds'), (b'06', b'06 - Merchant/NETELLER/Processor declined '), (b'07', b'07 - Incorrect PIN'), (b'08', b'08 - PIN tries exceed - card blocked'), (b'09', b'09 - Invalid Transaction'), (b'10', b'10 - Transaction frequency limit exceeded'), (b'11', b'11 - Invalid Amount format. Amount too high. Amount too low. Limit Exceeded'), (b'12', b'12 - Invalid credit card or bank account'), (b'13', b'13 - Invalid Card Issuer'), (b'15', b'15 - Duplicate transaction reference'), (b'19', b'19 - Authentication credentials expired/disabled/locked/invalid. Cannot authenticate. Request not authorized'), (b'20', b'20 - Neteller member is in a blocked country/state/region/geolocatio'), (b'22', b'22 - Unsupported Accept header or Content-Type'), (b'24', b'24 - Card expired'), (b'27', b'27 - Requested API function not supported (legacy function) '), (b'28', b'28 - Lost/Stolen card'), (b'30', b'30 - Format Failure'), (b'32', b'32 - Card Security Code (CVV2/CVC2) Check Failed '), (b'34', b'34 - Illegal Transaction'), (b'35', b'35 - Member/Merchant not entitled/authorized. Account closed. Unauthorized access. '), (b'37', b'37 - Card restricted by Card Issuer '), (b'38', b'38 - Security violation'), (b'42', b'42 - Card blocked by Card Issuer'), (b'44', b'44 - Card Issuing Bank or Network is not available'), (b'45', b'45 - Processing error - card type is not processed by the authorization centre'), (b'51', b'51 - System Error'), (b'58', b'58 - Transaction not permitted by acquirer'), (b'63', b'63 - Transaction not allowed for cardholder'), (b'64', b'64 - Invalid accountId/country/currency/customer/email/field/merchant reference / merchant account currency / term length / verification code. Account not found/ disabled. Entity not found. URI not found. Existing member email. Plan already exists. Bad request.'), (b'67', b'67 - BitPay session expired'), (b'68', b'68 - Referenced transaction has not been settled '), (b'69', b'69 - Referenced transaction is not fully authenticated'), (b'70', b'70 - Customer failed 3DS verification '), (b'80', b'80 - Fraud rules declined'), (b'98', b'98 - Error in communication with provider'), (b'99', b'99 - Other')], max_length=2, blank=True, help_text='If the transaction is with status -2 (failed), this field will contain a code detailing the reason for the failure.', null=True, verbose_name='Failed reason code')),
                ('md5sig', models.CharField(max_length=32, verbose_name='MD5 signature')),
                ('sha2sig', models.CharField(max_length=64, null=True, verbose_name='SHA2 signature', blank=True)),
                ('amount', models.DecimalField(help_text='Amount of the payment as posted by the Merchant on the entry form.', verbose_name='Amount', max_digits=18, decimal_places=2)),
                ('currency', models.CharField(help_text='Currency of the payment as posted by the Merchant on the entry form', max_length=3, verbose_name='Currency', choices=[(b'EUR', b'Euro'), (b'TWD', b'Taiwan Dollar'), (b'USD', b'U.S. Dollar'), (b'THB', b'Thailand Baht'), (b'GBP', b'British Pound'), (b'CZK', b'Czech Koruna'), (b'HKD', b'Hong Kong Dollar'), (b'HUF', b'Hungarian Forint'), (b'SGD', b'Singapore Dollar'), (b'SKK', b'Slovakian Koruna'), (b'JPY', b'Japanese Yen'), (b'EEK', b'Estonian Kroon'), (b'CAD', b'Canadian Dollar'), (b'BGN', b'Bulgarian Leva'), (b'AUD', b'Australian Dollar'), (b'PLN', b'Polish Zloty'), (b'CHF', b'Swiss Franc'), (b'ISK', b'Iceland Krona'), (b'DKK', b'Danish Krone'), (b'INR', b'Indian Rupee'), (b'SEK', b'Swedish Krona'), (b'LVL', b'Latvian Lat'), (b'NOK', b'Norwegian Krone'), (b'KRW', b'South-Korean Won'), (b'ILS', b'Israeli Shekel'), (b'ZAR', b'South-African Rand'), (b'MYR', b'Malaysian Ringgit'), (b'RON', b'Romanian Leu New'), (b'NZD', b'New Zealand Dollar'), (b'HRK', b'Croatian Kuna'), (b'TRY', b'New Turkish Lira'), (b'LTL', b'Lithuanian Litas'), (b'AED', b'Utd. Arab Emir. Dirham'), (b'JOD', b'Jordanian Dinar'), (b'MAD', b'Moroccan Dirham'), (b'OMR', b'Omani Rial'), (b'QAR', b'Qatari Rial'), (b'RSD', b'Serbian dinar'), (b'SAR', b'Saudi Riyal'), (b'TND', b'Tunisian Dinar')])),
                ('neteller_id', models.CharField(default=None, max_length=150, null=True, help_text="If the Neteller payment method is used this parameter contains the Neteller customer's account id or email depending on the details entered by the Neteller customer or the value supplied in the neteller_account parameter.", blank=True)),
                ('payment_type', models.CharField(help_text='The payment method the customer used. Contact merchant services to enable this option. You can choose to receive either consolidated values or detailed values', max_length=10, null=True, verbose_name='Payment type', blank=True)),
                ('merchant_fields', models.CharField(default=None, max_length=500, blank=True, help_text='If you submitted a list of values in the merchant_fields parameter, they will be passed back with the status report. Example: field1=value1', null=True, verbose_name='Merchant Fields')),
                ('payment_request', models.ForeignKey(help_text='PaymentRequest object directly mapped via incoming transaction_id', to='skrill.PaymentRequest')),
            ],
            options={
                'ordering': ['created_at'],
                'verbose_name': 'Status report',
                'verbose_name_plural': 'Status reports',
            },
        ),
        migrations.AlterUniqueTogether(
            name='statusreport',
            unique_together=set([('valid', 'status', 'mb_transaction_id')]),
        ),
    ]
