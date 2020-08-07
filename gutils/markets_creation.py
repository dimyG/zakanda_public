from __future__ import unicode_literals
import logging
import pytz
from django.utils import timezone
from django.db import transaction
import games.models
import zakanda.db
from zakanda.settings import Dummies

logger = logging.getLogger(__name__)


def get_dummy_source():
    try:
        dummy_source = games.models.Source.objects.get(name=Dummies.name)
    except Exception as e:
        # when the database is initially created with migrate command the code parses the get command
        # and raises exception.
        logger.warning('%s Probably the database has no zakanda schema or no data yet', e)
        dummy_source = None
    return dummy_source


def calculate_asian_handicap_thresholds(thresholds):
    if ',' in thresholds:
        threshold_1 = float(thresholds.split(',')[0])
        threshold_2 = float(thresholds.split(',')[1])
    else:
        threshold_1 = float(thresholds)
        threshold_2 = None
    return threshold_1, threshold_2


def create_asian_handicap_offer_tree(event, bookmaker_name, bookmaker_sid, source_timestamp, home, away, thresholds, source):
    threshold_1 = None
    threshold_2 = None
    if thresholds:
        threshold_1, threshold_2 = calculate_asian_handicap_thresholds(thresholds)

    asian_handicap_odd = None
    asian_handicap_offer = None
    asian_handicap_offer_odd = None
    tree_created = False
    try:
        with transaction.atomic():
            if not event or not bookmaker_name or not source_timestamp or not home or not away or not threshold_1 or not threshold_2:
                return asian_handicap_odd, asian_handicap_offer, asian_handicap_offer_odd, tree_created
            open_result, open_result_created = games.models.MarketResult.objects.get_or_create(result=games.models.MarketResult.open)
            asian_handicap_odd, asian_handicap_odd_created = games.models.AsianHandicapOdd.objects.get_or_create(home=home, away=away)

            market_name = games.models.MarketType.get_name(threshold_1, threshold_2, games.models.MarketType.generic_asian_handicap)
            asian_handicap_market = None
            if market_name:
                asian_handicap_market, asian_handicap_market_created = games.models.MarketType.objects.get_or_create(name=market_name)

            if asian_handicap_market:
                asian_handicap_offer, asian_handicap_offer_created = games.models.AsianHandicapOffer.objects.get_or_create(
                    event=event, market_result=open_result, threshold_1=threshold_1, threshold_2=threshold_2)
                asian_handicap_market.asian_handicap_offers.add(asian_handicap_offer)
                event.market_types.add(asian_handicap_market)
                bookmaker = zakanda.db.create_bookmaker_tree(bookmaker_name, source, sname=bookmaker_name, sid=bookmaker_sid)
                asian_handicap_offer_odd, asian_handicap_offer_odd_created = create_market_offer_odd(
                    games.models.AsianHandicapOfferOdd, asian_handicap_offer, asian_handicap_odd, bookmaker, source, source_timestamp)
                if asian_handicap_offer_created or asian_handicap_offer_odd_created:
                    # logger.debug("asian handicap offer tree was created successfully")
                    tree_created = True
    except Exception as e:
        logger.error("Asian Handicap Offer Tree wasn't created: Transaction rolled back", e)
        try:
            market_offer = games.models.AsianHandicapOffer.objects.get(event=event, threshold_1=threshold_1, threshold_2=threshold_2)
            logger.info("event %s already has this market offer: %s", event, market_offer)
        except Exception as e:
            logger.error("%s. Unexpected Error", e)
    return asian_handicap_odd, asian_handicap_offer, asian_handicap_offer_odd, tree_created


def create_handicap_offer_tree(event, bookmaker_name, bookmaker_sid, source_timestamp, home, draw, away, threshold, source):
    handicap_odd = None
    handicap_offer = None
    handicap_offer_odd = None
    tree_created = False
    try:
        with transaction.atomic():
            if not event or not bookmaker_name or not source_timestamp or not home or not draw or not away or not threshold:
                return handicap_odd, handicap_offer, handicap_offer_odd, tree_created

            open_result, open_result_created = games.models.MarketResult.objects.get_or_create(result=games.models.MarketResult.open)
            handicap_odd, handicap_odd_created = games.models.HandicapOdd.objects.get_or_create(home=home, draw=draw, away=away)

            market_name = games.models.MarketType.get_name(threshold, None, games.models.MarketType.generic_handicap)
            handicap_market = None
            if market_name:
                handicap_market, handicap_market_created = games.models.MarketType.objects.get_or_create(name=market_name)

            if handicap_market:
                handicap_offer, handicap_offer_created = games.models.HandicapOffer.objects.get_or_create(event=event, market_result=open_result, threshold=threshold)
                handicap_market.handicap_offers.add(handicap_offer)
                event.market_types.add(handicap_market)
                bookmaker = zakanda.db.create_bookmaker_tree(bookmaker_name, source, sname=bookmaker_name, sid=bookmaker_sid)

                handicap_offer_odd, handicap_offer_odd_created = create_market_offer_odd(
                    games.models.HandicapOfferOdd, handicap_offer, handicap_odd, bookmaker, source, source_timestamp
                )

                if handicap_offer_created or handicap_offer_odd_created:
                    # logger.debug("handicap offer tree was created successfully")
                    tree_created = True
    except Exception as e:
        logger.error("%s. Handicap Offer Tree wasn't created. Transaction rolled back", e)
        logger.error("given data are: %s %s %s %s %s %s %s %s", event, bookmaker_name, source_timestamp, home, draw, away, threshold, source)
        try:
            market_offer = games.models.HandicapOffer.objects.get(event=event, threshold=threshold)
            logger.info("event %s already has this market offer: %s", event, market_offer)
        except Exception as e:
            logger.error("%s. Unexpected Error", e)
    return handicap_odd, handicap_offer, handicap_offer_odd, tree_created


def create_double_chance_offer_tree(event, bookmaker_name, bookmaker_sid, source_timestamp, home_draw, draw_away, away_home, source):
    tree_created = False
    double_chance_odd = None
    double_chance_offer = None
    double_chance_offer_odd = None
    try:
        with transaction.atomic():
            if not event or not bookmaker_name or not source_timestamp or not home_draw or not draw_away or not away_home:
                return double_chance_odd, double_chance_offer, double_chance_offer_odd, tree_created
            open_double_chance_result, open_double_chance_result_created = games.models.MarketResult.objects.get_or_create(result=games.models.MarketResult.open)
            double_chance_odd, double_chance_odd_created = games.models.DoubleChanceOdd.objects.get_or_create(home_draw=home_draw, draw_away=draw_away, away_home=away_home)
            double_chance_market, double_chance_market_created = games.models.MarketType.objects.get_or_create(name=games.models.MarketType.double_chance_market_type)
            event.market_types.add(double_chance_market)

            double_chance_offer, double_chance_offer_created = games.models.DoubleChanceOffer.objects.get_or_create(event=event, market_result=open_double_chance_result)
            double_chance_market.double_chance_offers.add(double_chance_offer)

            bookmaker = zakanda.db.create_bookmaker_tree(bookmaker_name, source, sname=bookmaker_name, sid=bookmaker_sid)

            double_chance_offer_odd, double_chance_offer_odd_created = create_market_offer_odd(
                games.models.DoubleChanceOfferOdd, double_chance_offer, double_chance_odd, bookmaker, source, source_timestamp
            )

            if double_chance_offer_created or double_chance_offer_odd_created:
                # logger.debug("double chance offer tree was created successfully")
                tree_created = True
    except Exception as e:
        logger.error("%s. Double Chance Offer Tree wasn't created. Transaction rolled back", e)
        logger.error("given data are: %s %s %s %s %s %s %s", event, bookmaker_name, source_timestamp, home_draw, draw_away, away_home, source)
        try:
            market_offer = games.models.DoubleChanceOffer.objects.get(event=event)
            logger.info("event %s already has this market offer: %s", event, market_offer)
        except Exception as e:
            logger.error("%s. Unexpected Error", e)
    return double_chance_odd, double_chance_offer, double_chance_offer_odd, tree_created


def create_overunder_offer_tree(event, bookmaker_name, bookmaker_sid, source_timestamp, over, under, threshold, source):
    over_under_odd = None
    over_under_offer = None
    over_under_offer_odd = None
    tree_created = False
    try:
        with transaction.atomic():
            if not event or not bookmaker_name or not source_timestamp or not over or not under or not threshold:
                return over_under_odd, over_under_offer, over_under_offer_odd, tree_created
            open_result, open_result_created = games.models.MarketResult.objects.get_or_create(result=games.models.MarketResult.open)
            over_under_odd, over_under_odd_created = games.models.OverUnderOdd.objects.get_or_create(over=over, under=under)

            market_name = games.models.MarketType.get_name(threshold, None, games.models.MarketType.generic_goals_ovun)
            over_under_market = None
            if market_name:
                over_under_market, over_under_market_created = games.models.MarketType.objects.get_or_create(name=market_name)

            # We want ONE over_under_offer for each event and market_type. So if we have a new offer for the specific
            # sub-market_type (lets say for ov_un_25), we don't want to create a new over_under_offer. We just need to add
            # a new over_under_odd to the existing over_under_offer. So in this case we need to get the existing entry. We
            # can't use the get_or_create since if we have a new sub-market like ov_un_15 then we want a new over_under_offer
            # With the get_or_create the over_under_offer for the ov_un_25 would have been collected instead. This process
            # is only necessary for the markets that have "sub-markets".
            # We check if the event has already an offer for this market_type.
            # if over_under_market in event.market_types.all():
            #     print("The event has already an offer for {0}".format(over_under_market))
            #     # An over_under_offer for the specific event and the specific market_type already exists
            #     try:
            #         over_under_offer = games.models.OverUnderOffer.objects.get(event=event, market_result=open_result)
            #     except games.models.OverUnderOffer.DoesNotExist:
            #         over_under_offer = None
            #         logger.error("over_under_offer for event {0} and market_result {1} doesn't exist, but there is an over_"
            #                      "under_market {2} for this event".format(event, open_result, over_under_market))
            # else:
            #     print("The event has not yet any offer for {0}".format(over_under_market))
            #     over_under_offer = games.models.OverUnderOffer.objects.create(event=event, market_result=open_result)

            if over_under_market:
                over_under_offer, over_under_offer_created = games.models.OverUnderOffer.objects.get_or_create(event=event, market_result=open_result, threshold=threshold)
                over_under_market.over_under_offers.add(over_under_offer)
                event.market_types.add(over_under_market)
                bookmaker = zakanda.db.create_bookmaker_tree(bookmaker_name, source, sname=bookmaker_name, sid=bookmaker_sid)

                over_under_offer_odd, over_under_offer_odd_created = create_market_offer_odd(
                    games.models.OverUnderOfferOdd, over_under_offer, over_under_odd, bookmaker, source, source_timestamp
                )

                if over_under_offer_created or over_under_offer_odd_created:
                    # logger.debug("over under offer tree was created successfully")
                    tree_created = True
    except Exception as e:
        logger.error("%s. OverUnder Offer Tree wasn't created. Transaction rolled back", e)
        logger.error("given data are: %s %s %s %s %s %s %s", event, bookmaker_name, source_timestamp, over, under, threshold, source)
        try:
            market_offer = games.models.OverUnderOffer.objects.get(event=event, threshold=threshold)
            logger.info("event %s already has this market offer: %s", event, market_offer)
        except Exception as e:
            logger.error("%s. Unexpected Error", e)
    return over_under_odd, over_under_offer, over_under_offer_odd, tree_created


def create_winner_offer_tree(event, bookmaker_name, bookmaker_sid, source_timestamp, home, draw, away, source):
    """ Creates market_types, winner_offers, winner_odds, winner_offer_odds """
    try:
        with transaction.atomic():
            # event = zakanda.db.get_event_from(event_sid, source=source)
            open_winner_result, open_winner_result_created = games.models.MarketResult.objects.get_or_create(result=games.models.MarketResult.open)
            winner_odd, winner_odd_created = games.models.WinnerOdd.objects.get_or_create(home=home, draw=draw, away=away)
            winner_market, winner_market_created = games.models.MarketType.objects.get_or_create(name=games.models.MarketType.winner_market_type)
            event.market_types.add(winner_market)

            winner_offer, winner_offer_created = games.models.WinnerOffer.objects.get_or_create(event=event, market_result=open_winner_result)
            winner_market.winner_offers.add(winner_offer)

            # transaction inside transaction: If exception is raised then bookmaker
            # will be None and a new exception will be raised when it will be used so
            # the parent transaction will also roll back
            bookmaker = zakanda.db.create_bookmaker_tree(bookmaker_name, source, sname=bookmaker_name, sid=bookmaker_sid)

            winner_offer_odd, winner_offer_odd_created = create_market_offer_odd(
                games.models.WinnerOfferOdd, winner_offer, winner_odd, bookmaker, source, source_timestamp
            )
            tree_created = False
            if winner_offer_created or winner_offer_odd_created:
                # logger.debug("winner offer tree was created successfully")
                tree_created = True
    except Exception as e:
        # If the event that is related with this winner offer has been settled then the winner offer has
        # a closed market result. In this case if you make a call to get odds for this event then you will
        # get an Integrity error exception since it will try to get_or_create a winner offer with open result
        # which doesn't exist and it will try to create it. But since only one winner offer can exist for an event
        # you will get the Integrity error.
        winner_odd = None
        winner_offer = None
        winner_offer_odd = None
        tree_created = False

        logger.error("%s. transaction rolled back. Winner Offer Tree wasn't created", e)
        logger.error("given data are: %s %s %s %s %s %s %s %s", event, bookmaker_name, bookmaker_sid, source_timestamp,
                     home, draw, away, source)
        try:
            market_offer = games.models.WinnerOffer.objects.get(event=event)
            logger.info("event %s already has this market offer: %s", event, market_offer)
        except Exception as e:
            logger.error("%s. Unexpected Error", e)
    return winner_odd, winner_offer, winner_offer_odd, tree_created


def create_market_offer_odd(offer_odd_model, market_offer, market_odd, bookmaker, source, timestamp):
    """
    Create the respective market offer odd depending on the given offer odd model and assigns the dummy source to
    the created offer odd entry id the odds have been created by us (they belong to the dummy bookmaker)
    """
    # TODO you could compare with the latest entry of this bookmaker and save only if its different.
    # Have in mind the case that you have all the same but different source
    # As it is now every change in the timestamp will be a new entry even if all the other fields haven't changed

    if bookmaker.name == Dummies.name:
        # if the bookmaker to which the odds belong is the dummy bookmaker, then source of the
        # created market offer odds would also be the dummy source, so that we know that these
        # odds have been created by us
        source = games.models.Source.objects.get(name=Dummies.name)

    market_offer_odd, market_offer_odd_created = offer_odd_model.objects.get_or_create(
        offer=market_offer, odd=market_odd, bookmaker=bookmaker, source=source, timestamp=timestamp
    )

    return market_offer_odd, market_offer_odd_created


def create_initial_markets(events, source=get_dummy_source):
    """
    Creates market trees for the given events using the given source (for the entries that need a source).
    These markets would have all odds as 1.
    This happens in order to be able to show to the templates, events for which we
    haven't get odds yet (so these events have no market tree and so they are not available for selection
    by the user). So we create these initial market trees making these events selectable.
    * Creating these initial markets all events at the time of their creation would be connected to all
    markets and would be available for selection (with user defined odds). It's good practice to have existing
    initial markets for these events instead for creating then during the bet submit,
    for uniformity reasons.
    * Notice that since these market
    tree would contain dummy values for odds, we use dummy bookmaker and dummy source when needed. When to
    use the dummy source is decided implicitly in the call stack. If the bookmaker is the dummy one, then
    the dummy source will be used. The dummy bookmaker is associated with initial odds.
    The dummy bookmaker is associated with the dummy source. The marketOfferOdds are associated with
    the dummy bookmaker and dummy source.

    have in mind: about 1 hour in heroku hobby to create 65889 market offer trees for about 8000 events
    (events of a 20 day period)
    """
    # TODO NOW MAKE IT FASTER
    if not isinstance(source, games.models.Source):
        source = source()
    logger.info("creating initial markets (from source %s)...", source)
    if not source:
        return []
    markets = games.models.MarketType.objects.all()
    default_odd = 1
    market_offers = []
    for event in events:
        # sid_by_source = zakanda.db.event_sids_per_source([event], source_name=source.name)
        # event_sid = sid_by_source[event.id][source.name]
        # event = zakanda.db.get_event_from(event_sid, source=source)
        # logger.debug("event %s", event)

        if not event:
            logger.warning("event is None, initial markets were not created")
            continue
        if len(event.market_types.all()):
            # create initial markets only if the event has no markets associated with it
            logger.debug("event %s already has markets, initial markets were not created, %s, %s", event, event.created_at, event.updated_at)
            # logger.warning("sources: %s", event.event_infos.all())
            # logger.warning("markets: %s", event.market_types.all())
            continue

        timestamp = timezone.datetime(1954, 06, 07, 00, 00, 00, tzinfo=pytz.utc)  # so that it is the oldest
        bookmaker_name = Dummies.name
        market_odd, market_offer, market_offer_odd = None, None, None
        for market in markets:
            market_name, threshold_1, threshold_2 = market.get_thresholds()
            # logger.debug("%s, thresholds: %s, %s", market_name, threshold_1, threshold_2)

            if market_name == games.models.MarketType.winner_market_type:
                market_odd, market_offer, market_offer_odd, tree_created = create_winner_offer_tree(
                    event, bookmaker_name, Dummies.sid, timestamp, home=default_odd, draw=default_odd, away=default_odd, source=source)

            elif market_name.find('Goals Over Under') != -1:
                if not threshold_1:
                    logger.warning("No threshold was extracted from %s market!", market_name)
                    continue
                market_odd, market_offer, market_offer_odd, tree_created = create_overunder_offer_tree(
                    event, bookmaker_name, Dummies.sid, timestamp, over=default_odd, under=default_odd, threshold=threshold_1, source=source)

            elif market_name == games.models.MarketType.double_chance_market_type:
                market_odd, market_offer, market_offer_odd, tree_created = create_double_chance_offer_tree(
                    event, bookmaker_name, Dummies.sid, timestamp, home_draw=default_odd, draw_away=default_odd, away_home=default_odd, source=source)

            elif market_name.find("Handicap") != -1 and market_name.find("Asian") == -1:
                if not threshold_1:
                    logger.warning("No threshold was extracted from %s market!", market_name)
                    continue
                market_odd, market_offer, market_offer_odd, tree_created = create_handicap_offer_tree(
                    event, bookmaker_name, Dummies.sid, timestamp, home=default_odd, draw=default_odd, away=default_odd, threshold=threshold_1, source=source)

            # elif market_name.find("Asian Handicap") != -1:
            #     thresholds = [threshold_1, threshold_2]
            #     if None in thresholds:
            #         logger.warning("Thresholds %s were extracted from %s market!", thresholds, market_name)
            #         continue
            #     market_odd, market_offer, market_offer_odd, tree_created = create_asian_handicap_offer_tree(
            #         event, bookmaker_name, Dummies.sid, timestamp, home=default_odd, away=default_odd, thresholds=thresholds, source=source)

            else:
                logger.error('Given market_type name does not exist')

            if not market_odd:
                logger.warning("market odd for event %s doesn't exist!", event.id)
            if not market_offer:
                logger.warning("market offer for event %s doesn't exist!", event.id)
            if not market_offer_odd:
                logger.warning("market offer odd for event %s doesn't exist!", event.id)
            market_offers.append(market_offer)
    errors = market_offers.count(None)
    logger.info('%s market offers were processed, %s were created, %s are None', len(market_offers), len(market_offers)-errors, errors)
    return market_offers


def test_init_markets(request):
    import games.naming
    from django.http import HttpResponseRedirect
    from django.core.urlresolvers import reverse
    global_xmlsoccer_source_name = games.naming.source_names[0]
    global_xmlsoccer, global_created = games.models.Source.objects.get_or_create(name=global_xmlsoccer_source_name)

    dummy_source, s_created = games.models.Source.objects.get_or_create(name=Dummies.name)
    dummy_bookmaker = zakanda.db.create_bookmaker_tree(Dummies.name, dummy_source, Dummies.name, Dummies.sid)

    start_date = timezone.datetime(2016, 6, 10, tzinfo=pytz.timezone('UTC'))
    end_date = timezone.datetime(2016, 6, 12, tzinfo=pytz.timezone('UTC'))
    events = games.models.Event.filter_events(competition_gname='EURO 2016', home_team_gname=None,
                                      away_team_gname=None, season=None, start_date=start_date, end_date=end_date)
    # event_sids = zakanda.db.event_sids_per_source(events, source_name=global_xmlsoccer_source_name)
    logger.debug("%s events: %s", len(events), events)
    create_initial_markets(events, source=global_xmlsoccer)
    return HttpResponseRedirect(reverse('games:pick_bets'))