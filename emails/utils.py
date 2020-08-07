# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import requests
# import json
from zakanda.settings import mailgun_api_key, mailgun_domain, mailgun_email, mailgun_sender_name, mailgun_tips_mail
try:
    from zakanda.settings import EMAIL_BACKEND
except ImportError:
    EMAIL_BACKEND = None
# from zakanda.db import get_bet_events
# from actstream.models import followers
# from django.template.defaultfilters import pluralize
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django_rq import job
from gutils.utils import get_user
# from games.models import TotalBet

logger = logging.getLogger(__name__)


def mailgun_send(to_list, subject, text_template, html_template, context, recipient_variables,
                 from_arg=None, sender=None, text=None, html=None, **options):
    """
    :param sender: You can technically set the from field to be whatever you like (this is whet the recipients will see)
    The sender must always be one of your Mailgun domains.
    :param from_arg: if it is None, then the default mailgun domain will be used
    :param to_list: list of recipient emails
    :param options: a dictionary with mailgun options
    :param html: html must be a rendered string. If html is None then template and context must be provided
        in order to generate the html
    :param text: if text is None then template and context must be provided in order to generate the text
    :return:
    """

    default_smtp_backend = 'django.core.mail.backends.smtp.EmailBackend'
    if EMAIL_BACKEND and EMAIL_BACKEND != default_smtp_backend:
        logger.info('Dummy email backend found, email will not be send! Email info --> '
                    'subject: {}, to_list: {}, text: {}, recipient variables: {}'.format(
            subject, to_list, text, recipient_variables
        ))
        return

    logger.debug("initiating sending...")
    html_content = html or render_to_string(html_template, context)
    text_content = text or render_to_string(text_template, context)
    from_arg = from_arg or mailgun_sender_name + "<" + mailgun_tips_mail + ">"
    sender = sender or mailgun_sender_name + "<" + mailgun_email + ">"
    logger.debug('sender %s', sender)
    data = {
        "from": from_arg,
        "sender": sender,
        "to": to_list,
        "subject": subject,
        "text": text_content,
        "html": html_content,
        "recipient-variables": recipient_variables,
        # "recipient-variables": json.dumps({test_mail_01: {"username": "dimbetal"}, test_mail_02: {"username": "dimgeo"}}),
        # "o:testmode": "yes"
    }
    data.update(options)

    return requests.post(
        "https://api.mailgun.net/v3/"+mailgun_domain+"/messages",
        auth=("api", mailgun_api_key),
        data=data
    )


@job("emails", result_ttl=0, timeout=2*60*60)
def email_user_for_new_followers(target_user_id, filtered_followers):
    user = get_user(target_user_id)
    if not user:
        return
    domain = Site.objects.get_current().domain
    context = {'user': user, 'filtered_followers': filtered_followers, 'domain': domain, 'site': Site.objects.get_current()}

    subject = '{} you have new zakanda followers!'.format(user.username)
    html_content = render_to_string('emails/new_followers.html', context)
    text_content = strip_tags(html_content)  # this strips the html, so people will have the text as well.

    msg = EmailMultiAlternatives(subject, text_content, to=[user.email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@job("emails", result_ttl=0, timeout=2*60*60)
def email_user(target_user_id, html_template, subject, extra_context=None):
    """
    :param target_user_id: the user to send the email to
    :param html_template: it must be relative to this file location ('emails/template.html')
    :param subject:
    :param extra_context: dictionary
    :return:
    """
    user = get_user(target_user_id)
    if not user:
        return
    domain = Site.objects.get_current().domain
    context = {'domain': domain, 'site': Site.objects.get_current(), 'user': user}
    if isinstance(extra_context, dict):
        context.update(extra_context)

    html_content = render_to_string(html_template, context)
    text_content = strip_tags(html_content)  # this strips the html, so people will have the text as well.

    msg = EmailMultiAlternatives(subject, text_content, to=[user.email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
