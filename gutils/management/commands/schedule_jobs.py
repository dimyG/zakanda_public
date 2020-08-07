from __future__ import unicode_literals

import logging
import data_sources.utils
import django_rq
import games.models
import games.naming
import zakanda.db
import zakanda.utils
import gutils.utils
import bet_tagging.models
import skrill.models
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import IntegrityError
from user_accounts.utils import scan_users_for_new_followers, scan_users_for_new_tb_comments, email_users_tb_comments
from user_accounts.models import UserProfile
# from django.db.models import Count
# from gutils.utils import cache_leader_board_data


logger = logging.getLogger(__name__)
used_source_name = games.naming.source_names[3]  # sportmonks
# .---------------- minute (0 - 59)
# |  .------------- hour (0 - 23)
# |  |  .---------- day of month (1 - 31)
# |  |  |  .------- month (1 - 12) OR jan,feb,mar,apr ...
# |  |  |  |  .---- day of week (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
# |  |  |  |  |
# *  *  *  *  * command to be executed


def tipster_payments():
    sellers = UserProfile.get_sellers()
    transfer_reports = []
    for seller in sellers:
        transfer_status_report = seller.profile.transfer_due_funds()
        if transfer_status_report:
            transfer_reports.append(transfer_status_report)
        else:
            if seller.profile.due_fuds():
                # if due funds are 0 nothing is return and its fine. Here we want only the cases that there are
                # due funds but haven't transfered.
                logger.error('due funds transfer to user %s failed', seller)
    if transfer_reports:
        logger.info('%s transfer requests were completed successfully', len(transfer_reports))


def email_users_for_new_followers():
    scan_users_for_new_followers()


def email_users_for_new_tb_comments(timedelta):
    commented_tbs_by_target_user_id = scan_users_for_new_tb_comments(timedelta)
    email_users_tb_comments(commented_tbs_by_target_user_id)


def get_fixtures_by_date_interval_job(timedelta, source_name, odds):
    start_date = timezone.now()
    end_date = start_date + timedelta
    logger.info("getting fixtures in time period %s - %s ...", start_date, end_date)
    events, pre_events = data_sources.utils.get_and_create_events_by_date([source_name], start_date, end_date)
    event_ids = gutils.utils.ids(events)
    if odds:
        odds, offers, offer_odds = data_sources.utils.get_and_create_odd_trees([source_name], event_ids)


def get_odds_for_events_job(timedelta, source_name):
    start_date = timezone.now()
    end_date = start_date + timedelta
    status = games.models.Event.not_started  # todo LIVE
    logger.info("getting odds for %s events in time period %s -%s ...", status, start_date, end_date)
    events = games.models.Event.objects.filter(date__gte=start_date, date__lte=end_date, status=status)
    event_ids = events.values_list("id", flat=True)
    odds, offers, offer_odds = data_sources.utils.get_and_create_odd_trees([source_name], event_ids)


def get_results_job(timedelta, source_name, betted_only=False):
    if not timedelta:
        logger.info("getting results for all events...")
        events = games.models.Event.objects.all()
    else:
        soccer_match_duration = timezone.timedelta(minutes=105)  # todo LIVE
        end_date = timezone.now() - soccer_match_duration  # we call only for matches that have probably ended
        start_date = end_date - timedelta
        logger.info("getting results for events in time period %s - %s ...", start_date, end_date)
        events = games.models.Event.objects.filter(date__range=(start_date, end_date))

    to_call_event_ids_sorted, ingredients = games.models.Event.order_for_result_call(events)

    try:
        betted_no_final_ids = ingredients[0]
        betted_final_no_ft_ids = ingredients[1]
        betted_ids = betted_no_final_ids + betted_final_no_ft_ids
        # no_betted_no_final_ids = ingredients[2]
        # no_betted_final_no_ft_ids = ingredients[3]
    except Exception as e:
        betted_ids = None

    if not betted_only:
        data_sources.utils.get_and_create_results([source_name], to_call_event_ids_sorted)
    else:
        data_sources.utils.get_and_create_results([source_name], betted_ids)


def get_leagues_and_teams(season_names=None, competition_ids='All'):
    """
    Periodically run this function for the current season, to get any new competition and its teams
    :param season_names: If None, the current season will be used
    :param competition_ids:
    """
    # xmlsoccer issue:
    # Currently if this function is called and a new competition exists if this competition is of summer
    # type then there is an issue. The current season for a summer type is different from the winter current.
    # For example:
    # date: March 2016 -> Allsverskan (summer type) current season: 2016 (16/17 xmlsoccer convention)
    # date: March 2016 -> Super League (winter type) current season: 15/16
    # But in this case, the summer comp will be created for season 15/16 if I don't check the competition_season type.
    # This is not a
    # issue in terms of user functionality, but if there is no existing Allsverskan 16/17 already then the
    # events that will be retrieved which will be assigned to the 16/17 will not be created. I leave this issue
    # open since it is related with the source. For example another source might has a get leagues for specific season
    # todo xmlsoccer: When I create competition for the current season, then I must use
    # proper current season depending on the type.
    # a way to solve this would be to check in the xmlsoccer_get_all_leagues or wherever you create the leagues
    # the type and modify the given season if the competition type is summer. But this modification must be done
    # only when the function is called with one season. Because if you give a lot of seasons then there is no need
    # to manually create another competition_season, since it will created by default.

    seasons = []
    if not season_names:
        season_names = []
        winter_season_name, summer_season_name = zakanda.utils.season_names_from_datetime(timezone.now())
        season_names.extend([winter_season_name, summer_season_name])
        winter_season = zakanda.utils.season_from_season_name(winter_season_name)
        summer_season = zakanda.utils.season_from_season_name(summer_season_name)
        seasons = [winter_season, summer_season]
        # competition_ids = zakanda.utils.competition_ids_from_season_string(winter_season_name)
    else:
        for season_name in season_names:
            season_names.append(season_name)
            season = zakanda.utils.season_from_season_name(season_name)
            seasons.append(season)

    source_names = [games.naming.default_source_name]
    football_gname = games.naming.sport_names.get('football', None)

    # seasons argument for lncs used only for xmlsoccer: Make it season_names
    data_sources.utils.get_and_create_lncs(source_names, football_gname, seasons)
    data_sources.utils.get_and_create_teams(source_names, competition_ids=competition_ids, season_names=season_names)


def test(c, d):
    logger.debug("running test job with input = %s (%s) %s (%s)...", c, type(c), d, type(d))
    if not d:
        logger.debug("d is None")
    logger.debug("done")
    # i = 0
    # for i in range(0, c*1000):
    #     i += 1
    # logger.info('test i = %s', i)


class Command(BaseCommand):
    """
    Run this command one time when you start the application (maybe with one-off dyno or something)
    """
    def handle(self, *args, **kwargs):
        # IMPORTANT: You should always use UTC datetime when working with RQ Scheduler.
        # TODO NOW check django's timezone.now() in linux

        default_scheduler = django_rq.get_scheduler('default')

        list_of_job_instances = default_scheduler.get_jobs()
        for job in list_of_job_instances:
            # cancel existing jobs (since they will be rescheduled)
            # notice that the excessive api calls that have been scheduled are canceled too
            default_scheduler.cancel(job)

        # leagues_job = scheduler.cron(
        #     # "0 2 * * 2",  # every TUE at 02:00
        #     "*/1 * * * *",
        #     func=xmlSoccerParser.views.xmlsoccer_get_all_leagues,
        #     # args=[arg1, arg2],
        #     # kwargs={'foo': 'bar'},
        #     repeat=1,
        #     queue_name='low'
        # )

        # teams_job = scheduler.cron(
        #     # xmlsoccer api needs 3600 sec between calls to the same league. So we can get the teams from all leagues
        #     # for one season at once. But for another season we must wait at least 3600 secs.
        #     # "0 5 1 * *",  # 1st day of each month at 05:00
        #     "*/1 * * * *",
        #     func=xmlSoccerParser.views.get_all_teams_by_league_and_season,
        #     # args=[arg1, arg2],
        #     kwargs={'season_names': ('15/16',), 'competition_gnames': ('Scottish Premier League',)},
        #     repeat=1,
        #     queue_name='low'
        # )

        # test_job = default_scheduler.cron(
        #     "*/1 * * * *",
        #     func=test,
        #     args=[50],
        #     kwargs={'d': None},
        #     repeat=None,
        #     queue_name='default'
        # )

        followers_job = default_scheduler.cron(
            # the hours argument must be equal with the time interval of the job
            "0 5 * * *",
            func=email_users_for_new_followers,
            timeout=60 * 60 * 3,
            repeat=None,
            queue_name='default'
        )

        tb_comments_job = default_scheduler.cron(
            # the timedelta argument must be equal with the time interval of the job
            "15 4 * * *",
            func=email_users_for_new_tb_comments,
            kwargs={'timedelta': timezone.timedelta(hours=24)},
            timeout=60 * 60 * 3,
            repeat=None,
            queue_name='default'
        )

        fixtures_job = default_scheduler.cron(
            "0 22 * * *",
            func=get_fixtures_by_date_interval_job,
            kwargs={'timedelta': timezone.timedelta(days=15), 'source_name': used_source_name, 'odds': False},
            timeout=60*60*3,
            repeat=None,
            queue_name='default'
        )

        fixtures_job_frq_01 = default_scheduler.cron(
            "0 10 * * *",
            func=get_fixtures_by_date_interval_job,
            kwargs={'timedelta': timezone.timedelta(days=7), 'source_name': used_source_name, 'odds': False},
            timeout=60 * 60 * 2,
            repeat=None,
            queue_name='default'
        )

        fixtures_job_freq_02 = default_scheduler.cron(
            "0 4,12,18 * * *",
            func=get_fixtures_by_date_interval_job,
            kwargs={'timedelta': timezone.timedelta(days=3), 'source_name': used_source_name, 'odds': False},
            timeout=60 * 60 * 2,
            repeat=None,
            queue_name='default'
        )

        odds_job_rare = default_scheduler.cron(
            "0 2 * * *",
            func=get_odds_for_events_job,
            kwargs={'timedelta': timezone.timedelta(days=7), 'source_name': used_source_name},
            timeout=60*60*3,
            repeat=None,
            queue_name='default'
        )

        odds_job_freq_01 = default_scheduler.cron(
            "0 8,20 * * *",
            func=get_odds_for_events_job,
            kwargs={'timedelta': timezone.timedelta(days=3), 'source_name': used_source_name},
            timeout=60 * 60 * 2,
            repeat=None,
            queue_name='default'
        )

        # odds_job_freq_02 = default_scheduler.cron(
        #     "0/45 * * * *",
        #     func=get_odds_for_events_job,
        #     kwargs={'timedelta': timezone.timedelta(hours=12), 'source_name': used_source_name},
        #     timeout=60*60*2,
        #     repeat=None,
        #     queue_name='default'
        # )

        odds_job_freq_03 = default_scheduler.cron(
            "*/30 * * * *",
            func=get_odds_for_events_job,
            kwargs={'timedelta': timezone.timedelta(hours=8), 'source_name': used_source_name},
            timeout=60 * 60 * 2,
            repeat=None,
            queue_name='default'
        )

        # odds_job_freq_04 = default_scheduler.cron(
        #     "*/15 * * * *",
        #     func=get_odds_for_events_job,
        #     kwargs={'timedelta': timezone.timedelta(hours=2), 'source_name': used_source_name},
        #     timeout=60 * 60 * 2,
        #     repeat=None,
        #     queue_name='default'
        # )

        results_job_freq_betted = default_scheduler.cron(
            "*/15 * * * *",
            func=get_results_job,
            kwargs={'timedelta': timezone.timedelta(hours=2), 'source_name': used_source_name, 'betted_only': True},
            timeout=60*60*2,
            repeat=None,
            queue_name='default'
        )

        results_job_freq_all = default_scheduler.cron(
            "0 */1 * * *",
            func=get_results_job,
            kwargs={'timedelta': timezone.timedelta(hours=2), 'source_name': used_source_name, 'betted_only': False},
            timeout=60 * 60 * 2,
            repeat=None,
            queue_name='default'
        )

        results_job_rare = default_scheduler.cron(
            "0 */12 * * *",
            func=get_results_job,
            kwargs={'timedelta': timezone.timedelta(hours=13), 'source_name': used_source_name, 'betted_only': False},
            timeout=60*60*2,
            repeat=None,
            queue_name='default'
        )

        results_job_wipeout = default_scheduler.cron(
            # it searches all events with no final result and makes a call. Just in case that a results job
            # has not been executed for any reason
            "0 0 * * *",
            func=get_results_job,
            kwargs={'timedelta': None, 'source_name': used_source_name, 'betted_only': False},
            timeout=60*60*2,
            repeat=None,
            queue_name='default'
        )

        # expired_subscriptions_job = default_scheduler.cron(
        #     "0 3,15 * * *",
        #     func=bet_tagging.models.Subscription.check_for_expired,
        #     timeout=60 * 60 * 2,
        #     repeat=None,
        #     queue_name='default'
        # )

        # resend_scheduled_job = default_scheduler.cron(
        #     "0 */6 * * *",
        #     func=skrill.models.TransferStatusReport.resend_scheduled,
        #     timeout=60 * 60 * 2,
        #     repeat=None,
        #     queue_name='default'
        # )
        #
        # resolve_unclaimed_job = default_scheduler.cron(
        #     "0 */12 * * *",
        #     func=skrill.models.TransferStatusReport.resolve_unclaimed,
        #     timeout=60 * 60 * 2,
        #     repeat=None,
        #     queue_name='default'
        # )
        #
        # tipster_payments_job = default_scheduler.cron(
        #     "0 1 14 * *",
        #     func=skrill.models.TransferStatusReport.resolve_unclaimed,
        #     timeout=60 * 60 * 3,
        #     repeat=None,
        #     queue_name='default'
        # )

        # # I don't cache the page since the stats of each user are updated and cached so the
        # # leaderboard calculation will be quite fast
        # leaderboard_job = scheduler.cron(
        #     # since the calc tbs df of users is cached the calculation will not be very expensive. It will not
        #     # run any calc tbs df.
        #     "0 */2 * * *",
        #     func=cache_leader_board_data,
        #     timeout=60*60*3,
        #     repeat=None,
        #     queue_name='default'
        # )

        # new_leagues_and_teams_job = scheduler.cron(
        #     # since the calc tbs df of users is cached the calculation will not be very expensive. It will not
        #     # run any calc tbs df.
        #     "0 0 */20 * *",  # every 20 days
        #     func=get_leagues_and_teams,
        #     timeout=10800,
        #     repeat=None,
        #     queue_name='default'
        # )

        self.stdout.write('Jobs have been scheduled!\n')


