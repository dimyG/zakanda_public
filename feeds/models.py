from __future__ import unicode_literals

import logging
from django.db import models
from django.contrib.auth.models import User
import games.models
from bet_tagging.models import BetTag
from stream_django.activity import Activity, create_reference
from stream_django.feed_manager import feed_manager
from django.contrib.contenttypes.models import ContentType
# from django_comments.models import Comment
from django_comments_xtd.models import XtdComment
from actstream.models import Follow

logger = logging.getLogger(__name__)


class RawBetEvent(models.Model):
    """ It describes a raw bet event, for example (Aris-Paok Full_Time 1) """
    # todo move it to bet_statistics app
    event = models.ForeignKey(games.models.Event)
    market_type = models.ForeignKey(games.models.MarketType)
    choice = models.CharField(max_length=15)

    class Meta():
        unique_together = ('event', 'market_type', 'choice')

    def __unicode__(self):
        return "{} - {} {} {}".format(self.event.home_team, self.event.away_team, self.market_type, self.choice)

    def get_bet_events(self):
        bet_events = games.models.BetEvent.objects.filter(event=self.event, market_type=self.market_type, selection__choice=self.choice)
        if not bet_events:
            logger.error('RawBetEvent %s has no related BetEvents', self)
            return
        return bet_events

    def get_status(self):
        bet_events = self.get_bet_events()
        if not bet_events:
            return
        # normally all related bet_events have the same status (except during the bet_event settlement process)
        random_bet_event = bet_events[0]
        status = random_bet_event.selection.status
        return status

    def get_popularity(self):
        # todo raw bev get_popularity
        return

    def get_bet_amounts(self):
        # todo raw bev get_bet_amounts
        return

    def get_bettors(self):
        return

    def get_bettors_num(self):
        # todo raw bev get_bettors_num
        return


class BetEventActivity(models.Model):
    """
    * A bet_event must already exist when a user uses it. For this reason, the time field of the bet_event zakanda
    activity is the created_at field of the activity (and not the created_at of the bet_event)
    * A BetEventActivity is created for every bet_event no matter if an actual bet_event was created or not.
    * The Foreign_ID that is stored in the Stream db, is the id of the activity that you have saved in your db.
    * Have in mind that currently this model has no date field. So activities for past bet events (submitted by
      past bets) will be saved with the current date and not the old one. Currently this is not a problem since
      this model is used primarily for creating the getstream.io activities from it which are not created for past
      bets. It is also used to extract the popular raw bet_events so the date is not an issue.
    """
    default_verb = 'submit_bet_event'
    actor = models.ForeignKey(User, related_name='bev_activities')
    verb = models.CharField(max_length=20, default=default_verb)
    object = models.ForeignKey(RawBetEvent, related_name='bev_activities')
    bet_event = models.ForeignKey(games.models.BetEvent, related_name='bev_activities')
    total_bet = models.ForeignKey(games.models.TotalBet, related_name='bev_activities')
    event = models.ForeignKey(games.models.Event, related_name='bev_activities')
    num_bet_events = models.IntegerField()  # how many bevs the tb of this bev has
    # target = models.ForeignKey()
    # to = models.ManyToManyField()
    # foreign_id = self.id
    created_at = models.DateTimeField(auto_now_add=True)    # Stream activity uses this value as "time"
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "{} {} {} at {}".format(self.actor.username, self.verb, self.object, self.created_at)


class TotalBetActivity(models.Model):
    """
    The time field of the zakanda total_bet_activity is set equal to the created_at of the actual total_bet
    created_at field (not the total_bet_activity created_at as we do for bet_event_activities)
    """
    default_verb = 'submit_total_bet'
    actor = models.ForeignKey(User, related_name='total_bet_activities')
    verb = models.CharField(max_length=20, default=default_verb)
    object = models.OneToOneField(games.models.TotalBet, related_name='activities')
    num_bet_events = models.IntegerField()
    time = models.DateTimeField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """ I override the save method to define the time field equal to the total_bet created_at """
        if not self.time:
            self.time = self.object.created_at
        super(TotalBetActivity, self).save(*args, **kwargs)

    def __unicode__(self):
        return "{} submitted {}".format(self.actor, self.object.id)

    # def timesince(self, now=None):
    #     """
    #     Shortcut for the ``django.utils.timesince.timesince`` function of the
    #     current timestamp.
    #     """
    #     return djtimesince(self.timestamp, now).encode('utf8').replace(b'\xc2\xa0', b' ').decode('utf8')


class FollowActivity(models.Model, Activity):
    """ Activity for following a User """
    # this activity is needed so that I can notify users for new followers.
    # I didn't subclass the actstream Follow model since that one can be used
    # to follow any object. I only wanted to create activities for user follows.

    # It subclasses the Activity class. This way when a FollowActivity is created,
    # stream_django converts it into an activity and sends that to GetStream APIs.
    # This way you don't have to manually send (sync) the activities to GetStream
    default_verb = 'follow'
    verb = models.CharField(max_length=10, default=default_verb)
    user = models.ForeignKey(User, related_name='follow_activities')
    target_user = models.ForeignKey(User, related_name='followed_activities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'target_user')

    def follow_obj(self):
        """ :return: The Follow object that corresponds to this follow_activity """
        user = self.user
        target_user = self.target_user
        target_user_id = target_user.id
        user_content_type = ContentType.objects.get_for_model(User)
        try:
            follow_obj = Follow.objects.get(user=user, content_type=user_content_type, object_id=target_user_id)
            return follow_obj
        except Exception as e:
            logger.debug('%s', e)

    # @property
    # def activity_author_feed(self):
    #     '''
    #     The name of the feed where the activity will be stored; this is normally
    #     used by the manager class to determine if the activity should be stored elsewehere than
    #     settings.USER_FEED
    #     '''
    #     pass

    @property
    def activity_verb(self):
        return self.default_verb

    @property
    def activity_actor_attr(self):
        return self.user

    @property
    def activity_object_attr(self):
        return self.target_user

    @property
    def activity_foreign_id(self):
        return create_reference(self)

    @property
    def activity_notify(self):
        # Here we add the follow activity to the notification feed of the target user
        # to notify him about his new follower.
        # Then you can define an aggregation statement for the notification feed and you are done.
        return [feed_manager.get_notification_feed(self.target_user.id)]


# todo can I create a single generic Activity model for all types of following objects, using
# generic foreign keys. Then set the object, the foreign ids and the notifications depending on the content_type
class BetGroupFollowActivity(models.Model, Activity):
    """ Activity for following a BetGroup """
    default_verb = 'bet_group_follow'
    verb = models.CharField(max_length=25, default=default_verb)
    user = models.ForeignKey(User, related_name='bet_group_follow_activities')
    follow_object = models.ForeignKey(BetTag, related_name='follow_activities')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'follow_object')

    def follow_obj(self):
        """ :return: The Follow object that corresponds to this follow_activity """
        user = self.user
        obj = self.follow_object
        obj_id = obj.id
        obj_content_type = ContentType.objects.get_for_model(BetTag)
        try:
            follow_obj = Follow.objects.get(user=user, content_type=obj_content_type, object_id=obj_id)
            return follow_obj
        except Exception as e:
            logger.debug('%s', e)

    # @property
    # def activity_author_feed(self):
    #     '''
    #     The name of the feed where the activity will be stored; this is normally
    #     used by the manager class to determine if the activity should be stored elsewehere than
    #     settings.USER_FEED
    #     '''
    #     pass

    @property
    def activity_verb(self):
        return self.default_verb

    @property
    def activity_actor_attr(self):
        return self.user

    @property
    def activity_object_attr(self):
        return self.follow_object

    @property
    def activity_foreign_id(self):
        return create_reference(self)

    @property
    def activity_notify(self):
        # Here we add the follow activity to the notification feed of the bet_group's owner
        # to notify him about his new subscriber.
        # Then you can define an aggregation statement for the notification feed and you are done.
        return [feed_manager.get_notification_feed(self.follow_object.owner.id)]


class CommentActivity(models.Model, Activity):
    verb = 'comment'
    # verb = models.CharField(max_length=10, default=default_verb)
    # in case of unauthenticated users, user will be null
    # user = models.ForeignKey(User, null=True, blank=True, related_name='comment_activities')
    # if you want to group activities by user you have to use a username field
    # so that you can group by different unauthenticated users
    # content_type = models.ForeignKey(ContentType, db_index=True)
    # object_id = models.CharField(max_length=255, db_index=True)
    comment = models.OneToOneField(XtdComment, related_name='comment_activity')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_object(self):
        content_type = self.comment.content_type
        target_obj_id = self.comment.object_pk
        model = content_type.model_class()
        try:
            obj = model.objects.get(pk=target_obj_id)
        except Exception as e:
            logger.error('%s', e)
            obj = None
        logger.debug('comment activity selected object: %s', obj)
        return obj

    def get_actor(self):
        try:
            return self.comment.user
        except Exception as e:
            logger.error('%s', e)

    # @property
    # def activity_author_feed(self):
    #     '''
    #     The name of the feed where the activity will be stored; this is normally
    #     used by the manager class to determine if the activity should be stored elsewehere than
    #     settings.USER_FEED
    #     '''
    #     return

    @property
    def activity_verb(self):
        return self.verb

    @property
    def activity_actor_attr(self):
        return self.get_actor()

    @property
    def activity_object_attr(self):
        return self.get_object()

    @property
    def activity_foreign_id(self):
        return create_reference(self)

    @property
    def activity_notify(self):
        # access the followup attr of comment_xtd and notify if True
        obj = self.get_object()
        if isinstance(obj, games.models.TotalBet):
            return [feed_manager.get_notification_feed(obj.user.id)]
        # notify users for comments in events on which they have open bets
        # notify users for comments in events related with their favorite teams
