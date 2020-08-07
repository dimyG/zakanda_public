# from django.contrib.auth.models import User
# import user_accounts.utils
from games.models import Result
from bet_tagging.models import BetTag
from zakanda.utils import get_selected_bookmaker
# from django.core.urlresolvers import reverse
import logging

logger = logging.getLogger(__name__)


def main_processor(request):
    """ These variables override any variables with the same name defined in the context of the views """
    extra_context = dict()

    user = request.user
    if user.is_authenticated():
        total_balance = 0
        for bet_tag in user.bet_tags.all():
            total_balance += bet_tag.balance
        extra_context['total_balance'] = total_balance
        extra_context['decision_result_types'] = Result.decision_types
        extra_context['free'] = BetTag.free
        extra_context['premium'] = BetTag.premium
        extra_context['private'] = BetTag.private

        # following_list, followers_list = user_accounts.utils.follow_relations(user, User)
        # extra_context['following'] = following_list
        # extra_context['followers'] = followers_list
    selected_bookmaker, selected_bookmaker_name, added, updated = get_selected_bookmaker(request, get_bookmaker=False)
    extra_context["selected_bookmaker_name"] = selected_bookmaker_name
    # extra_context['default_domain'] = settings.DEFAULT_DOMAIN

    # logger.debug("%s %s", request.build_absolute_uri(), reverse('user_accounts:leader_board'))
    # if request.build_absolute_uri() == reverse('user_accounts:leader_board'):
    #     logger.debug("MATCH")

    return extra_context
