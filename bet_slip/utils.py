from __future__ import unicode_literals
__author__ = 'xene'

from django.db.models import Count
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


max_num_events = 14


def get_exact_m2m_match(model_class, m2m_field, m2m_instances):
    """
    It is used to get any bets that might be related with the given bet_events
    :param model_class:
    :param m2m_field:
    :param m2m_instances:
    :return: a queryset with the model_class instances which are related only with the m2m_instances
    """
    logger.debug("getting all %s entities connected with the exact given %s...", model_class, m2m_field)
    query = model_class.objects.annotate(count=Count(m2m_field))\
        .filter(count=len(m2m_instances))
    if query:
        ids = (m2m_instance.id for m2m_instance in m2m_instances)
        for _id in ids:
            query = query.filter(**{m2m_field: _id})
    # logger.debug("bets_with_same_bet_events: %s", query)
    return query


def get_instance(model_class, query, **kwargs):
    """
    It is used to get THE bet, out of a bets queryset, which satisfies the given filters
    :param model_class:
    :param query:
    :param kwargs: The fields to be used to filter the queryset
    :return: The matched instance or None
    """
    if not query:
        return None
    try:
        logger.debug("getting The bet that has fields %s, same with the placed bet...", kwargs)
        instance = query.get(**kwargs)
        logger.debug("identical %s found and will be used '%s'", model_class, instance)
        return instance
    except model_class.DoesNotExist:
        logger.debug('new %s instance will be created...', model_class)
    except model_class.MultipleObjectsReturned:
        logger.error('many %s entries with exactly the same bet_events and %s found', model_class, kwargs)
        # # This is for user convenience. We save the tb with the first matched bet. Then we have to manually fix this
        # instance = query.filter(**kwargs).first()
        # return instance
        # # This will roll back the total bet tree transaction
        raise IntegrityError('many %s entries with exactly the same bet_events and %s found' % (model_class, kwargs))


class BetEventsDontExist(Exception):
    pass