# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import math
from django.db.models.signals import post_save
from django.db import models, IntegrityError
from django.contrib.auth.models import User
import bet_tagging.utils
from bet_tagging.models import Subscription, GenericTransferReport
import games.models
import games.naming
import gutils.utils
import zakanda.db
import data_sources.utils
from bet_statistics.views import calc_user_total_bets_df, calculate_total_bets_stats
import gutils.views
from bet_tagging.models import Deposit, Withdrawal
from actstream.models import following
from django.core.validators import MinValueValidator
from django.db.models import F
import skrill.models
import skrill.settings
from wallet.signals import withdraw_excess_wallet_balance
from zakanda import settings
from django.utils.translation import ugettext_lazy as _
# from django.core.cache import cache  # this is the default cache


logger = logging.getLogger(__name__)


class SellerInfoBase(models.Model):
    """ If a user has both person_seller_info and legal_seller_info the legal info prevail.
    For example a user can initially be a person seller and then become a legal seller.
    """
    class Meta:
        abstract = True

    percents = (
        (40, 40),
        (50, 50),
        (60, 60),
        (70, 70),
        (80, 80),
        (90, 90),
    )

    method_skrill = 'skrill'
    payment_methods = (
        ('skrill', method_skrill)
    )

    country = models.CharField(max_length=3, choices=settings.ISO3166_A3,
                               help_text="Incorporation Country for legal entities "
                                         "or Country of Residence for physical entities")
    address = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=15, unique=True, help_text="Tax Identification Number (TIN)")
    payment_method = models.CharField(max_length=15, default=method_skrill,
                                      help_text="The payment method the tipster wants to be paid with.")
    payments_email = models.EmailField(help_text="The email the funds will be paid to. It must be connected "
                                                 "to the sellers account on the selected payment method")
    percentage_tier = models.IntegerField(choices=percents, default=70,
                                          help_text='The percent of subscriptions that goes to tipster.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LegalSellerInfo(SellerInfoBase):
    """
    Legal entities that sell tips
    info required for legal entities:
        Legal Name, Address, (Incorporation Country, Payments email)
    """
    profile = models.OneToOneField('UserProfile', related_name='legal_seller_info')
    legal_name = models.CharField(max_length=100)

    def __unicode__(self):
        return "{} {} {} {}".format(self.profile, self.tax_number, self.legal_name, self.payments_email)


class PersonSellerInfo(SellerInfoBase):
    """
    Private Persons that sell tips
    info required for physical entities:
        First Name, Last Name, Address, Tax Number, (Incorporation Country, Phone Number, Payments email)
    """
    profile = models.OneToOneField('UserProfile', related_name='person_seller_info')
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    phone_number = models.CharField(max_length=17)


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    public = models.BooleanField(default=False)
    description = models.TextField(max_length=2000, blank=True)
    wallet_balance = models.FloatField(default=0, validators=[MinValueValidator(0)])

    # TODO use a money python module
    euro = 'EUR'
    dollar = 'USD'
    currencies = (
        (euro, '€'),
        (dollar, '$'),
    )
    # currency = models.CharField(choices=currencies, max_length=3, default=euro)

    # is_premium = models.BooleanField(default=False)

    def __unicode__(self):
        return self.user.username

    def premium_bet_groups(self):
        return self.user.bet_tags.filter(type='Premium')

    def is_premium(self):
        if self.premium_bet_groups():
            return True

    def create_skrill_transfer_request(self, bnf_email=None):
        user = self.user
        funds = self.due_fuds()
        if not funds:
            return
        if not bnf_email:
            bnf_email = self.seller_info().payments_email
        user_transfer_request = skrill.models.TransferRequest.objects.create(
            # test=False,
            user=user,
            amount=funds,
            bnf_email=bnf_email
        )
        return user_transfer_request

    def create_generic_transfer_report(self, transfer_status_report):
        """ It could be triggered from the transfer_status_report creation signal. Triggered for both statuses """
        generic_transfer_report = GenericTransferReport(skrill_report=transfer_status_report)
        generic_transfer_report.save()
        # The due subscriptions are (normally) the same with the ones the due_funds was calculated from and paid by
        # this transfer so they are being connected with the transfer's report.
        for subscription in self.due_subscriptions():
            subscription.transfer_reports.add(generic_transfer_report)

    def transfer_due_funds(self):
        if not self.is_seller():
            return
        transfer_request = self.create_skrill_transfer_request()
        if not transfer_request:
            return
        transfer_status_report = transfer_request.prepare_and_execute()
        if not transfer_status_report:
            return
        self.create_generic_transfer_report(transfer_status_report)
        return transfer_status_report

    def due_subscriptions(self):
        subscriptions = []
        for subscription in Subscription.objects.filter(service__bet_group__owner=self.user):
            if not subscription.is_fully_paid():
                subscriptions.append(subscription)
        return subscriptions
        # return Subscription.objects.filter(service__bet_group__owner=self.user).filter(fully_paid=False)

    def due_fuds(self):
        logger.debug('calculating due funds for user: %s...', self)
        if not self.is_seller():
            return 0.0
        try:
            turnover = self.monthly_turnover()
            if not turnover:
                return 0.0
            tier = float(self.seller_info().percentage_tier/100.0)
            due_funds = turnover * tier
            skrill_fees = skrill.settings.skrill_to_skrill_fees(due_funds)
            due_funds = due_funds - skrill_fees
            due_funds = math.floor(due_funds*10)/10
            logger.info('due funds for user %s is %s [%s of %s]', self, due_funds, tier, turnover)
            return due_funds
        except Exception as e:
            logger.exception('%s', e)
            return 0.0

    def monthly_turnover(self):
        bet_groups = self.user.bet_tags.all()
        turnover = 0
        for bet_group in bet_groups:
            turnover += bet_group.monthly_turnover()
        # logger.debug('monthly turnover for user %s is %s', self, turnover)
        return turnover

    @classmethod
    def get_sellers(cls):
        sellers = User.objects.filter(
            models.Q(profile__legal_seller_info__isnull=False) | models.Q(profile__person_seller_info__isnull=False)
        )
        return sellers

    def seller_info(self):
        try:
            legal_seller_info = self.legal_seller_info
            return legal_seller_info
        except Exception as e:
            try:
                person_seller_info = self.person_seller_info
                return person_seller_info
            except Exception as e:
                logger.debug("%s", e)

    def is_seller(self):
        try:
            legal_seller_info = self.legal_seller_info
            return True
        except Exception as e:
            try:
                person_seller_info = self.person_seller_info
                return True
            except Exception as e:
                logger.debug("%s", e)

    def is_legal_seller(self):
        try:
            legal_seller_info = self.legal_seller_info
            return legal_seller_info
        except Exception as e:
            logger.debug("%s", e)

    def is_person_seller(self):
        try:
            person_seller_info = self.person_seller_info
            return person_seller_info
        except Exception as e:
            logger.debug("%s", e)

    # def has_perm(self, perm, obj=None):
    #     """Does the user have a specific permission?"""
    #     # Simplest possible answer: Yes, always
    #     return True

    def get_tips(self):
        tipsters = following(self.user, User)
        if not tipsters:
            return
        tip_tbs = games.models.TotalBet.objects.filter(status=games.models.TotalBet.open).filter(user__in=tipsters). \
            select_related('user', 'bookmaker', 'bet_tag'). \
            prefetch_related('bets__bet_events', 'bets__bet_events__selection', 'bets__bet_events__market_type',
                             'bets__bet_events__event__home_team', 'bets__bet_events__event__away_team',
                             'bets__bet_events__event__competition_season__competition',
                             'bets__bet_events__event__competition_season__season', 'bets__bet_events__event__results',
                             'bets__bet_events__event__competition_season__competition__country')
        return tip_tbs

    def is_subscribed(self, bet_group):
        active_subscribers = bet_group.get_active_subscribers()
        if active_subscribers and self.user in active_subscribers:
            return True

    # ############ wallet stuff START ############

    def deposit_to_wallet(self, status_report):
        logger.info("depositing to wallet %s %s", self, status_report)
        amount = float(status_report.mb_amount)
        self.wallet_balance = F('wallet_balance') + amount
        self.save()

    def withdraw_from_wallet(self, transfer_status_report):
        logger.info("withdrawing from wallet %s %s", self, transfer_status_report)
        amount = float(transfer_status_report.mb_amount)
        new_balance = self.wallet_balance - amount
        if new_balance < 0:
            logger.error('Negative wallet balance!')
            excess_amount = self.wallet_balance - amount
            withdraw_excess_wallet_balance.send(sender=self, instance=transfer_status_report,
                                                withdraw_amount=amount, excess_amount=excess_amount)
        self.wallet_balance = F('wallet_balance') - amount
        self.save()

    def spend_from_wallet(self, status_report):
        logger.info("spending from wallet %s %s", self, status_report)
        amount = float(status_report.mb_amount)
        new_balance = self.wallet_balance - amount
        if new_balance < 0:
            logger.error('Negative wallet balance!')
            excess_amount = self.wallet_balance - amount
            withdraw_excess_wallet_balance.send(sender=self, instance=status_report,
                                                withdraw_amount=amount, excess_amount=excess_amount)
        self.wallet_balance = F('wallet_balance') - amount
        self.save()

    def reported_payment_requests(self, status=None, valid=True):
        payment_reports = skrill.models.StatusReport.objects.filter(payment_request__user=self.user).filter(valid=valid)
        if status:
            payment_reports = payment_reports.filter(status=status)
        payment_requests = skrill.models.PaymentRequest.objects.filter(statusreport__in=payment_reports)
        return payment_requests

    def reported_transfer_requests(self, status=None, claimed=None):
        transfer_reports = skrill.models.TransferStatusReport.objects.filter(transfer_request__user=self.user)
        if status:
            transfer_reports = transfer_reports.filter(status=status)
        if claimed:
            transfer_reports = transfer_reports.filter(claimed=claimed)
        transfer_requests = skrill.models.TransferRequest.objects.filter(transferstatusreport__in=transfer_reports)
        return transfer_requests

    def get_wallet_deposits(self):
        return self.reported_payment_requests(status=2, valid=True)

    def get_wallet_withdrawals(self):
        """ In the no zakanda wallet context the withdrawals are the payments made to tipsters from zakanda"""
        return self.reported_transfer_requests(claimed=True)

    def get_wallet_chargebacks(self):
        return self.reported_payment_requests(status=-3, valid=True)

    def get_wallet_spending(self):
        """ zakanda would not implement user wallet. Users would buy a service directly, so every deposit
        is instantly an expense. """
        # deposits amount should be equal to the sum of the subscription amounts
        return self.get_wallet_deposits()

    def wallet_history(self):
        """ return all wallet actions, ordered by date """
        wallet_payments = self.reported_payment_requests(status=None, valid=True)  # not only the processed
        wallet_expenses = self.get_wallet_spending()
        wallet_withdraws = self.get_wallet_withdrawals()
        # make one ordered list of wallet history action objects
        latest = list(wallet_payments) + list(wallet_withdraws) + list(wallet_expenses)
        latest_sorted = sorted(latest, key=lambda x: x.created_at, reverse=True)
        # logger.debug('dates: %s', latest_sorted)
        return latest_sorted

    def calc_wallet_balance(self):
        # withdraws are the transfers made from zakanda to the tipster
        deposits = self.get_wallet_deposits()
        spending = self.get_wallet_spending()
        charge_backs = self.get_wallet_chargebacks()
        withdraws = self.get_wallet_withdrawals()

        deposits_amount = self.amount_from_qs(deposits)
        spending_amount = self.amount_from_qs(spending)
        due_funds_amount = self.due_fuds()
        withdraws_amount = self.amount_from_qs(withdraws)
        charge_backs_amount = self.amount_from_qs(charge_backs)
        wallet_balance = deposits_amount + due_funds_amount - withdraws_amount - charge_backs_amount - spending_amount
        return wallet_balance

    @classmethod
    def amount_from_qs(cls, queryset):
        """
        :param queryset: a queryset of any Model that has an "amount" field (for example PaymentRequest)
        :return: the sum of amounts of the given queryset
        """
        if not queryset:
            return 0
        amounts = queryset.values_list('amount', flat=True)
        overall_amount = float(sum(amounts))
        return overall_amount

    # ############ wallet stuff END ############

    def deposits(self):
        deposits = Deposit.objects.filter(bet_tag__owner=self.user)
        return deposits

    def withdrawals(self):
        withdrawals = Withdrawal.objects.filter(bet_tag__owner=self.user)
        return withdrawals

    def distinct_bet_events(self, exclude_open=False):
        """
        user_bets = games.models.Bet.objects.filter(totalbet__user=user)
        Collects the bets from the bet_totalbet intermediate table. So it collects all totalbets of the user and takes the
        bets that are related with these totalbets. One bet can be related with many total_bets of the user. In this case
        this bet will appear in the list more than one time.

        user_bet_events = games.models.BetEvent.objects.filter(bet__in=user_bets)
        Collects the bet_events from the bet_event_bet intermediate table. One bet_event can be related with many bets
        of the same user. In this case this bet_event will appear in the list more than one time.

        If what we want is to get the distinct bet_events of a user, then we can get only the distinct bets and
        then get the distinct bet_events from them.
        """
        # TODO BET SYSTEMS check if the user_bets are collected properly (for statistics calculations)
        user_bets = games.models.Bet.objects.filter(totalbet__user=self.user).distinct()
        user_bet_events = games.models.BetEvent.objects.filter(bet__in=user_bets).distinct()
        if exclude_open:
            user_bet_events = user_bet_events.exclude(selection__status=games.models.Selection.open)
        return user_bet_events

    def settle_related_bets_and_tbs(self, bet_events):
        """
        some bet_events are already closed and we want to settle the related bets and total bets.
        This is useful for settling past tbs that have been connected to closed bet events
        :param bet_events: these must be closed in order for the related bets and tbs to be settled
        """

        bets = games.models.Bet.objects.filter(bet_events__in=bet_events)
        logger.debug("bets collected to be settled: %s", len(bets))
        lost_bets, won_bets, open_bets = games.models.Bet.settle_bets(bets)
        # closed_bets = lost_bets + won_bets
        total_bets = self.user.total_bets.filter(bets__in=bets).filter(status=games.models.TotalBet.open)
        logger.debug("total_bets collected to be settled :%s", len(total_bets))
        closed_total_bets, open_total_bets, changed_total_bets = games.models.TotalBet.settle_total_bets(total_bets)
        return closed_total_bets, open_total_bets, changed_total_bets

    def settle_total_bets(self, call_api=False):
        """ The concept is that the events are settled (even if they have already been settled) since these
        events might be related with some new unsettled bet_events and these bet_events are settled
        during the event settlement process. You can't (?) settle the bet_events directly since there are
        some actions that might be done during the event settlement like market_offer settlement? (check it)

        ??? The void events are separated in those that are
        connected with closed (void bevs) and those with new open bevs. The tbs of the closed ones must be manually
        settled. The open ones are settled by the api call ??? Is this solved by the event.settle_tree ?
        """
        bet_events = self.distinct_bet_events(exclude_open=False)
        events = games.models.Event.objects.filter(bet_events__in=bet_events).distinct()
        events = events.order_by("bet_events")

        ndr_events, dr_events = zakanda.db.split_decision_no_decision_events(events)
        logger.debug("events with no decision result: %s", ndr_events)
        # logger.debug("events with decision result: %s", dr_events)

        games.models.Event.settle_trees(dr_events, update_cache=False)

        if call_api:
            source_names = [games.naming.default_source_name]
            ndr_event_ids = gutils.utils.ids(ndr_events)
            data_sources.utils.get_and_create_results(source_names, ndr_event_ids)

    def get_tbs_df(self, exclude_open=False, start_date=None, end_date=None):
        user_id = self.user.id
        user_tbs, user_tbs_df = calc_user_total_bets_df(
            user_id, exclude_open=exclude_open, start_date=start_date, end_date=end_date)
        return user_tbs, user_tbs_df

    def calc_stats(self, user_tbs_df=None, exclude_open=False, start_date=None, end_date=None):
        """ The calculated stats do not depend on the type of tbs_df (normalized or absolute)
        no matter the type the stats would be the same. In this case the absolute is used """
        if not user_tbs_df:
            user_tbs, user_tbs_df = self.get_tbs_df(exclude_open=exclude_open, start_date=start_date, end_date=end_date)
        user_id = self.user.id
        stats = calculate_total_bets_stats(user_tbs_df, user_id)
        return stats

    # the approach of caching an aggregated dictionary for all users stats was replaced by a database table
    # @classmethod
    # @gutils.views.try_cache_first(timeout=60 * 60 * 24 * 7)
    # def users_stats(cls):
    #     """ returns a dictionary mapping user ids with their stats. This way you can make only one cache call
    #     to get the given users stats instead of looping through users and making one cache call for each.
    #     It needs to be updated whenever a user's cache is updated """
    #     # users = User.objects.filter(id__in=user_ids)
    #     from user_accounts.views import Leaderboard
    #     users = Leaderboard.get_users()
    #     # users = User.objects.all()
    #     stats = {}
    #     for user in users:
    #         user_stats = user.profile.calc_stats(exclude_open=False, start_date=None, end_date=None)
    #         # user.stats = stats
    #         stats[user.id] = user_stats
    #     return stats

    # @classmethod
    # def update_user_in_stats(cls, user_id):
    #     # untested
    #     user = User.objects.get(id=user_id)
    #     user_stats = user.profile.calc_stats()
    #     stats = cls.users_stats()
    #     stats[user.id] = user_stats
    #     func_key = gutils.views.build_cache_key(cls.users_stats, (), {})
    #     cache.set(func_key, stats)
    #     return user_stats

    # @classmethod
    # def users_stats_clear_cache(cls):
    #     # untested
    #     logger.debug("clearing users_stats cache...")
    #     args = ()
    #     kwargs = {}
    #     func_key = gutils.views.build_cache_key(cls.users_stats, args, kwargs)
    #     delete = cache.delete(func_key)
    #     logger.debug("users_stats cache delete: %s", delete)


@gutils.utils.disable_for_loaddata
def user_post_save(sender, instance, created, *args, **kwargs):
    if created:
        new_profile, profile_created = UserProfile.objects.get_or_create(user=instance)
        basic_stats, created = BasicStats.objects.get_or_create(user=instance)
        default_bet_tag = bet_tagging.utils.create_default_bet_tag(instance)

        # logger.debug('profile %s, created = %s', new_profile, profile_created)
        # notify.send(instance,
        #             recipient=MyUser.objects.get(username='jmitchel3'), #admin user
        #             verb='New user created.')
        # merchant account customer id -- stripe vs braintree
        # send email for verifying user email


post_save.connect(user_post_save, sender=User)


class BasicStats(models.Model):
    """ Redundant information used for easier handling and presentation purposes.
     It must be the current picture of a player's performance updated in each user's action """
    user = models.OneToOneField(User, related_name='basic_stats')
    score = models.FloatField(default=0, null=True)
    bet_yield = models.FloatField(default=0, null=True)
    roi = models.FloatField(default=0, null=True)
    num_bets = models.PositiveIntegerField(default=0, null=True)
    num_opens = models.PositiveIntegerField(default=0, null=True)
    num_wins = models.PositiveIntegerField(default=0, null=True)
    num_losses = models.PositiveIntegerField(default=0, null=True)
    num_bet_groups = models.PositiveIntegerField(default=1, null=True)
    num_followers = models.PositiveIntegerField(default=0, null=True)
    num_following = models.PositiveIntegerField(default=0, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '[{}] score: {} yield: {} roi: {}'.format(self.user, self.score, self.bet_yield, self.roi)

    def update(self, stats=None):
        if not stats:
            stats = self.user.profile.calc_stats()
        self.score = stats.get('score')
        self.bet_yield = stats.get('total_yield')
        self.roi = stats.get('roi')
        self.num_bets = stats.get('num_total_bets')
        self.num_opens = stats.get('open_total_bets')
        self.num_wins = stats.get('won_total_bets')
        self.num_losses = stats.get('lost_total_bets')
        self.num_bet_groups = stats.get('num_bet_tags')
        self.save()
