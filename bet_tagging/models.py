# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
import math
import logging
import pandas as pd
from django.utils import timezone
from django.db import models, IntegrityError
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.sites.models import Site
from django.db.models import F
from zakanda.settings import SessionKeys, FeedNames
import games.models
import gutils.utils
from actstream.models import following, followers, Follow
from stream_django.client import stream_client
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django_rq import job
from django.utils.translation import ugettext_lazy as _
from skrill.models import StatusReport
from actstream.actions import follow, unfollow
from django.db import transaction
import emails.utils
import skrill.models

# import bet_statistics.views

logger = logging.getLogger(__name__)


# todo QUEUE HIGH PRIORITY
@job("default", result_ttl=0, timeout=2 * 60 * 60)
def bet_group_create_handle_job(bet_group_id):
    NotificationSubscription.bet_group_create_handle(bet_group_id)


# todo QUEUE HIGH PRIORITY
@job("default", result_ttl=0, timeout=2 * 60 * 60)
def to_archived_handle(bet_group_id):
    try:
        bet_group = BetTag.objects.get(id=bet_group_id)
    except BetTag.DoesNotExist as e:
        logger.debug('%s', e)
        return
    bet_group.notification_subscriptions.all().delete()

    user_id = bet_group.owner.id
    import bet_statistics.signals
    bet_statistics.signals.update_user_cache(user_id)


# todo QUEUE HIGH PRIORITY
@job("default", result_ttl=0, timeout=2 * 60 * 60)
def to_free_handle(bet_group_id):
    try:
        bet_group = BetTag.objects.get(id=bet_group_id)
    except BetTag.DoesNotExist as e:
        logger.debug('%s', e)
        return
    nss = NotificationSubscription.bet_group_create_handle(bet_group_id)

    user_id = bet_group.owner.id
    import bet_statistics.signals
    bet_statistics.signals.update_user_cache(user_id)


# todo QUEUE HIGH PRIORITY
@job("default", result_ttl=0, timeout=2 * 60 * 60)
def from_free_handle(bet_group_id):
    try:
        bet_group = BetTag.objects.get(id=bet_group_id)
    except BetTag.DoesNotExist as e:
        logger.debug('%s', e)
        return
    logger.debug("deleting notification subscriptions for bet group: %s", bet_group_id)
    bet_group.notification_subscriptions.all().delete()

    user_id = bet_group.owner.id
    import bet_statistics.signals
    bet_statistics.signals.update_user_cache(user_id)


@job("emails", result_ttl=0, timeout=2 * 60 * 60)
def to_premium_handle(bet_group_id):
    # from premium: there is no need to auto unfollow the bet group. When the existing subscriptions expire
    # the auto unfollow will happen.
    try:
        bet_group = BetTag.objects.get(id=bet_group_id)
    except BetTag.DoesNotExist as e:
        logger.debug('%s', e)
        return
    owner = bet_group.owner
    owner_followers = followers(owner)
    if not owner_followers:
        return
    # owner_followers_ids = owner_followers.values_list('id', flat=True)
    subject = 'Your tipster {} offers a new Premium service!'.format(owner.username)
    html_template = 'bet_tagging/to_premium.html'
    text_template = 'bet_tagging/to_premium.txt'
    context = {'domain': Site.objects.get_current().domain, 'bet_group': bet_group}
    to_list = []
    recipient_variables = {}
    for user in owner_followers:
        to_list.append(user.email)
        recipient_values = {
            "username": user.username,
            "id": user.id,
        }
        recipient_variables[user.email] = recipient_values
    recipient_variables = json.dumps(recipient_variables)
    res = emails.utils.mailgun_send(to_list, subject, text_template, html_template, context, recipient_variables)
    logger.debug("send mailgun mails function returned %s", res)


class PaymentReport(models.Model):
    skrill_report = models.OneToOneField(skrill.models.StatusReport, related_name='generic_report')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # I didn't created a GenericForeignKey since I wanted to be able to do this:
    # filter and exclude do not work on Generic Relations:
    # PaymentReport.objects.filter(report=a_status_report)  # not ok
    # PaymentReport.objects.get(report=a_status_report)  # not ok


class GenericTransferReport(models.Model):
    """ just so that the provider specific reports do not belong to the Subscription model.
    One transfer_report can be connected with more that one Subscriptions
    (all tipster's subscription contribute to the due funds that are transfered). Also, one subscription can be
    connected with more than one transfers. (The 3 months subscriptions are paid monthly). So a 3 months subscription
    would be fully paid when the number of transfers is 3.

    num of transfer_reports is the number of times this subscription has been paid to the tipster.
    A fully paid 30 days subscription should have 1 transfer report. A fully paid 90 days subscription should have
    3 transfer reports. This way we can identify which subscriptions are not yet fully paid, so that they are taken
    into account for the tipster's monthly due funds calculation.
    """
    skrill_report = models.OneToOneField(skrill.models.TransferStatusReport, related_name='generic_report')
    # paypal_report = models.OneToOneField(paypal.TransferStatusReport)  # etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Subscription(models.Model):
    """
    Every subscription is connected with one payment report. On renewal a new subscription is created,
    with new start and end date and a new payment report. If you have an active subscription
    for a service then you can't create a new one for the same service.
    On recurring subscriptions first deactivate the first and then create a new one so that always there is only
    one active subscription for each user and service

    Subscriptions are being paid to tipster the following pay day. If a subscription is made at 29/11 and
    pay day is 30/11 then it will be paid to the tipster."""
    user = models.ForeignKey(User, related_name='subscriptions')
    service = models.ForeignKey('Service', related_name='subscriptions')
    payment_report = models.OneToOneField(PaymentReport, related_name='subscription')
    transfer_reports = models.ManyToManyField(GenericTransferReport, related_name='subscriptions')
    active = models.BooleanField(default=True)
    recurring = models.BooleanField(default=False)
    # fully_paid = models.BooleanField(default=False)

    # It is more robust for the end_date to be a model field instead of a method so that it isn't affected
    # by modifications in Service duration.
    end_date = models.DateTimeField()  # now + service.duration
    # renewed_at = models.DateTimeField()  # start date
    created_at = models.DateTimeField(auto_now_add=True)  # start date
    updated_at = models.DateTimeField(auto_now=True)

    # todo high, send email for subscription expiration
    # create subscription on payment status_report processed signal, and create also the follow relationship there
    # regular job once per day to check subscription end_dates and unfollow bet groups if now > end_date and
    # recurring = False. This way the followers are always the active subscribers
    # on post save if you don't follow the user then auto-follow him? Not necessary. If you want his free, follow him
    # on post save update the notification_subscription to all True
    # is currently allowed for a user to subscribe in 2 services of the same bet_group? No it is checked in the payment view
    def __unicode__(self):
        return '{} [{} {}] - active:{}'.format(self.user, self.service.bet_group.name, self.service.bet_group.owner.username, self.active)

    def is_fully_paid(self):
        # If a transfer becomes unclaimed (the funds have returned to zakanda skrill account) and the
        # subscriptions must be collected for a new transfer. In this case its subscriptions are not
        # considered fully paid and will be collected for the due funds calculation.
        # When there is a new scheduled transfer, it is onitially treated as claimed (for the wait period).
        # When the wait passes and doesn't become processed, then it is unclaimed.
        claimed_transfers = self.transfer_reports.filter(skrill_report__claimed=True)
        # logger.debug('reports: %s', self.transfer_reports.all())
        if self.transfer_reports.all() and claimed_transfers.count() == int(self.service.duration/30):
            # logger.debug('fully paid subscription %s', self)
            return True
        # logger.debug('not fully paid subscription %s', self)

    def expired(self):
        if timezone.now() > self.end_date:
            return True

    def activate(self):
        logger.info("activating subscription %s...", self)
        follow_obj = follow(self.user, self.service.bet_group)
        if not self.active and follow_obj:
            self.active = True
            self.save()

    def deactivate(self):
        logger.info("deactivating subscription %s...", self)
        if self.active:
            self.active = False
            self.save()
        unfollow(self.user, self.service.bet_group)

    def save(self, *args, **kwargs):
        """ Ensure that a user has only one active subscription to a specific service """
        if not self.pk:
            # if a new subscription is to be created (not updating an existing one)
            active_service_subscriptions = self.user.subscriptions.filter(active=True).filter(service=self.service)
            if active_service_subscriptions:
                logger.error('User already has an active subscription for this service! [%s %s]', self.user, self.service)
                raise IntegrityError
        super(Subscription, self).save(*args, **kwargs)

    @classmethod
    def check_for_expired(cls):
        """ it must run regularly """
        active_subscriptions = cls.objects.filter(active=True)
        expired_subscriptions = []
        for subscription in active_subscriptions:
            if subscription.expired():
                # todo handle recurring subscriptions
                subscription.deactivate()
                expired_subscriptions.append(subscription)
        logger.info("%s expired subscriptions were deactivated", len(expired_subscriptions))
        return expired_subscriptions

    @classmethod
    def create_subscription_tree(cls, skrill_payment_report):
        """ creates the subscription tree when a payment has been completed successfully.
        Normally it is invoked by the skrill_status_report_processed signal and extracts the needed information
        from the created status_report """
        logger.info("creating subscription tree from %s...", skrill_payment_report)
        user = skrill_payment_report.payment_request.user
        # 1. create a generic PaymentReport
        payment_report = PaymentReport(skrill_report=skrill_payment_report)
        payment_report.save()
        # 2. get the service
        service = Service.get_from_report(skrill_payment_report)
        if not service:
            logger.exception("Error on Subscription tree creation for report: %s!", skrill_payment_report)
            return
        # 3. create a Subscription
        try:
            with transaction.atomic():
                end_date = timezone.now() + timezone.timedelta(days=service.duration)
                subscription = cls(user=user, service=service, payment_report=payment_report, end_date=end_date)
                subscription.save()
                # 4. user follows bet group
                subscription.activate()  # more actions are triggered by the post_save_follow signal
                # NOTICE: As I saw if there is an exception in the functions executed in the signal
                # the transaction is rolled back! The signal is considered part of the transaction block.
        except Exception as e:
            logger.exception("Error on Subscription tree creation for report: %s! %s. transaction rolled back", skrill_payment_report, e)
            return
        return subscription


# https://stackoverflow.com/questions/18489393/django-submit-two-different-forms-with-one-submit-button
class Service(models.Model):
    # if the bet group becomes Free the Service is not deleted. This is just for retaining the information
    # of past services and related subscriptions. Notice that this way there will be Free Bet groups
    # related with services
    price_choices = (
        # (10, 10),
        (15, 15),
        (20, 20),
        (25, 25),
        (30, 30),
        (35, 35),
        (40, 40),
        (45, 45),
        (50, 50),

        (60, 60),
        (70, 70),
        (80, 80),
        (90, 90),
        (100, 100),

        (120, 120),
        (140, 140),
        (160, 160),
        (180, 180),
        (200, 200),
        (220, 220),
        (240, 240),
        (260, 260),
        (280, 280),
        (300, 300),

        (350, 350),
        (400, 400),
        (450, 450),
        (500, 500),

        (600, 600),
        (700, 700),
        (800, 800),
        (900, 900),
        (1000, 1000),

        (1250, 1250),
        (1500, 1500),
        (2000, 2000),
        (2500, 2500),
        (3000, 3000),
    )
    duration_30 = 30
    duration_90 = 90
    duration_180 = 180
    duration_choices = (
        (duration_30, duration_30),
        # (15, 15),
        # (7, 7),
        (duration_90, duration_90),
        # (duration_180, duration_180),
    )
    bet_group = models.ForeignKey('BetTag', related_name='services')
    subscribers = models.ManyToManyField(User, through=Subscription, related_name='services')
    price = models.PositiveIntegerField(choices=price_choices)
    # duration in days
    duration = models.PositiveIntegerField(choices=duration_choices)
    subscribers_limit = models.PositiveIntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('bet_group', 'duration')

    def __unicode__(self):
        return '{} {} price{} days{} subs{}'.format(self.bet_group.owner, self.bet_group.name, self.price, self.duration, self.subscribers.count())

    def active_subscribers(self):
        return self.subscribers.filter(subscriptions__service=self, subscriptions__active=True)

    def monthly_price(self):
        monthly_price = self.price * float(30.0/self.duration)
        # return the first 1 decimal place of the monthly price (1.6699 -> 1.66)
        return math.floor(monthly_price*10)/10

    def due_subscriptions(self):
        subscriptions = []
        for subscription in self.subscriptions.all():
            if not subscription.is_fully_paid():
                subscriptions.append(subscription)
        return subscriptions
        # return self.subscriptions.filter(fully_paid=False)  # active or inactive

    def monthly_turnover(self):
        # Once per month all the not fully paid subscriptions pay a monthly installment to the tipster
        # logger.debug('  service (%s), due subscriptions: %s, [%s, %s] turnover: %s',
        #              self, due_subscriptions, self.monthly_price(), due_subscriptions.count(),
        #              self.monthly_price() * due_subscriptions.count())
        return self.monthly_price() * len(self.due_subscriptions())

    @classmethod
    def get_from_report(cls, report):
        """ The service id is stored in the field_2 attribute of the payment report """
        service_id = report.field_2
        if not service_id:
            service_id = report.payment_request.Field2
        if not service_id:
            logger.error('service_id can not be extracted from report %s', report)
            return
        try:
            service = cls.objects.get(id=service_id)
        except Exception as e:
            logger.error("%s", e)
            return
        return service


class NotificationSubscription(models.Model):
    # This model is created on follow bet group post save signal for premium bet groups and on follow
    # user for his Free bet groups (since Free bet groups are not followed). It is deleted when not needed.
    # In the setup in which it has a OneToOne relationship with the Follow object, it was too complicated
    # to get the recipients for a particular notification type (email, in_app etc.).
    # So I replaced this setup with 2 ForeignKeys to User and BetGroup which has the same effect.
    # follow_obj = models.OneToOneField(Follow)
    user = models.ForeignKey(User, related_name='notification_subscriptions')
    bet_group = models.ForeignKey('BetTag', related_name='notification_subscriptions')
    email = models.BooleanField(default=True)
    in_app = models.BooleanField(default=True)
    # sms = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'bet_group')

    def __unicode__(self):
        return '{} {}'.format(self.user, self.bet_group)

    @classmethod
    def initialize_existing_relationships(cls):
        """ Creates entries for existing following relationships. Must run after the model's migration """
        users = User.objects.all()
        notification_subscriptions = []
        for user in users:
            following_users = following(user)
            if not following_users:
                continue
            free_bet_groups = BetTag.objects.filter(owner__in=following_users).filter(type=BetTag.free)
            for bet_group in free_bet_groups:
                try:
                    notification_subscription = cls.objects.create(user=user, bet_group=bet_group)
                except IntegrityError:
                    logger.info('notification subscription for user: %s and bet group: %s already exists', user, bet_group)
                    continue
                notification_subscriptions.append(notification_subscription)
        logger.info('%s notification_subscriptions were created', len(notification_subscriptions))

    @classmethod
    def bet_group_create_handle(cls, bet_group_id):
        """ When a new Free bet group is created, new notification subscription entries are created
        for the existing user followers """
        logger.debug('bet_group_create_handle...')
        try:
            bet_group = BetTag.objects.get(id=bet_group_id)
        except Exception as e:
            logger.warning('%s', e)
            return
        if not bet_group.type == BetTag.free:
            return
        user_followers = followers(bet_group.owner)
        if not user_followers:
            return
        notification_subscriptions = []
        for user in user_followers:
            try:
                notification_subscription = cls.objects.create(user=user, bet_group=bet_group)
                notification_subscriptions.append(notification_subscription)
            except Exception as e:
                logger.error('%s', e)
        logger.debug('%s notification_subscriptions were created', len(notification_subscriptions))
        return notification_subscriptions

    @classmethod
    def bet_group_follow_handle(cls, user_id, bet_group):
        """ If a user subscribes to a bet group then all notifications must be active by default """
        user = gutils.utils.get_user(user_id)
        if not user:
            return
        try:
            # if a notification already exists, for example if this bet group was a Free one before, then
            # make the values True
            notification_subscription = cls.objects.get(user=user, bet_group=bet_group)
            if not notification_subscription.email or not notification_subscription.in_app:
                notification_subscription.email = True
                notification_subscription.in_app = True
                notification_subscription.save()
        except cls.DoesNotExist as e:
            logger.debug("%s", e)
            notification_subscription = cls.objects.create(user=user, bet_group=bet_group)
        return notification_subscription

    @classmethod
    def bet_group_unfollow_handle(cls, user_id, bet_group):
        user = gutils.utils.get_user(user_id)
        if not user:
            return
        try:
            notification_subscription = cls.objects.get(user=user, bet_group=bet_group)
            notification_subscription.delete()
        except cls.DoesNotExist as e:
            logger.warning("%s. User %s didn't had a notification_subscription for bet group %s as he should",
                           e, user, bet_group)

    @classmethod
    def user_follow_handle(cls, request_user_id, target_user):
        """
        Create notification_subscriptions for the Free bet groups of target_user
        :param request_user_id: the user who did the follow action
        :param target_user: the user who was followed
        :return:
        """
        request_user = gutils.utils.get_user(request_user_id)
        if not request_user:
            return
        free_type = BetTag.free
        free_bet_groups = target_user.bet_tags.filter(type=free_type)
        if not free_bet_groups:
            return
        notification_subscriptions = []
        for bet_group in free_bet_groups:
            try:
                notification_subscription = cls.objects.create(user=request_user, bet_group=bet_group)
                notification_subscriptions.append(notification_subscription)
            except Exception as e:
                logger.error('%s', e)
                continue
        logger.debug('%s notification_subscriptions were created', len(notification_subscriptions))
        return notification_subscriptions

    @classmethod
    def user_unfollow_handle(cls, request_user_id, target_user):
        """
        Delete notification_subscriptions for the Free bet groups of target_user
        :param request_user_id: the user who did the unfollow action
        :param target_user: the user who was unfollowed
        :return:
        """
        request_user = gutils.utils.get_user(request_user_id)
        if not request_user:
            return
        free_type = BetTag.free
        free_bet_groups = target_user.bet_tags.filter(type=free_type)
        if not free_bet_groups:
            return
        notification_subscriptions = cls.objects.filter(bet_group__in=free_bet_groups)
        notification_subscriptions.delete()
        logger.debug('%s notification_subscriptions were deleted', len(notification_subscriptions))

    # def get_bet_group(self):
    #     follow_obj = self.follow_obj
    #     content_type_id = follow_obj.content_type_id
    #     object_id = follow_obj.object_id
    #     target_content_type = ContentType.objects.get_for_id(content_type_id)
    #     target_object = target_content_type.get_object_for_this_type(id=object_id)
    #     if not target_content_type.model_class() == BetTag:
    #         logger.error('')
    #         return
    #     return target_object
    #
    # def get_user(self):
    #     follow_obj = self.follow_obj
    #     user_id = follow_obj.user_id
    #     user = gutils.utils.get_user(user_id)
    #     return user


class BetTag(models.Model):
    default_name = 'default'

    # these variables must not be translated here since if you are in greek language, in the template
    # the expression: {% if bet_group.type == bet_group.free %} would be: free == ελευθερη. But this
    # way you have to manually add these variables in the .po file by yourself, they aren't collected
    # by the makemessages command
    free = 'Free'
    premium = 'Premium'
    private = 'Private'
    archived = 'Archived'
    type_choices = (
        # the first element must be in english so that all entries are stored in english in the database
        (free, _(free)),
        (premium, 'Premium'),
        (private, _(private)),
        # (archived, 'Archived')
    )
    name = models.CharField(max_length=40)
    owner = models.ForeignKey(User, related_name='bet_tags')
    is_default = models.BooleanField(default=False)
    description = models.CharField(max_length=400, null=True, default=None, blank=True)
    balance = models.FloatField(default=0)
    type = models.CharField(max_length=8, choices=type_choices, default=type_choices[0][0])
    # number_of_resets = models.PositiveIntegerField(default=0)  # update using F expression
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # have in mind that if you manually change a tb status (won -> open) you have to update also the
    # balance value

    class Meta:
        unique_together = ("name", "owner")

    def __unicode__(self):
        return "{}, ({})".format(self.name, self.balance)

    def make_default(self):
        if self.is_default:
            logger.warning("bet group %s is already the default one", self)
            return
        self.is_default = True
        self.save()
        # notice: queryset.update() doesn't call Model.save() method so your custom save method is not used.
        # In consequence pre and post save signals are also not triggered
        self.owner.bet_tags.exclude(id=self.id).update(is_default=False)

    def get_absolute_url(self):
        return reverse('bet_tagging:bet_tag_edit', kwargs={'pk': self.pk})

    def monthly_turnover(self):
        services = self.services.all()
        # logger.debug('bet_group: %s, services: %s', self, services)
        turnover = 0
        for service in services:
            turnover += service.monthly_turnover()
        # logger.debug('  turnover: %s', turnover)
        return turnover

    def get_active_subscribers(self):
        if self.type == self.premium:
            # the following queryset and the followers list must be the same since when a subscription period ends
            # the user automatically unfollows the bet_group.
            # return User.objects.filter(subscriptions__service__in=self.services).filter(
            #     subscriptions__end_date__gt=timezone.now())
            return followers(self)
        elif self.type == self.private:
            return
        elif self.type == self.free:
            return followers(self.owner)
        elif self.type == self.archived:
            logger.info('There are no subscribers for bet group %s of type: %s', self, self.type)
            return
        else:
            logger.error('Bet Group %s has invalid type %s!', self, self.type)
            return

    def get_recipients(self, in_app=False, email=False):
        """
        A user can subscribe to various types of notifications in a bet group:
        In app notifications, email notifications, sms in the future etc.
        By specifying True in the respective argument, you declare which type
        of recipients you want to get. For example:
        :param email: If True then get all users who are subscribed to email notifications for this Bet Group
        :param in_app:
        Only one argument (the first True) will be used. If non is True then email subscribers are returned
        """
        if self.type == self.private:
            # private groups have no subscribers by definition
            return
        elif self.type == self.premium:
            active_subscribers = self.get_active_subscribers()
            # the following 2 lines only necessary if active_subscribers is a list instead of queryset
            active_subscribers_ids = [user.id for user in active_subscribers]
            active_subscribers = User.objects.filter(id__in=active_subscribers_ids)
            if email:
                return active_subscribers.filter(notification_subscriptions__bet_group=self.id, notification_subscriptions__email=True)
            if in_app:
                return active_subscribers.filter(notification_subscriptions__bet_group=self.id, notification_subscriptions__in_app=True)
        elif self.type == self.free:
            if email:
                return User.objects.filter(notification_subscriptions__bet_group=self.id, notification_subscriptions__email=True)
            if in_app:
                # logger.debug('followers: %s', User.objects.filter(notification_subscriptions__bet_group=self.id))
                # logger.debug('followers with active in-app notifications: %s',
                #              User.objects.filter(notification_subscriptions__bet_group=self.id,
                #                                  notification_subscriptions__in_app=True))
                # User.objects.filter(notification_subscriptions__bet_group=self.id) are the bet group's followers
                return User.objects.filter(notification_subscriptions__bet_group=self.id, notification_subscriptions__in_app=True)
        elif self.type == self.archived:
            logger.info('There are no recipients for bet group %s of type: %s', self, self.type)
            return
        else:
            logger.error('Bet Group %s has invalid type %s!', self, self.type)
            return
        return

    def get_feed_name(self):
        """ get the feed name in which the activity will be added,
        depending on the type of bet group: public, private, premium)
        :return: Feed name or None
        """
        bet_group_type = self.type
        if bet_group_type == self.free:
            return FeedNames.user
        elif bet_group_type == self.premium:
            return FeedNames.bet_group
        elif bet_group_type == self.private:
            return FeedNames.user_private
        elif bet_group_type == self.archived:
            logger.warning('There is no feed for archived Bet Groups (invoked from %s)', self)
            return
        else:
            logger.error('Bet Group %s has invalid type %s!', self, bet_group_type)
            return

    def get_feed(self):
        """
        Each user has 2 feeds:
        * The default public user feed: Activities of free bet groups are added to this feed.
        * A private user feed: This feed is for all activities that are strictly private,
          activities that you don't want the followers of the target user to know about.
          Activities of private bet groups are added to this feed

        There is also a bet_group flat feed. Each premium bet_group has a feed similar with how each user
        has a public feed. When you subscribe to a premium bet group your timeline and aggregated timeline feeds
        follow this bet group's feed. All the activities of the public bet groups are added to the public user feed.
        When you follow a user, your feeds follow his public user feed. When you subscribe to a premium bet_group
        your feeds follow that bet_group's feed.
        :return:
        """
        bet_group_type = self.type
        if bet_group_type == self.free:
            feed_name = FeedNames.user
            actor_id = self.owner.id
        elif bet_group_type == self.premium:
            feed_name = FeedNames.bet_group
            actor_id = self.id
        elif bet_group_type == self.private:
            feed_name = FeedNames.user_private
            actor_id = self.owner.id
        elif bet_group_type == self.archived:
            logger.warning('There is no feed for archived Bet Groups (invoked from %s)', self)
            return
        else:
            logger.error('Bet Group %s has invalid type %s!', self, bet_group_type)
            return
        feed = stream_client.feed(feed_name, actor_id)
        return feed

    def add_to_session(self, request):
        session_bet_tags = request.session.get(SessionKeys.bet_tags, None)
        if not request.session.get(SessionKeys.bet_tags, None):
            bet_tag_list = list()
            bet_tag_list.append(self.id)
            request.session[SessionKeys.bet_tags] = bet_tag_list
        else:
            if self in session_bet_tags:
                logger.warning("BetTag %s that was just created is already in session", self)
            else:
                session_bet_tags.append(self.id)
                request.session[SessionKeys.bet_tags] = session_bet_tags
        return request.session[SessionKeys.bet_tags]

    def remove_from_session(self, request):
        session_bet_tags = request.session.get(SessionKeys.bet_tags, None)
        if not session_bet_tags:
            logger.warning("Can't remove BetTag %s from session, session bet_tag list is empty", self)
        else:
            if self.id not in session_bet_tags:
                logger.warning("Can't remove BetTag %s from session because it doesn't exist in session bet_tag list", self)
            else:
                session_bet_tags.remove(self.id)
        return request.session[SessionKeys.bet_tags]

    # def update_to_session(self, request):
    #     session_bet_tags = request.session.get(SessionKeys.bet_tags, None)
    #     if not request.session.get(SessionKeys.bet_tags, None):
    #         logger.warning("BetTag %s that was just edited wasn't in the session", self)
    #         bet_tag_list = list()
    #         bet_tag_list.append(self)
    #         request.session[SessionKeys.bet_tags] = bet_tag_list
    #     else:
    #         if self not in session_bet_tags:
    #             try:
    #                 old_bet_tag = BetTag.objects.get(id=self.id)
    #                 old_bet_tag.remove_from_session(request)
    #                 self.add_to_session(request)
    #             except BetTag.DoesNotExist:
    #                 logger.error("BetTag with id %s doesn't exist in the db")
    #             except BetTag.MultipleObjectsReturned:
    #                 logger.error("More than one BetTags with id %s exist in the db")
    #         else:
    #             logger.warning("A same BetTag with the just edited BetTag %s already exists in the session")
    #     return request.session[SessionKeys.bet_tags]

    @classmethod
    def from_db(cls, db, field_names, values):
        new_bet_tag = super(BetTag, cls).from_db(db, field_names, values)
        # new_bet_tag._existing_name = values[field_names.index('name')]
        # we store all the existing values to the new instance
        new_bet_tag._loaded_values = dict(zip(field_names, values))
        return new_bet_tag

    def save(self, *args, **kwargs):
        """
        If there is a name change then the user's cache is updated. The cache update can't be done
        in the pre_save signal since if the job executes before the actual save() is done, then
        the name of the selected bet group would be the old one.

        If the balance becomes < 0 this means that the user has bet without having enough balance.
        In this case a new deposit entry is automatically created with the remaining amount.
        Notice that the deposit must appear to be made before the total bet that uses it.
        """
        logger.debug("Saving Bet tag...")

        # todo race condition do the comparison with existing fields in pre save because the current solution
        # results in the issue where the database may change between when this is evaluated
        # and when the comparison is done. So it wouldn't be safe in a multiprocess environment.

        # Check if the bet_tag is going to be updated with a new name using the from_db() method
        name_update = False
        to_archived = False
        to_free = False
        to_premium = False
        from_free = False
        if not self._state.adding:  # if a bet_tag entry is going to be updated
            if self._loaded_values['name'] != self.name:  # if the existing name is different from the new one
                name_update = True

            if self._loaded_values['type'] != self.type:
                # 3 issues: subscription and followers for premium, notification_subscription for premium and free
                existing_type = self._loaded_values['type']
                new_type = self.type
                if new_type == self.archived:
                    to_archived = True
                elif new_type == self.premium:
                    to_premium = True
                elif existing_type in [self.premium, self.private]:  # new type free
                    to_free = True
                elif existing_type == self.free:
                    from_free = True
                elif existing_type == self.archived:
                    logger.warning('Archived Bet group can not reopen (invoked from %s)', self)

        # Handling the balance of the bet_tag
        old_balance = kwargs.pop('old_balance', None)
        balance_change = kwargs.pop('balance_change', None)
        initiator = kwargs.pop('initiator', None)
        calculated_deposit = None
        if self.balance < 0:  # self.balance is the new balance
            logger.warning("User %s placed a bet bigger from his balance for tag %s", self.owner, self.name)
            logger.warning("old balance: %s, new balance: %s, balance_change: %s", old_balance, self.balance, balance_change)
            if old_balance is not None and balance_change is not None:
                calculated_deposit = -(old_balance + balance_change)
            self.balance = 0

        super(BetTag, self).save(*args, **kwargs)

        if to_archived:
            to_archived_handle.delay(self.id)
        elif to_premium:
            to_premium_handle.delay(self.id)
        elif to_free:
            to_free_handle.delay(self.id)
        elif from_free:
            from_free_handle.delay(self.id)

        if name_update:
            # can't be a post save (created=False) since on balance change there is no need to update the cache
            logger.debug("bet tag %s was updated with a new name", self)
            import bet_statistics.signals  # needs to be here to avoid circular dependency issue
            user_id = self.owner.id
            bet_statistics.signals.update_user_cache.delay(user_id)

        if calculated_deposit:
            """
            """
            logger.debug("Creating a calculated deposit entry...")
            min_allowed_deposit = Deposit.min_amount
            if calculated_deposit < min_allowed_deposit:
                calculated_deposit = min_allowed_deposit
            date = initiator.date - timezone.timedelta(seconds=1)  # as if it was done 1 sec before the tb submitting
            Deposit.objects.create(user=self.owner, bet_tag=self, amount=calculated_deposit, date=date,
                                   is_calculated=True)

    def get_total_bets(self):
        total_bet_qs = games.models.TotalBet.objects.filter(bet_tag=self)
        return total_bet_qs

    def get_deposits(self):
        deposits_qs = self.deposits.all()
        return deposits_qs

    def tbs_df(self, total_bet_qs=None):
        # todo create a df class and add all df functions as methods. Add also the Bet group
        # functions that calculate df stats and add an attribute to Bet Group that is an instance
        # of that class, so that bet group stats can be calculated easily
        if not total_bet_qs:
            total_bet_qs = self.get_total_bets()

        # values = ('id', 'name', 'date', 'decision_date', 'status', 'odd', 'amount', 'total_return',
        #           'bookmaker__name', 'bet_tag__name', 'bet_tag__id', 'user__id')
        values = ('id', 'date', 'decision_date', 'status', 'odd', 'amount', 'total_return')
        tbs_df = gutils.utils.create_df(total_bet_qs, values, index='date', datetime_cols=['decision_date'])
        # logger.debug('tbs_df: %s', tbs_df)
        return tbs_df

    def deposits_df(self, deposits_qs=None):
        if not deposits_qs:
            deposits_qs = self.get_deposits()
        values = ('id', 'amount', 'date')
        df = gutils.utils.create_df(deposits_qs, values, index='date')
        # logger.debug('deposits df: %s', df)
        return df

    def deposit_amounts(self, df=None):
        if not isinstance(df, pd.DataFrame):
            df = self.deposits_df()
        if df.empty:
            return 0
        # logger.debug(df)
        total_deposits = df['amount'].sum()
        return total_deposits

    def tb_nums(self, tbs_df=None):
        if not isinstance(tbs_df, pd.DataFrame):
            tbs_df = self.tbs_df()
        if tbs_df.empty:
            return 0, 0, 0
        num_open = tbs_df.loc[tbs_df['status'] == games.models.TotalBet.open].shape[0]
        num_closed = tbs_df.loc[tbs_df['status'] != games.models.TotalBet.open].shape[0]
        num_total = tbs_df.shape[0]
        return num_total, num_open, num_closed

    def stakes(self, tbs_df=None):
        if not isinstance(tbs_df, pd.DataFrame):
            tbs_df = self.tbs_df()
        if tbs_df.empty:
            return 0, 0, 0
        open_stakes = tbs_df.loc[tbs_df['status'] == games.models.TotalBet.open]['amount'].sum()
        closed_amount = tbs_df.loc[tbs_df['status'] != games.models.TotalBet.open]['amount'].sum()
        all_stakes = tbs_df['amount'].sum()
        return all_stakes, open_stakes, closed_amount

    def return_amounts(self, tbs_df=None):
        if not isinstance(tbs_df, pd.DataFrame):
            tbs_df = self.tbs_df()
        if tbs_df.empty:
            return 0
        closed_tbs_return = tbs_df.loc[tbs_df['status'] != games.models.TotalBet.open]['total_return'].sum()
        return closed_tbs_return

    def lost_stakes(self, tbs_df=None):
        if not isinstance(tbs_df, pd.DataFrame):
            tbs_df = self.tbs_df()
        if tbs_df.empty:
            return 0
        lost_df = tbs_df.loc[tbs_df['status'] == games.models.TotalBet.lost]
        lost_stakes = lost_df['amount'].sum()
        return lost_stakes

    def pure_wins_amount(self, tbs_df=None):
        if not isinstance(tbs_df, pd.DataFrame):
            tbs_df = self.tbs_df()
        if tbs_df.empty:
            return 0
        won_df = tbs_df.loc[tbs_df['status'] == games.models.TotalBet.won]
        # No need to check for empty won_df. If it is empty the sum() returns 0
        # if won_df.empty:
        #     return None
        won_returns = won_df['total_return'].sum()
        won_stakes = won_df['amount'].sum()
        pure_wins = won_returns - won_stakes
        return pure_wins

    def odds(self, tbs_df=None):
        if not isinstance(tbs_df, pd.DataFrame):
            tbs_df = self.tbs_df()
        if tbs_df.empty:
            return 0, 0, 0
        odds_stats = tbs_df['odd'].describe()
        max_odd = odds_stats['max']
        min_odd = odds_stats['min']
        avg_odd = odds_stats['mean']
        return avg_odd, max_odd, min_odd

    def describe(self, tbs_df=None, deposits_df=None):
        # We don't check if dfs are empty since the check is done in the individual functions which return None.
        # This way we get the information that there are no tbs or no deposits in the returned data
        if not isinstance(tbs_df, pd.DataFrame):
            tbs_df = self.tbs_df()
        if not isinstance(deposits_df, pd.DataFrame):
            deposits_df = self.deposits_df()
        num_total, num_open, num_closed = self.tb_nums(tbs_df)
        all_stakes, open_stakes, closed_stakes = self.stakes(tbs_df)
        closed_tbs_return = self.return_amounts(tbs_df)
        lost_stakes = self.lost_stakes(tbs_df)
        pure_wins = self.pure_wins_amount(tbs_df)
        bank_growth = pure_wins - lost_stakes if pure_wins and lost_stakes else 0
        yield_total = bank_growth/all_stakes*100 if all_stakes and bank_growth else 0
        deposits = self.deposit_amounts(deposits_df)
        balance = bank_growth + deposits if bank_growth and deposits else 0
        roi = bank_growth/deposits if bank_growth and deposits else 0
        avg_odd, max_odd, min_odd = self.odds(tbs_df)

        deposits_stats = {
            'deposits': deposits,
            'roi': roi,
        }
        tbs_stats = {
            'num_all': num_total,
            'num_open': num_open,
            'num_closed': num_closed,
            'all_stakes': all_stakes,
            'open_stakes': open_stakes,
            'closed_stakes': closed_stakes,
            'returns': closed_tbs_return,
            'lost_stakes': lost_stakes,
            'pure_wins': pure_wins,
            'bank_growth': bank_growth,
            'yield': yield_total,
            'avg_odd': avg_odd,
            'max_odd': max_odd,
            'min_odd': min_odd,
            'balance': balance,
        }
        stats = tbs_stats.copy()  # so that tbs_stats original dict remains intact after the update() operation
        stats.update(deposits_stats)
        return stats


class Deposit(models.Model):
    """
    All deposits are made for a specific tag. If no bet tag is specified, then the default tag is used.
    """
    min_amount = 0.01
    max_amount = 999999
    # user = models.ForeignKey(User, related_name='deposits')  # user is redundant. It is contained in bet group
    bet_tag = models.ForeignKey(BetTag, related_name='deposits')
    amount = models.FloatField(validators=[MinValueValidator(min_amount), MaxValueValidator(max_amount)])
    # TODO HIGH there is no need to make a comparison between the bet_deposits and the user_deposits if
    # the calculated deposits are created. The total deposits would be the sum of the deposits table.
    # the bet_deposits would be the sum of the calculated deposits. If I gather only the not calculated
    # then the existing calculations (the comparison) would work as it did. But I need to change it.
    # Finally I chose not to allow bets without balance so no calculated or bet deposits exist
    is_calculated = models.BooleanField(default=False)  # is the deposit calculated from the bet amount
    date = models.DateTimeField()  # in order to be able to register past deposits
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "[{} on {}]: {}".format(self.bet_tag.owner, self.bet_tag, self.amount)

    def update_balance(self):
        logger.debug("updating balance...")
        bet_group = self.bet_tag
        bet_group.balance += self.amount
        bet_group.save()


class Withdrawal(models.Model):
    """
    All withdrawals are made for a specific group. If no bet group is specified, then the default one is used.
    """
    min_amount = 0.01
    # user = models.ForeignKey(User, related_name='withdrawals')
    bet_tag = models.ForeignKey(BetTag, related_name='withdrawals')
    amount = models.FloatField(validators=[MinValueValidator(min_amount)])
    is_calculated = models.BooleanField(default=False)
    date = models.DateTimeField()  # in order to be able to register past withdrawals
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "[{} on {}]: {}".format(self.bet_tag.owner, self.bet_tag, self.amount)

    def update_balance(self):
        bet_group = self.bet_tag
        bet_group.balance -= self.amount
        bet_group.save()
