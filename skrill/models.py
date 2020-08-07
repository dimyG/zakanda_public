# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib
import requests
import logging
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from multiselectfield import MultiSelectField
import decimal
from skrill.settings import *
from lxml import etree


logger = logging.getLogger(__name__)


class TransferPrepareException(Exception):
    pass


class TransferExecuteException(Exception):
    pass


class NoDataException(Exception):
    pass


class PaymentRequest(models.Model):
    # skrill will repost 10 times to the status_url until it gets a 200 response. This reposting process
    # takes a few minutes so that a temporary network error can be avoided.

    # list of custom fields that will be ignored upon submit
    SUBMIT_IGNORE_FIELDS = ['user', 'user_id', 'test', 'submitted', 'created_at', 'updated_at', 'statusreport',
                            'status_response_received']

    merchant_field_choices = (
        ('Field1', 'Field1'),
        ('Field2', 'Field2'),
        ('Field3', 'Field3'),
        ('Field4', 'Field4'),
        ('Field5', 'Field5'),
    )

    # custom stuff
    user = models.ForeignKey(User, verbose_name="User", related_name='payment_requests')
    test = models.BooleanField("Is test", default=False)
    submitted = models.BooleanField("Is submitted", default=False, editable=False,
                                    help_text="If Skrill has created a session id for a specific payment request, the"
                                              "payment request is marked as submitted in the database. It has been"
                                              "submitted to Skrill and a session id has been created for it.")
    status_response_received = models.BooleanField("Is a status response received", default=False,
                                                   help_text="If True then a call to get the status report for this transaction "
                                                    "has been made and a status response has been returned. "
                                                    "The response can be either a normal status report response with "
                                                    "a status value, or a 'transaction doesn't exist' response. These "
                                                    "transactions that don't exist in Skrill are "
                                                    "the transactions that we want to be able to identify. These "
                                                    "transactions would have no associated status report since Skrill "
                                                    "doesn't support a status value for these transactions and "
                                                             "their status_response_received flag will be True."
                                                    "These are paymentRequests that are never executed. For example "
                                                    "the user presses the deposit button, the payment request is "
                                                    "submitted, a session id is created for it by Skrill, but the "
                                                    "user doesn't complete the payment. If you ask for a status report "
                                                    "for such a payment request you will get a 'doesn't exist' "
                                                    "response. "
                                                             "Since their value will be True will can separate them"
                                                     "from transaction that don;t have an associated status report "
                                                     "and their value is False. For these transactions the status must be asked")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Merchant details
    transaction_id = models.AutoField("Transaction ID", primary_key=True,
                                      help_text="Reference or identification number provided by the Merchant. "
                                                "MUST be unique for each payment")
    pay_to_email = models.EmailField("Merchant Email", max_length=50, default=PAY_TO_EMAIL,
                                     help_text="Email address of the Merchant's moneybookers.com account.")
    recipient_description = models.CharField("Merchant description", max_length=30, blank=True, null=True,
                                             default=RECIPIENT_DESCRIPTION,
                                             help_text=" A description to be shown on the Skrill payment page in the "
                                                       "logo area if there is no logo_url parameter. If no value is "
                                                       "submitted and there is no logo, the pay_to_email value is "
                                                       "shown as the recipient of the payment. ")
    return_url = models.URLField("Return URL", max_length=240, blank=True, null=True, default=None,
                                 help_text="URL to which the customer will be returned when the payment is made. "
                                           "If this field is not filled, the gateway window will simply close "
                                           "automatically at the end of the transaction, so that the customer will be "
                                           "returned to the page on your website from where they were redirected "
                                           "to Skrill. A secure return URL option is available.")
    return_url_text = models.CharField("Return URL text", max_length=35, blank=True, null=True, default=RETURN_URL_TEXT,
                                       help_text="The text on the button when the user finishes his payment.")
    return_url_target = models.SmallIntegerField("Return URL target", choices=URL_TARGET_CHOICES, default=DEFAULT_URL_TARGET,
                                                 help_text="Specifies a target in which the return_url value will be "
                                                           "called upon successful payment from customer.")
    cancel_url = models.URLField("Cancel URL", max_length=240, blank=True, null=True, default=None,
                                 help_text="URL to which the customer is returned if the payment is cancelled or fails."
                                           " If no cancel URL is provided the Cancel button is not displayed")
    cancel_url_target = models.SmallIntegerField("Cancel URL target", choices=URL_TARGET_CHOICES,
                                                 default=DEFAULT_URL_TARGET,
                                                 help_text="Specifies a target in which the cancel_url value will be "
                                                           "called upon cancellation of payment from customer.")
    # It is important that the default value is None (not the lazy evaluated object) because if you are at Dev
    # environment the evaluated url is a local one but it is added in the migration files as a default value
    # and will be applied to the production when the migrations are applied there. So the default value is None
    # and the value of the STATUS_URL setting is used explicitly when the the payment request is submitted
    # to Skrill.
    status_url = models.CharField("Status URL", max_length=400, blank=True, null=True, default=None,
                                  help_text="URL to which the transaction details will be posted after the payment "
                                            "process is complete. Alternatively, you may specify an email address "
                                            "to which you would like to receive the results.")
    status_url2 = models.CharField("Status URL 2", max_length=400, blank=True, null=True, default=None,
                                   help_text="Second URL to which the transaction details will be posted after the "
                                             "payment process is complete. Alternatively, you may specify an email "
                                             "address to which you would like to receive the results.")
    # new_window_redirect = models.BooleanField("New window redirect", default=NEW_WINDOW_REDIRECT,
    #                                           help_text="Merchants can choose to redirect customers to the "
    #                                                     "Sofortueberweisung payment method in a new window instead of "
    #                                                     "in the same window.")
    language = models.CharField("Language", max_length=2, choices=LANGUAGE_CHOICES, default=LANGUAGE,
                                help_text="2-letter code of the language used for Skrill (Moneybookers)' pages.")
    # hide_login = models.BooleanField("Hide login", default=False,
    #                                  help_text="Merchants can show their customers the gateway page without "
    #                                            "the prominent login section.")
    # confirmation_note = models.CharField("Confirmation note", max_length=240, blank=True, null=True,
    #                                      default=CONFIRMATION_NOTE,
    #                                      help_text="Merchant may show to the customer on the confirmation screen - the "
    #                                                "end step of the process - a note, confirmation number, PIN or any "
    #                                                "other message. Line breaks <br> may be used for longer messages.")
    logo_url = models.URLField("Logo URL", max_length=240, blank=True, null=True, default=None,
                               help_text="The URL of the logo which you would like to appear at the top of the gateway. "
                                         "The logo must be accessible via HTTPS otherwise it will not be shown. "
                                         "For best integration results we recommend that Merchants use logos with "
                                         "dimensions up to 200px in width and 50px in height.")
    prepare_only = models.BooleanField("Prepare only", default=True,
                                       help_text="Forces only the SID to be returned without the actual page. "
                                                 "Useful when using the secure method to redirect the customer "
                                                 "to Quick Checkout.")
    dynamic_descriptor = models.CharField(max_length=50, blank=True, null=True, default=None,
                                          help_text="When a customer pays through Skrill, Skrill submits a "
                                                    "preconfigured descriptor with the transaction, containing your "
                                                    "business trading name/ brand name. The descriptor is typically "
                                                    "displayed on the bank or credit card statement of the customer. "
                                                    "For Klarna and Direct Debit payment methods, you can submit a "
                                                    "dynamic_descriptor, which will override the default value "
                                                    "stored by Skrill.")
    sid = models.CharField(blank=True, null=True, default=None, max_length=32,
                           help_text="This is an optional parameter containing the Session ID returned by the "
                                     "prepare_only call. If you use this parameter you should not supply any "
                                     "other parameters.")
    rid = models.CharField("Referral ID", max_length=100, blank=True, null=True,
                           help_text="Merchants can pass the unique referral ID or email of the affiliate from which "
                                     "the customer is referred. The rid value must be included within the "
                                     "actual payment request.")
    ext_ref_id = models.CharField("Extra Referral ID", max_length=100, blank=True, null=True,
                                  help_text="Merchants can pass additional identifier in this field in order to track "
                                            "affiliates. You MUST inform your account manager about the exact value "
                                            "that will be submitted so that affiliates can be tracked.")
    # merchant_fields = MultiSelectField("Merchant Fields", max_length=240, choices=merchant_field_choices, blank=True,
    #                                    help_text="A comma-separated list of field names that are passed back to "
    #                                              "your web server when the payment is confirmed (maximum 5 fields).")
    Field1 = models.CharField("Field 1", max_length=240, blank=True, null=True, help_text="Custom merchant field 1")
    Field2 = models.CharField("Field 2", max_length=240, blank=True, null=True, help_text="Custom merchant field 1")
    Field3 = models.CharField("Field 3", max_length=240, blank=True, null=True, help_text="Custom merchant field 1")
    Field4 = models.CharField("Field 4", max_length=240, blank=True, null=True, help_text="Custom merchant field 1")
    Field5 = models.CharField("Field 5", max_length=240, blank=True, null=True, help_text="Custom merchant field 1")

    # customer details (used to speed up Registration or Payment)
    pay_from_email = models.EmailField("Pay from Email", max_length=100, blank=True, null=True,
                                       help_text="Email address of the customer who is making the payment. If "
                                                 "provided, this field is hidden on the payment form. If left empty, "
                                                 "the customer has to enter their email address")
    # title = models.CharField("Title", max_length=3, choices=TITLE_CHOICES, blank=True, null=True, help_text="Customer's title.")
    firstname = models.CharField("First name", max_length=20, blank=True, null=True,  help_text="Customer's first name.")
    lastname = models.CharField("Last name", max_length=50, blank=True, null=True, help_text="Customer's last name.")
    date_of_birth = models.DateField("Date of birth", blank=True, null=True, max_length=8,
                                     help_text="Date of birth of the customer. The format is ddmmyyyy. Only numeric "
                                               "values are accepted. If provided this field will be pre-filled in the "
                                               "Payment form. This saves time for SEPA payments and Skrill Wallet "
                                               "sign-up which require the customer to enter a date of birth")
    address = models.CharField("Address", max_length=100, blank=True, null=True, help_text="Customer's address.")
    address2 = models.CharField("Address2", max_length=100, blank=True, null=True, help_text="Customer's address.")
    phone_number = models.PositiveIntegerField("Phone number", blank=True, null=True,
                                               help_text="Customer's phone number. Only numeric values are accepted.")
    postal_code = models.CharField("Postal code", max_length=9, blank=True, null=True,
                                   help_text="Customer's postal code/ZIP Code. Only alphanumeric values are accepted "
                                             "(no punctuation marks etc.)")
    city = models.CharField("City", max_length=50, blank=True, null=True, help_text="Customer's city.")
    state = models.CharField("State", max_length=50, blank=True, null=True, help_text="Customer's state or region.")
    country = models.CharField("Country", max_length=3, choices=ISO3166_A3, blank=True, null=True,
                               help_text="Customer's country in the 3-digit ISO Code.")
    neteller_account = models.CharField(max_length=150, blank=True, null=True, default=None,
                                        help_text="Neteller customer account email or account ID")
    neteller_secure_id = models.PositiveIntegerField(blank=True, null=True, default=None,
                                                     help_text="Secure ID or Google Authenticator One Time Password "
                                                               "for the customer's Neteller account")

    # payment details
    amount = models.DecimalField("Amount", max_digits=19, decimal_places=2,
                                 help_text="The total amount payable. Note: Do not include the trailing zeroes if "
                                           "the amount is a natural number. For example: '23' (not '23.00')")
    currency = models.CharField("Currency", max_length=3, choices=ISO4217, default=DEFAULT_CURRENCY,
                                help_text="3-letter code of the currency of the amount according to ISO 4217")
    amount2_description = models.CharField("Amount 2 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may specify a detailed calculation for the total amount "
                                                     "payable. Please note that Skrill (Moneybookers) does not check "
                                                     "the validity of these data - they are only displayed in the "
                                                     "'More information' section in the header of the gateway.")
    amount2 = models.DecimalField("Amount 2", max_digits=19, decimal_places=2, blank=True, null=True,
                                  help_text="This amount in the currency defined in field 'currency' will be shown "
                                            "next to amount2_description.")
    amount3_description = models.CharField("Amount 3 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may specify a detailed calculation for the total amount "
                                                     "payable. Please note that Skrill (Moneybookers) does not check "
                                                     "the validity of these data - they are only displayed in the "
                                                     "'More information' section in the header of the gateway.")
    amount3 = models.DecimalField("Amount 3", max_digits=19, decimal_places=2, blank=True, null=True,
                                  help_text="This amount in the currency defined in field 'currency' will be "
                                            "shown next to amount3_description.")
    amount4_description = models.CharField("Amount 4 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may specify a detailed calculation for the total "
                                                     "amount payable. Please note that Skrill (Moneybookers) does not "
                                                     "check the validity of these data - they are only displayed in "
                                                     "the 'More information' section in the header of the gateway.")
    amount4 = models.DecimalField("Amount 4", max_digits=19, decimal_places=2, blank=True, null=True,
                                  help_text="This amount in the currency defined in field 'currency' will be "
                                            "shown next to amount4_description.")
    detail1_description = models.CharField("Detail 1 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may show up to 5 details about the product or transfer "
                                                     "in the 'More information' section in the header of the gateway.")
    detail1_text = models.CharField("Detail 1 text", max_length=240, blank=True, null=True,
                                    help_text="The detail1_text is shown next to the detail1_description in the More "
                                              "Information section in the header of the payment form with the other "
                                              "payment details. The detail1_description combined with the detail1_text "
                                              "is shown in the more information field of the merchant account history "
                                              "CSV file. Using the example values, this would be Product ID: 4509334. "
                                              "Note: If a customer makes a purchase using Skrill Wallet this "
                                              "information will also appear in the same field in their account history")
    detail2_description = models.CharField("Detail 2 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may show up to 5 details about the product or transfer "
                                                     "in the 'More information' section in the header of the gateway.")
    detail2_text = models.CharField("Detail 2 text", max_length=240, blank=True, null=True,
                                    help_text="The detail2_text is shown next to the detail2_description. The detail1_"
                                              "text is also shown to the client in his history at "
                                              "Skrill (Moneybookers)' website.")
    detail3_description = models.CharField("Detail 3 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may show up to 5 details about the product or transfer "
                                                     "in the 'More information' section in the header of the gateway.")
    detail3_text = models.CharField("Detail 3 text", max_length=240, blank=True, null=True,
                                    help_text="The detail3_text is shown next to the detail3_description. "
                                              "The detail3_text is also shown to the client in his history "
                                              "at Skrill (Moneybookers)' website.")
    detail4_description = models.CharField("Detail 4 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may show up to 5 details about the product or transfer "
                                                     "in the 'More information' section in the header of the gateway.")
    detail4_text = models.CharField("Detail 4 text", max_length=240, blank=True, null=True,
                                    help_text="The detail4_text is shown next to the detail4_description. "
                                              "The detail4_text is also shown to the client in his history at "
                                              "Skrill (Moneybookers)' website.")
    detail5_description = models.CharField("Detail 5 description", max_length=240, blank=True, null=True,
                                           help_text="Merchant may show up to 5 details about the product or transfer "
                                                     "in the 'More information' section in the header of the gateway.")
    detail5_text = models.CharField("Detail 5 text", max_length=240, blank=True, null=True,
                                    help_text="The detail5_text is shown next to the detail5_description. "
                                              "The detail5_text is also shown to the client in his history at "
                                              "Skrill (Moneybookers)' website.")

    # other features
    payment_methods = MultiSelectField("Payment methods", max_length=100, choices=GATEWAY_PAYMENT_CODES, blank=True,
                                       null=True,
                                       help_text="Different effect depending on your skrill merchant account "
                                                 "(fixed or flexible). Flexible: only a single code is used. "
                                                 "Fixed: one or more payment method codes separated by commas. "
                                                 "If no value, all payment methods available in the customer's country")

    class Meta:
        verbose_name = "Payment request"
        verbose_name_plural = "Payment requests"
        ordering = ['created_at']

    def __unicode__(self):
        return "#%s %s %s" % (self.transaction_id, self.user, self.created_at)

    @classmethod
    def _format_boolean(cls, value):
        if value:
            return 1
        else:
            return 0

    def _get_formatted_field_value(self, field):
        field_class = self._meta.get_field(field).__class__
        field_value = getattr(self, field)
        # if field == "payment_methods":
        #     return ",".join(field_value)
        if field_class == models.BooleanField:
            return self._format_boolean(field_value)
        elif field_class == models.DateField:
            return field_value.strftime("%d%m%Y")
        elif field_class == models.DecimalField:
            if field_value % 1 == 0:
                # Do not include the trailing zeroes if the amount is a natural number. "23" (not "23.00").
                return str(int(field_value))
            return str(field_value)
        # elif isinstance(field_value, unicode):
        #     logger.debug("unicode: %s", field_value)
        #     print ("utf8 encoded: ", field_value.encode('utf8'))
        #     logger.debug("utf8 encoded: %s", field_value.encode('utf8'))
        #     return field_value.encode('utf8')
        else:
            return field_value

    def _get_used_custom_fields_as_csv(self):
        used_custom_fields = []
        for i in range(1, 6):
            value = getattr(self, "Field%d" % i)
            if value is not None and value != '':
                used_custom_fields.append("Field%d" % i)

        if len(used_custom_fields) > 0:
            return ', '.join(used_custom_fields)
        else:
            return ''

    @classmethod
    def get_sid_from_response_headers(cls, response):
        set_cookie_headers = response.headers['Set-Cookie']
        logger.debug("set cookie header: %s", set_cookie_headers)
        if not set_cookie_headers:
            logger.error("Session id can't be extracted, no Set-Cookie header exist [%s]", set_cookie_headers)
            return
        cookies = set_cookie_headers.split(",")
        for cookie in cookies:
            directives = cookie.split(";")
            for directive in directives:
                key_value_pair = directive.split("=")
                if key_value_pair[0] == "SESSION_ID":
                    try:
                        session_id = key_value_pair[1]
                        logger.debug("session id: %s", session_id)
                        return session_id
                    except Exception as e:
                        logger.exception("Session id can't be extracted, [%s], %s", set_cookie_headers, e)

    def get_sid(self, response):
        """ The session id is in the body of the response and in the headers too. I get both values
        and return the session id only if they match (not necessary). """
        logger.debug("posted to url: %s", response.url)
        logger.debug("response: %s, %s", response.text, response.status_code)
        if not response.status_code == 200:
            logger.error("session id response status code is %s", response.status_code)
            return
        body_session_id = response.text

        # if len(body_session_id) > 32:
        #     # max length of session id is 32 (probably == 32 would be better but is it always 32?)
        #     return

        headers_session_id = self.get_sid_from_response_headers(response)
        if not body_session_id == headers_session_id:
            logger.error("session id from body and headers do not match: %s != %s", body_session_id, headers_session_id)
            return
        return body_session_id

    def submit(self, force_submit=False):
        """ Submit model content to skrill and return redirect url with session ID on success."""
        self.save()  # is this necessary?
        assert self.prepare_only is True, "Use this only with prepare_only = True"
        assert self.pk is not None, "Save PaymentRequest before submitting!"
        if not force_submit:
            assert self.submitted is False, "PaymentRequest already submitted!"
        self.submitted = True
        self.save()  # so that it is certain that a submitted payment request always exists in our database

        data = {}
        for field in self._meta.get_all_field_names():
            if field in self.SUBMIT_IGNORE_FIELDS:
                continue
            field_value = getattr(self, field)
            if field_value is not None and field_value != '':
                data[field] = self._get_formatted_field_value(field)

        used_custom_fields = self._get_used_custom_fields_as_csv()
        if used_custom_fields != '':
            data['merchant_fields'] = used_custom_fields

        # the urls use lazy evaluation in settings. They are sent as an object to skrill and that doesn't work.
        # They must be evaluated and sent as a string
        try:
            data['status_url'] = STATUS_URL[:]  # evaluate the url
        except TypeError:
            # if no url is defined in settings the default value is None and you get a TypeError.
            # In this case the value None is used.
            pass
        try:
            data['status_url2'] = STATUS_URL2[:]
        except TypeError:
            pass
        try:
            data['return_url'] = RETURN_URL[:]
        except TypeError:
            pass
        try:
            data['cancel_url'] = CANCEL_URL[:]
        except TypeError:
            pass
        logger.debug("posting data: %s to url: %s", data, QUICK_CHECKOUT_URL)
        response = requests.post(QUICK_CHECKOUT_URL, data)
        session_id = self.get_sid(response)
        if not session_id:
            logger.error("skrill session id for PaymentRequest %s wasn't extracted", self)
            return
        url = "{}?sid={}".format(QUICK_CHECKOUT_URL, session_id)
        return url

    def is_shady(self):
        if not self.statusreport_set.all() and not self.status_response_received:
            return True

    @classmethod
    def get_shady(cls):
        # get the payment requests that might have been completed but we didn't received a status report for
        # due to some error. The status_response_received field of these payment_requests is False
        # (and they have no associated status report). If a payment request has no associated status report
        # despite the fact that a status response has been received for it, then it is a payment request
        # that hasn't been executed and we can just ignore it.
        shady = cls.objects.filter(statusreport=None).filter(status_response_received=False)
        return shady

    def resolve_shady(self):
        # todo skrill API: ask for a repost of the status of the shady transactions (using the MerchantQueryInterface)
        return


class StatusReport(models.Model):
    # custom fields
    valid = models.BooleanField("Valid", default=False)
    # signal_sent = models.BooleanField("Signal sent", default=False)
    # times_received = models.PositiveIntegerField(default=1)  # update it with F expression
    payment_request = models.ForeignKey(
        PaymentRequest, help_text="PaymentRequest object directly mapped via incoming transaction_id")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Skrill fields
    pay_to_email = models.EmailField("Merchant Email", max_length=50, default=PAY_TO_EMAIL,
                                     help_text="Email address of the Merchant's moneybookers.com account.")
    pay_from_email = models.EmailField("Customer Email", max_length=50,
                                       help_text="Email address of the customer who is making the payment, i.e. "
                                                 "sending the money.")
    merchant_id = models.BigIntegerField("Merchant ID",
                                              help_text="Unique ID for the Merchant's moneybookers.com account.")
    customer_id = models.BigIntegerField("Customer ID", null=True, blank=True,
                                              help_text="Unique ID for the customer's moneybookers.com account.")
    # transaction_id = models.PositiveIntegerField("Transaction ID",
    #                                              help_text="A unique reference or identification number provided "
    #                                                        "by you in your HTML form.")
    # 2,399,071,734: an integer that big caused a problem with a normal Integer or PositiveInteger field
    mb_transaction_id = models.BigIntegerField("Skrill transaction ID",
                                                    help_text="Moneybookers' unique transaction ID for the transfer.")
    mb_amount = models.DecimalField("MB Amount", max_digits=19, decimal_places=2,
                                    help_text="The total amount of the payment in Merchant's currency.")
    mb_currency = models.CharField("MB Currency", max_length=3, choices=ISO4217,
                                   help_text="Currency of mb_amount. Will always be the same as the currency of the "
                                             "beneficiary's account at Skrill (Moneybookers).")
    status = models.IntegerField("Status", choices=STATUS_CHOICES,
                                 help_text="Status of the transaction.")
    failed_reason_code = models.CharField("Failed reason code", max_length=2, choices=FAILED_REASON_CODES, blank=True, null=True,
                                          help_text="If the transaction is with status -2 (failed), this field will "
                                                    "contain a code detailing the reason for the failure.")
    md5sig = models.CharField("MD5 signature", max_length=32)
    sha2sig = models.CharField("SHA2 signature", max_length=64, null=True, blank=True)
    amount = models.DecimalField("Amount", max_digits=18, decimal_places=2,
                                 help_text="Amount of the payment as posted by the Merchant on the entry form.")
    currency = models.CharField("Currency", max_length=3, choices=ISO4217,
                                help_text="Currency of the payment as posted by the Merchant on the entry form")
    neteller_id = models.CharField(max_length=150, blank=True, null=True, default=None,
                                   help_text="If the Neteller payment method is used this parameter contains the "
                                             "Neteller customer's account id or email depending on the details "
                                             "entered by the Neteller customer or the value supplied in the "
                                             "neteller_account parameter.")
    payment_type = models.CharField("Payment type", max_length=10, blank=True, null=True,
                                    help_text="The payment method the customer used. Contact merchant services "
                                              "to enable this option. You can choose to receive either consolidated "
                                              "values or detailed values")
    merchant_fields = models.CharField("Merchant Fields", blank=True, null=True, default=None, max_length=500,
                                       help_text="If you submitted a list of values in the merchant_fields parameter, "
                                                 "they will be passed back with the status report. "
                                                 "Example: field1=value1")
    field_1 = models.CharField("Field 1", max_length=240, blank=True, null=True, default=None, help_text="Custom merchant field 1")
    field_2 = models.CharField("Field 2", max_length=240, blank=True, null=True, default=None, help_text="Custom merchant field 1")
    field_3 = models.CharField("Field 3", max_length=240, blank=True, null=True, default=None, help_text="Custom merchant field 1")
    field_4 = models.CharField("Field 4", max_length=240, blank=True, null=True, default=None, help_text="Custom merchant field 1")
    field_5 = models.CharField("Field 5", max_length=240, blank=True, null=True, default=None, help_text="Custom merchant field 1")
    # custom_field_1 = models.CharField("Custom field 1", max_length=240, blank=True, null=True,
    #                                   help_text="One of 5 custom fields, see \"merchant_fields\" in documentation")
    # custom_field_2 = models.CharField("Custom field 2", max_length=240, blank=True, null=True,
    #                                   help_text="One of 5 custom fields, see \"merchant_fields\" in documentation")
    # custom_field_3 = models.CharField("Custom field 3", max_length=240, blank=True, null=True,
    #                                   help_text="One of 5 custom fields, see \"merchant_fields\" in documentation")
    # custom_field_4 = models.CharField("Custom field 4", max_length=240, blank=True, null=True,
    #                                   help_text="One of 5 custom fields, see \"merchant_fields\" in documentation")
    # custom_field_5 = models.CharField("Custom field 5", max_length=240, blank=True, null=True,
    #                                   help_text="One of 5 custom fields, see \"merchant_fields\" in documentation")

    class Meta:
        verbose_name = "Status report"
        verbose_name_plural = "Status reports"
        ordering = ['created_at']
        # so that you can have only one valid processed transaction ?
        unique_together = ['valid', 'status', 'mb_transaction_id']

    class InvalidMD5Signature(Exception):
        def __init__(self, status_report):
            self.status_report = status_report

        def __unicode__(self):
            return "Invalid MD5 signature in status report #%d" % self.status_report.pk

    class InvalidTransactionData(Exception):
        def __init__(self, status_report):
            self.status_report = status_report

        def __unicode__(self):
            return "Invalid Transaction data: StatusReport data do not match with " \
                   "PaymentRequest data in StatusReport: {}!".format(self.status_report)

    # @property
    # def transaction_id(self):
    #     return self.payment_request.transaction_id

    # todo as a safety measure I can periodically check for completed payments using the skrill API
    # and compare them with zakanda status report with completed status. If something is missing take case

    def __unicode__(self):
        return 'id: {}, payment_request: {}'.format(self.id, self.payment_request)

    @classmethod
    def get_secret_word_as_md5(cls):
        """ returns md5 hash of SECRET_WORD in upper case """
        m = hashlib.md5()
        m.update(SECRET_WORD)
        return m.hexdigest().upper()

    def generate_md5_signature(self):
        """ hexdigest returns a bytestring but the received md5 hash value is unicode and the comparison
        would evaluate as not equal. So the returned bytestring is converted to unicode. """
        # logger.debug("generating md5 hash from merchant id: %s, transaction id: %s, secret_word: %s, mb_amount: %s, "
        #              "mb_currency: %s, status: %s", self.merchant_id, self.payment_request.transaction_id,
        #              self.get_secret_word_as_md5(), self.mb_amount, self.mb_currency, self.status)
        m = hashlib.md5()
        m.update(str(self.merchant_id))
        m.update(str(self.payment_request.transaction_id))
        m.update(self.get_secret_word_as_md5())
        m.update(str(self.mb_amount))
        m.update(self.mb_currency)
        m.update(str(self.status))
        return m.hexdigest().upper()

    def validate_md5sig(self):
        generated_md5 = unicode(self.generate_md5_signature(), "utf-8")  # or self.generate_md5_signature().decode("utf-8")
        # logger.debug("generated md5: %s (%s)", generated_md5, type(generated_md5))
        # logger.debug("received md5:  %s (%s)", self.md5sig, type(self.md5sig))
        if generated_md5 != self.md5sig:
            raise StatusReport.InvalidMD5Signature(self)

    def compare_status_and_request_data(self):
        """ the received data are of type unicode and in order to compare them with the existing model fields
        their types must match. This is a reason to create the status model (so that the received values are
        transformed to the field types and then check its validity"""
        # logger.debug("received amount - saved: %s(%s) - %s(%s)", self.mb_amount, type(self.mb_amount),
        #              self.payment_request.amount, type(self.payment_request.amount))
        # logger.debug("received pay_from_email - saved: %s(%s) - %s(%s)", self.pay_from_email, type(self.pay_from_email),
        #              self.payment_request.pay_from_email, type(self.payment_request.pay_from_email))
        if decimal.Decimal(self.mb_amount) != self.payment_request.amount:
            raise StatusReport.InvalidTransactionData(self)
        # if the user pays with another skrill account then the email match will fail
        # if self.payment_request.pay_from_email and self.pay_from_email != unicode(self.payment_request.pay_from_email):
        #     raise StatusReport.InvalidTransactionData(self)

    def validate(self):
        self.validate_md5sig()
        self.compare_status_and_request_data()

    def is_valid(self):
        try:
            self.validate()
        except Exception as e:
            logger.exception('Invalid skrill StatusReport %s, %s', self, e)
            return False
        return True


def password_hash():
    # it must be declared before its use as a model's field default value.
    # it gets evaluated every time you request a new default value.
    m = hashlib.md5()
    m.update(API_PASSWORD)
    return m.hexdigest().lower()


class TransferRequest(models.Model):
    # Have in mind that a transfer request can be have the prepared flag = True and not having an sid,
    # if something goes wrong with the request (network error or sth)

    # list of custom fields that will be ignored upon submit
    SUBMIT_IGNORE_FIELDS = ['user', 'user_id', 'test', 'prepared', 'created_at', 'updated_at', 'transferstatusreport',
                            'sid']
    prepare_choice = "prepare"
    transfer_choice = "transfer"
    action_choices = (
        (prepare_choice, "prepare"),
        (transfer_choice, "transfer"),
    )

    transaction_id = models.AutoField("Transaction ID", primary_key=True,
                                      help_text="It is the 'frn_trn_id' skrill field. Reference or identification "
                                                "number provided by the Merchant. MUST be unique for each transfer.")
    user = models.ForeignKey(User, verbose_name="User", related_name='transfer_requests')
    test = models.BooleanField("Is test", default=False)
    prepared = models.BooleanField("Is prepared", default=False, editable=False,
                                   help_text="If a 'prepare' transfer request has been send for this transfer_request. "
                                             "This flag has a meaning of existence despite the fact that there is "
                                             "also an 'action' flag since you know if a prepare request has been sent")
    # status_response_received = models.BooleanField("Is a status response received", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # skrill parameters
    action = models.CharField(max_length=8, choices=action_choices, default=action_choices[0][0])
    email = models.EmailField("Merchant account", max_length=50, default=PAY_TO_EMAIL, help_text="Your Merchant account")
    password = models.CharField(max_length=32, default=password_hash, help_text="The MD5 hash of your API/MQI password")
    amount = models.DecimalField("Amount", max_digits=19, decimal_places=2,
                                 help_text="Amount to be transferred. Note: Do not include the trailing zeroes if "
                                           "the amount is a natural number. For example: '23' (not '23.00')")
    currency = models.CharField("Currency", max_length=3, choices=ISO4217, default=DEFAULT_CURRENCY,
                                help_text="3-letter code of the currency of the amount according to ISO 4217")
    bnf_email = models.EmailField("Recipients email", max_length=50)
    subject = models.CharField(max_length=250, default="Money Received",
                               help_text="Subject of the notification email. Up to 250 1-byte characters.")
    note = models.CharField(max_length=2000, default="zakanda just sent you money through Skrill",
                            help_text="Comment to be included in the notification email. Up to 2000 1-byte characters.")
    sid = models.CharField("Session Id", max_length=50, null=True, blank=True, default=None,
                           help_text="The latest received session id")  # max_length 32

    def __unicode__(self):
        return "transaction_id {} [{}] {}{} - {}".format(self.transaction_id, self.user, self.amount, self.currency,
                                                          self.created_at)

    def _get_formatted_field_value(self, field):
        field_class = self._meta.get_field(field).__class__
        field_value = getattr(self, field)
        if field_class == models.DecimalField:
            if field_value % 1 == 0:
                # Do not include the trailing zeroes if the amount is a natural number. "23" (not "23.00").
                # This is mentioned in the Quick Checkout docs for the PaymentRequest but not for the TransferRequest
                # so it might be not necessary
                return str(int(field_value))
            return str(field_value)
        else:
            return field_value

    @classmethod
    def _map_fields_to_skrill_fields(cls, field):
        if field == "transaction_id":
            # This is the name that skrill uses for the reference number of your transaction.
            field = "frn_trn_id"
        return field

    @classmethod
    def parse_prepare_response(cls, response):
        """
        Skrill returns an XML response to the prepare request, which contains
        *   a <response> element containing one of the following elements
            *   <sid> element - returned if the authorisation and payment preparation is successful.
                The SID (Session Identifier) must be submitted in your transfer execution request
            *   <error> element - included if an error occurs.
                It includes an <error_msg> element, which contains the error message description.
        """
        logger.debug('parsing transfer prepare response...')
        root = etree.XML(response.text.encode('utf-8'))
        if len(root) == 0:
            raise (NoDataException("Root element has no children, (root el): %s" % root.text))
        for child in list(root):
            if child.tag == 'sid':
                sid = child.text
                return sid
            elif child.tag == 'error':
                for grandchild in list(child):
                    error_message = grandchild.text
                    raise TransferPrepareException(error_message)
            else:
                raise Exception("Unexpected tag in transfer prepare response")

    @classmethod
    def parse_execute_response(cls, response):
        """
        The correct XML response contains a <response> element that includes the following elements:
        * <transaction> element – returned if the transfer is successful;
        the response includes the elements described in Table4-3 below.
        * <error> element – returned if an error occurs, which includes
        an <error_msg> element, which provides details of the error.
        """
        logger.debug('parsing transfer execute response...')
        kwargs = dict()
        root = etree.XML(response.text.encode('utf-8'))
        if len(root) == 0:
            raise (NoDataException("Root element has no children, (root el): %s" % root.text))
        for child in list(root):
            if child.tag == "transaction":
                for grandchild in list(child):
                    if grandchild.tag == "amount":
                        amount = grandchild.text
                        kwargs["mb_amount"] = amount
                    elif grandchild.tag == "currency":
                        currency = grandchild.text
                        kwargs["mb_currency"] = currency
                    elif grandchild.tag == "id":
                        mb_transaction_id = grandchild.text
                        kwargs["mb_transaction_id"] = mb_transaction_id
                    elif grandchild.tag == "status":
                        status = grandchild.text
                        kwargs["status"] = status
                    elif grandchild.tag == "status_msg":
                        status_msg = grandchild.text
                        kwargs["status_msg"] = status_msg
                    else:
                        raise Exception("Unexpected tag in transfer execute response")
                return kwargs
            elif child.tag == "error":
                for grandchild in list(child):
                    if grandchild.tag == "error_msg":
                        error_msg = grandchild.text
                        raise TransferExecuteException(error_msg)
                    else:
                        raise Exception("Unexpected tag in transfer execute response")
            else:
                raise Exception("Unexpected tag in transfer execute response")

    def send_prepare_request(self, force_submit=False):
        logger.debug('sending transfer prepare request...')
        assert self.pk is not None, "Save TransferRequest before submitting!"
        if self.action != self.prepare_choice:
            # since resending a prepare request is possible the action argument only informs us
            # about the state of the transfer_request.
            logger.warning('Resending a transfer prepare request for a transfer that has already been executed')
            self.action = self.prepare_choice
            self.save()
        if not force_submit:
            assert not self.prepared, "TransferRequest prepare request already submitted!"
        payload = {}
        for field in self._meta.get_all_field_names():
            if field in self.SUBMIT_IGNORE_FIELDS:
                continue
            field_value = getattr(self, field)
            if field_value is not None and field_value != '':
                payload[self._map_fields_to_skrill_fields(field)] = self._get_formatted_field_value(field)

        logger.debug("posting data: %s to url: %s", payload, API_URL)
        response = requests.post(API_URL, payload)
        if not self.prepared:
            self.prepared = True
            self.save()
        return response

    def send_execute_request(self):
        logger.debug('sending transfer execute request...')
        assert self.sid, "A skrill session id must exist in order to execute a transfer request"
        self.action = self.transfer_choice
        self.save()
        paylod = dict()
        paylod["action"] = self.action
        paylod["sid"] = self.sid
        response = requests.post(API_URL, paylod)
        return response

    @classmethod
    def get_scheduled(cls):
        return

    @classmethod
    def resend_shady(cls):
        # regular job high frequency
        # get all requests which are 'prepared' but have no associated status report and resend them
        return

    def prepare_sequence(self):
        logger.info("Initiating transfer request sequence for %s", self)
        prepare_response = self.send_prepare_request()
        session_id = self.parse_prepare_response(prepare_response)
        logger.debug('saving session id %s...', session_id)
        # no need to raise exception if sid=None. In this case an Exception will be raised by send_execute_request
        self.sid = session_id
        self.save()
        return session_id

    def execute_sequence(self):
        execute_response = self.send_execute_request()
        params = self.parse_execute_response(execute_response)
        logger.debug('creating transfer request status report...')
        params["transfer_request"] = self
        try:
            # if a report already exists for this transfer request
            transfer_status_report = TransferStatusReport.objects.get(mb_transaction_id=params["mb_transaction_id"])
            logger.info('transfer_status_report already exists: %s', transfer_status_report)
            status = params["status"]
            if transfer_status_report.status == transfer_status_report.status_scheduled and \
                            status == transfer_status_report.status_processed:
                # In this case a scheduled transfer has been processed so
                # update existing transfer_status_report from scheduled to processed
                logger.info('updating transfer_status_report status from %s to %s', transfer_status_report.status,
                            status)
                transfer_status_report.status = status
                transfer_status_report.save()
                # Notice transfer_processed signal is send only on new transfer creation not an update.
                # Currently a new signal for the sqitch of scheduled to processed is not needed.
        except TransferStatusReport.DoesNotExist:
            transfer_status_report, created = TransferStatusReport.objects.get_or_create(**params)
            logger.info('new transfer_status_report was created successfully: %s', transfer_status_report)
        return transfer_status_report

    def prepare_and_execute(self):
        """ The prepare_sequence and execute_sequence functions raise exceptions on specific errors so they
        need to be inside a try except loop to catch and handle them appropriately """
        try:
            session_id = self.prepare_sequence()
            transfer_status_report = self.execute_sequence()
        except Exception as e:
            logger.exception('Error in skrill transfer request. %s', e)
            return
        return transfer_status_report


class TransferStatusReport(models.Model):
    """
    You receive a session id, you send an execute request for it, it is received by skrill and processed but
    you have no response due to a network error. Then you need to repost the execute request in order to get
    the response and handle it. What happens in this case is described bellow.

    You must resend the request within 15 minutes (before the transfer_request session expires).

    - If the transaction has been executed (???? what response you receive ????) you will need to generate a
    new session ID (action=prepare), since only one transaction is allowed per session. So in my context I
    need to resend the existing transfer_request (reapply the send process)

    - If the transaction associated with this session is still being executed, Skrill responds with status
    EXECUTION_PENDING (??? what status code or probably this is the status code ???).
    In this case you do not need to generate a new session ID
    and can wait for the response. Probably wait means that the original sending is executing and will get eventually
    a response

    If the 15 minutes have passed then you can just reapply the sending process of the transfer_request.
    So all shady transfer_requests will be simply resent.


    The Skrill server executes only one transaction per session, so the request cannot be duplicated
    If you resend the same transfer request (with the same frn_trn_id) nothing will happen.
    """
    status_scheduled = "scheduled"  #
    status_processed = "processed"
    transfer_status_choices = (
        # if you resend a transfer execution request the execution of which is still being executed the returned
        # status will be "EXECUTION_PENDING". Since the status field is IntegerField you will get an Exception
        # and no TransferStatusReport will be created and no change will be made to user's wallet. This transfer
        # request will be collected as a shady one and will be resend.
        (1, status_scheduled),  # (if beneficiary is not yet registered at Skrill)
        (2, status_processed),  # (if beneficiary is registered)
    )

    mb_amount = models.DecimalField("MB Amount", max_digits=19, decimal_places=2, help_text="Amount paid in the currency of your Skrill account.")
    mb_currency = models.CharField("MB Currency", max_length=3, choices=ISO4217, help_text="Currency of your Skrill account")
    mb_transaction_id = models.BigIntegerField("Skrill transaction ID", help_text="Moneybookers' unique transaction ID for the transfer.")
    status = models.IntegerField("Status", choices=transfer_status_choices,
                                 help_text="Status of the transaction. 2 possible values: "
                                           "'scheduled' (if beneficiary is not yet registered at Skrill) and "
                                           "'processed' (if beneficiary is registered'")
    status_msg = models.CharField("Status message", max_length=50)
    transfer_request = models.ForeignKey(TransferRequest, help_text="The TransferRequest object the execution request of which, returned this Status Report")
    claimed = models.BooleanField(default=True,
                                  help_text="This flag is taken under consideration only for 'scheduled' transfers. "
                                            "If the user doesn't claim the funds within the skrill timeframe (14 days?)"
                                            "then the funds are returned to the sender (zakanda) and must appear "
                                            "in users zakanda wallet. In this case the transfer_status obj is marked as"
                                            " unclaimed and the status remains 'scheduled'. Skrill docs don't "
                                            "mention any other possible status (like cancelled) so in order to "
                                            "identify a cancelled scheduled transfer we mark it with the flag "
                                            "unclaimed. So a 'scheduled' transfer with claim=False is a cancelled one."
                                            "(The unclaimed funds do not participate in the withdraws calculation)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # what is the role of status_msg? Can you have the same status but different message?
        unique_together = ['mb_transaction_id', 'status']

    def is_claimed(self):
        """ if it is scheduled and the required timeframe has passed mark them as unclaimed and send a signal
        (unclaimed_transfer_request) to make a zakanda wallet deposit"""
        wait_days = 14
        if self.status == self.status_processed:
            return True
        elif self.status == self.status_scheduled:
            if timezone.now() - self.created_at > wait_days:
                return False
        return True

    @classmethod
    def resend_scheduled(cls):
        # regular job high frequency
        scheduled_transfers = cls.objects.filter(status=cls.status_scheduled, claimed=True)
        if scheduled_transfers:
            logger.info('resending scheduled transfers %s...', scheduled_transfers.count())
        for scheduled_transfer in scheduled_transfers:
            # if it is processed the status will be updated
            scheduled_transfer.transfer_request.prepare_and_execute()

    @classmethod
    def resolve_unclaimed(cls):
        # regular job medium frequency
        # make a wallet deposit with the exact same amount to this request's user
        scheduled_transfers = cls.objects.filter(status=cls.status_scheduled, claimed=True)
        if scheduled_transfers:
            logger.info('resolving scheduled transfers %s...', scheduled_transfers.count())
        for scheduled_transfer in scheduled_transfers:
            if not scheduled_transfer.is_claimed():
                scheduled_transfer.transfer_request.prepare_and_execute()  # a final try
                if not scheduled_transfer.is_claimed():  # if it is still unclaimed
                    # send signal? remove flag?
                    scheduled_transfer.claimed = False
                    scheduled_transfer.save()

    # todo Wallet:
    # Become tipster page (give additional info)
    # if you are tipster you can create a Premium bet group
    # you edit your existing one and make it premium defining the needed info (price, period, max_subscribers etc.)
    # a global "Buy" button exists along with the "Follow" that buys all active Premium groups 1 month periods
    # a "Buy" button exists also per BetGroup.

    # wallet functionality changes: There is no zakanda wallet. Users buy directly and tipsters are paid automatically
    # wallet functionality can exist in the code, but it will not appear as such in the users
    # user buys: go through the deposit process and subscription process at once. wallet deposit is made, his
    #     wallet balance increases and then an expense (a subscription) is created at once so balance is equally decreased.
    #     all user's wallet balances must be 0.
    # Funds due to tipsters are not added to their wallet balance. They are calculated by the active subscriptions
    # and are paid to them at standard intervals. If it is their wallet balance I must ensure that they are forced
    # to make a new payment when they want to subscribe to others instead of using their existing balance.

    # todo payment errors
    # resolve shady payment requests instantly (not as a scheduled job) redirect to page on signal?
    # This is more important than shady transfer
    # requests because the user has to have a feedback on what happened so that he doesn't pay twice.

    # resolve the unclaimed transfer requests (ask skrill for details)

    # create a command that manually triggers the skrill_status_processed signal so that if there is a real payment
    # that wasn't followed by a signal for whatever reason, to manually do it
