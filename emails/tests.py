import logging
import json
import games.models
from games.utils import send_tb_mails
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def send_tip_email(total_bet, to_list=None, recipient_variables=None):
    send_tb_mails(total_bet.id, to_list, recipient_variables)


def check_tip_email():
    total_bet = games.models.TotalBet.objects.last()

    recipient = User.objects.get(username="dimgeo")
    to_list = [recipient.email]
    recipient_variables = {}
    recipient_values = {
        "username": recipient.username,
        "id": recipient.id,
    }
    recipient_variables[recipient.email] = recipient_values
    logger.debug("recipient_variables: %s", recipient_variables)
    recipient_variables = json.dumps(recipient_variables)
    logger.debug("json recipient_variables: %s", recipient_variables)

    send_tip_email(total_bet, to_list, recipient_variables)
