import logging
from collections import defaultdict
from actstream.models import following, followers, Follow
from gutils.utils import get_user
from django.utils import timezone
from django.contrib.auth.models import User
from emails.utils import email_user_for_new_followers
from django_comments.models import Comment
from games.models import TotalBet
from gutils.utils import get_object
from emails.utils import email_user
from zakanda.db import get_bet_events


logger = logging.getLogger(__name__)


def follow_relations(user, model):
    following_list = following(user, model)
    followers_list = followers(user)
    # logger.debug("following: %s, followers: %s", following_list, followers_list)
    return following_list, followers_list


def new_followers(target_user_id, hours):
    """ gets the followers of the given user that have been created within the last given hours """
    user = get_user(target_user_id)
    if not user:
        return
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(hours=hours)
    qs = Follow.objects.followers_qs(user).filter(started__gt=start_date, started__lt=end_date)
    filtered_followers = [follow.user for follow in qs]
    return filtered_followers


def scan_users_for_new_followers():
    users = User.objects.all()
    for user in users:
        user_id = user.id
        filtered_followers = new_followers(user_id, hours=24)
        if filtered_followers:
            email_user_for_new_followers.delay(user_id, filtered_followers)


def scan_users_for_new_tb_comments(timedelta):
    """
    :param timedelta: timedelta object
    :return: {user_id: [tb1, tb2, tb3], ... } user's tbs that have comments
    """
    # from django_comments.models import Comment
    # from gutils.utils import get_object
    # from emails.utils import email_user
    # from django.utils import timezone
    # from games.models import TotalBet
    logger.debug('scaning users for comments')
    start_date = timezone.now() - timedelta
    # comments under moderation aren't selected
    latest_comments = Comment.objects.filter(is_public=True, submit_date__gt=start_date)
    commented_tbs_by_target_user_id = defaultdict(list)
    for comment in latest_comments:
        target_object = get_object(comment.content_type, comment.object_pk)
        if isinstance(target_object, TotalBet):
            commented_tbs_by_target_user_id[target_object.user.id].append(target_object)
    return commented_tbs_by_target_user_id


def email_users_tb_comments(commented_tbs_by_target_user_id):
    """
    :param commented_tbs_by_target_user_id: {user_id: [tb1, tb2, tb3], ... } user's tbs that have comments
    :return:
    """
    logger.debug('emailing to %s', commented_tbs_by_target_user_id)
    # todo replace total_bets with their ids. In this case you must find a way
    # to attach to them the bet_events (maybe a template tag)
    subject = 'There are new comments on your bets!'
    template = 'emails/new_tb_comments.html'
    for user_id, total_bets in commented_tbs_by_target_user_id.iteritems():
        total_bets = list(set(total_bets))
        for tb in total_bets:
            bet_events = get_bet_events([tb], distinct=False, exclude_open=False)
            tb.bet_events = bet_events
        extra_context = {'total_bets': total_bets}
        email_user.delay(user_id, template, subject, extra_context)
