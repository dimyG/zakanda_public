__author__ = 'xene'

import logging
import json
import hashlib
from functools import wraps
from django.http import HttpResponse, HttpResponseRedirect
from django.core.cache import cache     # this is the default cache
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from djpjax import pjaxtend
import zakanda.utils

logger = logging.getLogger(__name__)


def update_session(request):
    if request.method == 'POST':
        pairs = json.loads(request.POST.get('key_value_pairs', None))
        if not pairs:
            return HttpResponse(json.dumps('Session was not updated'), content_type="application/json")
        for pair in pairs:
            for variable_name, variable_value in pair.iteritems():
                added, updated = zakanda.utils.add_or_update_session(request, variable_name, variable_value)
                return HttpResponse(json.dumps('Session updated successfully'), content_type="application/json")
    return HttpResponse(json.dumps('Session was not updated'), content_type="application/json")


def misc_data(request):
    user_id = None
    if request.user.is_authenticated():
        user_id = request.user.id
    data = {"user_id": user_id}
    return HttpResponse(json.dumps(data), content_type="application/json")


def build_cache_key(function, args, kwargs):
    """ Builds keys from function name and arguments """
    caching_keys = [function.__name__]
    # logger.debug("func %s", function)
    # logger.debug("func.__name__ %s", caching_keys)
    # logger.debug("args %s", args)
    # logger.debug("kwargs %s", kwargs)

    if args is not None:
        caching_keys.extend(args)

    if kwargs is not None:
        caching_keys.extend(sorted(kwargs.iteritems()))
        # have to sort the caching keys because kwargs can be in random
        # order which screws with hashing the inputs.

    # Convert the keys to a big string and hash it
    caching_keys = map(str, caching_keys)
    cache_key = '_'.join(caching_keys)
    cache_key = hashlib.sha512(cache_key).hexdigest()

    cache_key = cache_key[:250]  # max size of caching keys in memcached
    return cache_key


def try_cache_first(timeout=300):
    """
    Tries to get the output of the function from the cache firsts. Otherwise,
    computes the function and stores the result in the cache.

    You can also pass the timeout in seconds for the cached value. By default,
    this is 5 minutes.

    Example usage, which holds the value of expensive_function in the cache for
    10 minutes:

        @try_cache_first(timeout=600)
        def expensive_function():
            <do expensive stuff>
            return result

    All results are indexed by a hash of the function name and parameters,
    so changes to function inputs should refresh the cache automatically.
    """
    def decorator(func):

        def wrapper(*args, **kwargs):

            cache_key = build_cache_key(func, args, kwargs)

            # Fetch from cache
            output = cache.get(cache_key)
            if output is None:
                output = func(*args, **kwargs)
                cache.set(cache_key, output, timeout)
            return output

        return wraps(func)(wrapper)

    return decorator


@zakanda.utils.custom_pjaxtend()
def index(request):
    # if I use the decorator to pjaxify it, then the process doesn't work properly. It redirects to the
    # profile template but this url is not processed by js and no template data are called. In normal page load it works
    if not request.user.is_authenticated():
        return TemplateResponse(request, 'gutils/index.html', {})
    # user_pk = request.user.pk
    # return HttpResponseRedirect(reverse('bet_statistics:profile_stats_template', kwargs={'user_pk': user_pk}))
    return HttpResponseRedirect(reverse('gutils:popular_raw_bevs'))


@pjaxtend()
def contact_us(request):
    return TemplateResponse(request, 'gutils/contact_us.html', {})


@pjaxtend()
def features(request):
    return TemplateResponse(request, 'gutils/features_details.html', {})
