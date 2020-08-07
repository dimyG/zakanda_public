import logging
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
# from django.utils import timezone
from actstream.models import Follow
from stream_django.client import stream_client
from zakanda.settings import FeedNames
import feeds.models
import feeds.api
import feeds.utils
import gutils.utils
import bet_tagging.models
# from django_comments.models import Comment
from django_comments_xtd.models import XtdComment
from django.core.urlresolvers import reverse

logger = logging.getLogger(__name__)


def create_follow_activity(user_id, target_user_id, follow_obj_id):
    follow_activity = feeds.models.FollowActivity.objects.create(
        user_id=user_id, target_user_id=target_user_id)


def delete_follow_activity(user_id, target_user_id):
    # only one object should normally be filtered
    # as I saw in feed_managers code, this action will trigger the activity_delete method which removes
    # the activity from GetStream
    feeds.models.FollowActivity.objects.filter(user_id=user_id, target_user_id=target_user_id).delete()


def create_bet_group_follow_activity(user_id, obj_id, follow_obj_id):
    follow_activity = feeds.models.BetGroupFollowActivity.objects.create(
        user_id=user_id, follow_object_id=obj_id)


def delete_bet_group_follow_activity(user_id, obj_id):
    # only one object should normally be filtered
    # as I saw in feed_managers code, this action will trigger the activity_delete method which removes
    # the activity from GetStream
    feeds.models.BetGroupFollowActivity.objects.filter(user_id=user_id, follow_object_id=obj_id).delete()


def upd_basic_stats_follow(user_id, target_object):
    # todo race condition check, use F expression?
    if target_object:
        target_object.basic_stats.num_followers += 1
        target_object.basic_stats.save()
    user = gutils.utils.get_user(user_id)
    if not user:
        logger.error("user with id %s who did a following action, doesn't exist!", user_id)
        return
    user.basic_stats.num_following += 1
    user.basic_stats.save()


def upd_basic_stats_unfollow(user_id, target_object):
    if target_object:
        if not target_object.basic_stats.num_followers:
            logger.error('unfollowing number, inconsistency for user: %s', target_object)
        else:
            target_object.basic_stats.num_followers -= 1
            target_object.basic_stats.save()

    user = gutils.utils.get_user(user_id)
    if not user:
        logger.error("user with id %s who did an unfollowing action, doesn't exist!", user_id)
        return
    if not user.basic_stats.num_following:
        logger.error('unfollowing number, inconsistency for user: %s', user)
        return
    user.basic_stats.num_following -= 1
    user.basic_stats.save()


# def follow_free_bet_groups(target_user):
#     free_type = bet_tagging.models.BetTag.free
#     free_bet_groups = target_user.bet_tags.filter(type=free_type)
#     if not free_bet_groups:
#         return
#     bet_group_content_type = ContentType.objects.get_for_model(free_bet_groups.first()).pk
#     for bet_group in free_bet_groups:
#         reverse('actstream_follow', kwargs={
#             'content_type_id': bet_group_content_type, 'object_id': bet_group.pk})
#
#
# def unfollow_free_bet_groups(target_user):
#     free_type = bet_tagging.models.BetTag.free
#     free_bet_groups = target_user.bet_tags.filter(type=free_type)
#     if not free_bet_groups:
#         return
#     bet_group_content_type = ContentType.objects.get_for_model(free_bet_groups.first()).pk
#     for bet_group in free_bet_groups:
#         reverse('actstream_unfollow', kwargs={
#             'content_type_id': bet_group_content_type, 'object_id': bet_group.pk})


def follow_handler(user_id, content_type_id, object_id, follow_obj):
    """
    follow and unfollow actions can't be worker jobs since they need to be executed in the right order. If you
    follow a user, the job is enqueue then you unfollow, it is also enqueue before the follow job is executed.
    In this case the unfollow job might be executed first
    :param user_id: the id of the user that did the follow action
    :param object_id: the id of the object that the user chose to follow
    """
    target_content_type = ContentType.objects.get_for_id(content_type_id)
    target_object = target_content_type.get_object_for_this_type(id=object_id)
    if target_content_type.model_class() == User:
        logger.debug("following target user's feed...")
        # user's timeline and aggregated_timeline feeds follow target user's user_feed (stream_django abstraction)
        # follow = feed_manager.follow_user(user_id, target_object)
        user_timeline = stream_client.feed(FeedNames.timeline, user_id)
        user_aggregated_timeline = stream_client.feed(FeedNames.timeline_aggregated, user_id)
        # notification_feed = stream_client.feed(FeedNames.notification, user_id)
        follow_timeline = user_timeline.follow(FeedNames.user, object_id)
        follow_aggr = user_aggregated_timeline.follow(FeedNames.user, object_id)
        # if your notification feed follows the target user, then every activity of the target user
        # will be collected and aggregated by the notification feed. Such activities might be:
        # submit_bet, follow user, make a comment etc. If you do not want that then you must
        # not follow him with your notification feed, but manually add to the notification feed
        # the activities you want, using either the "to" field or the activity_notify method
        # follow_not = notification_feed.follow(FeedNames.user, object_id)
        create_follow_activity(user_id, object_id, follow_obj.id)
        logger.debug("follow %s", follow_timeline)
        upd_basic_stats_follow(user_id, target_object)
        bet_tagging.models.NotificationSubscription.user_follow_handle(user_id, target_object)
    elif target_content_type.model_class() == bet_tagging.models.BetTag:
        logger.debug("following bet group %s", target_object)
        bet_tagging.models.NotificationSubscription.bet_group_follow_handle(user_id, target_object)
        create_bet_group_follow_activity(user_id, object_id, follow_obj.id)
    else:
        logger.error("Following object class is not User")
    return target_object


def unfollow_handler(user_id, content_type_id, object_id):
    target_content_type = ContentType.objects.get_for_id(content_type_id)
    target_object = target_content_type.get_object_for_this_type(id=object_id)
    if target_content_type.model_class() == User:
        logger.debug("unfollowing target user's feed...")
        user_timeline = stream_client.feed(FeedNames.timeline, user_id)
        user_aggregated_timeline = stream_client.feed(FeedNames.timeline_aggregated, user_id)
        # notification_feed = stream_client.feed(FeedNames.notification, user_id)
        unfollow_timeline = user_timeline.unfollow(FeedNames.user, object_id)
        unfollow_aggr = user_aggregated_timeline.unfollow(FeedNames.user, object_id)
        # unfollow_not = notification_feed.unfollow(FeedNames.user, object_id)
        delete_follow_activity(user_id, object_id)
        logger.debug("unfollow %s", unfollow_timeline)
        upd_basic_stats_unfollow(user_id, target_object)
        bet_tagging.models.NotificationSubscription.user_unfollow_handle(user_id, target_object)
    elif target_content_type.model_class() == bet_tagging.models.BetTag:
        logger.debug("unfollowing bet group %s", target_object)
        bet_tagging.models.NotificationSubscription.bet_group_unfollow_handle(user_id, target_object)
        delete_bet_group_follow_activity(user_id, object_id)
    else:
        logger.error("Unfollowing object class is not User")
    return target_object


def create_total_bet_tree_related_activities(user_id, total_bet, bet_events):
    num_bet_events = bet_events.count()
    # total_bet_activity = feeds.api.create_total_bet_zakanda_activity(user_id, total_bet, num_bet_events)
    bet_event_activities = feeds.api.create_bet_event_zakanda_activities(user_id, total_bet, bet_events, num_bet_events)
    # zakanda_activities = [total_bet_activity] + bet_event_activities
    if not total_bet.is_past:
        stream_activities = feeds.utils.sync_activities_to_stream(bet_event_activities, batch=True)
    # return stream_activities  # No need to store them in redis even instantly


@gutils.utils.disable_for_loaddata
@receiver(post_save, sender=Follow, dispatch_uid="follow_an_object")
def follow_signal(sender, instance, created, **kwargs):
    if created:
        user_id = instance.user_id
        content_type_id = instance.content_type_id
        object_id = instance.object_id
        # queue = django_rq.get_queue("default")
        # target_object = queue.enqueue(follow_handler, user_id, content_type_id, object_id, result_ttl=0)
        target_object = follow_handler(user_id, content_type_id, object_id, instance)


@receiver(post_delete, sender=Follow, dispatch_uid="unfollow_an_object")
def unfollow_signal(sender, instance, **kwargs):
    user_id = instance.user_id
    content_type_id = instance.content_type_id
    object_id = instance.object_id
    # queue = django_rq.get_queue("default")
    # target_object = queue.enqueue(unfollow_handler, user_id, content_type_id, object_id, result_ttl=0)
    target_object = unfollow_handler(user_id, content_type_id, object_id)


def notifications_unfollow_all():
    follows = Follow.objects.all()
    for obj in follows:
        user_id = obj.user.id
        content_type = obj.content_type
        target_id = obj.object_id
        user_content_type = ContentType.objects.get_for_model(User)
        if content_type == user_content_type:
            notification_feed = stream_client.feed(FeedNames.notification, user_id)
            unfollow = notification_feed.unfollow(FeedNames.user, target_id)


@gutils.utils.disable_for_loaddata
@receiver(post_save, sender=XtdComment, dispatch_uid="create_a_comment")
def comment_create_handler(sender, instance, created, **kwargs):
    # todo notify only if the comment is_public when created else when it is updated from public False to True
    if created:
        logger.debug('new comment created')
        zak_activity = feeds.models.CommentActivity.objects.create(comment=instance)


@gutils.utils.disable_for_loaddata
@receiver(post_delete, sender=XtdComment, dispatch_uid="delete_a_comment")
def comment_delete_handler(sender, instance, **kwargs):
    feeds.models.CommentActivity.objects.filter(comment=instance).delete()
