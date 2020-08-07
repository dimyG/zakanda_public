# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from django.core.management.base import BaseCommand
import games.models
import bet_tagging.models


logger = logging.getLogger(__name__)


def update_offer_with_result(event, market_type, market_result_type):
    market_specific_offer, market_type_order, threshold_1, threshold_2 = market_type.get_offer_thresholds_and_order(event)
    market_result, mr_created = games.models.MarketResult.objects.get_or_create(result=market_result_type)
    if market_specific_offer.market_result != market_result:
        print('  - market result', market_specific_offer.market_result, 'for market ', market_type, 'needs to be updated')
    # market_specific_offer.market_result = market_result
    # market_specific_offer.save()
    # # logger.debug('%s offer was updated with market_result %s', market_specific_offer, market_result_type)
    # print (market_specific_offer, ' was updated with market_result: ', market_result_type)
    return market_specific_offer


class Command(BaseCommand):
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '-id',
            '--id',
            action='store',
            dest='user_id',
            help='',
        )

    def handle(self, *args, **kwargs):
        # event_ids = [96735, 96739, 96741, 96770, 96864, 96863, 96474, 96790, 96476]  # 84239 for local test
        # events = games.models.Event.objects.filter(id__in=event_ids)
        # for event in events:
        #
        #     if not event.public:
        #         event.public = True
                # event.save()

            # print ('event: ', event)
            # # logger.debug('event: %s', event)
            # market_types = event.market_types.all()
            # if market_types:
            #     # update all the offers that this event is related to, to open (open marketResult)
            #     for market_type in market_types:
            #         updated_offer = update_offer_with_result(event, market_type, games.models.MarketResult.open)

        bet_tagging.models.NotificationSubscription.initialize_existing_relationships()

        self.stdout.write('Done!\n')
