import logging
from allauth.account.signals import email_confirmed
from django.dispatch import receiver
from django.contrib.sites.models import Site
# from django.core.mail import EmailMessage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from gutils.utils import get_user

logger = logging.getLogger(__name__)


@receiver(email_confirmed, dispatch_uid="custom.allauth.email_confirmed")
def user_signed_up_(request, email_address, **kwargs):
    logger.debug("sending welcome email to {}...".format(email_address))
    try:
        # email_address is an object
        user_id = email_address.user_id
    except Exception as e:
        user_id = None
    user = get_user(user_id)
    if not user:
        return
    subject = 'Welcome to zakanda {}'.format(user.username)
    context = {'user': user, 'request': request, 'site': Site.objects.get_current()}
    html_content = render_to_string('founder_welcome.html', context)
    text_content = strip_tags(html_content)  # this strips the html, so people will have the text as well.

    msg = EmailMultiAlternatives(subject, text_content, to=[user.email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
