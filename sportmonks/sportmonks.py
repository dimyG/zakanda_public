from __future__ import unicode_literals
import logging
import requests
import json
import zakanda.settings


logger = logging.getLogger(__name__)
api_key = zakanda.settings.sportmonks_api_key
api_url = 'https://soccer.sportmonks.com/api/v2.0/'


class Client(object):
    def __init__(self, main_endpoint=None):
        self._api_key = api_key
        self._api_url = api_url
        self._separator = '/'
        self.main_endpoint = main_endpoint
        self.date_format = None

    def make_endpoint(self, *children_endpoints):
        endpoint = self.main_endpoint
        for child_endpoint in children_endpoints:
            endpoint += self._separator + str(child_endpoint)
        return endpoint

    def reform_date(self, datetime_object, date_format=None):
        if not date_format:
            date_format = self.date_format
        try:
            return datetime_object.strftime(date_format)
        except Exception as e:
            # You can pass the expected string directly. The function will return it
            logger.debug('%s', e)
            return datetime_object

    def get(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return: data is a list of the combined paginated data, meta is a dict and is the meta data of the first page
        """
        endpoint = self.make_endpoint(*args)
        logger.info("endpoint: %s", endpoint)
        if not endpoint:
            logger.warning('no endpoint was given, call can not be made')
            return None, None, None

        address = self._api_url + endpoint
        payload = dict()
        payload['api_token'] = self._api_key
        for key, value in kwargs.iteritems():
            # if value is a list, requests will handle it properly
            payload[key] = value
        try:
            r = requests.get(address, payload)
            logger.info("requested url: %s", r.url)
            if r.status_code != 200:
                logger.error("response's status code is %s. Response text: %s", r.status_code, r.text)
                return None, None, r.status_code
            # logger.debug('response status code: %s, text: %s, encoding: %s', r.status_code, r.text, r.encoding)
            # The gzip and deflate transfer-encodings are automatically decoded by requests (it sets the proper
            # request headers to let the server know that it accepts these encodings)
            total_data = r.json()
            # with open('../sportmonks/response_texts/{}_total_data.txt'.format(self.__class__.__name__), 'w') as outfile:
            #     json.dump(total_data, outfile, indent=4)
            # logger.debug("total data: %s", total_data)
            meta = total_data.get('meta')
            meta_list = [meta]
            data = total_data.get('data')
            pagination = meta.get('pagination')
            if not pagination:
                return data, meta, r.status_code
            # total_entities = pagination.get('total')
            total_pages = pagination.get('total_pages')
            current_page = pagination.get('current_page')
            logger.info("total pages: %s", total_pages)
            for page in range(current_page+1, total_pages+1):
                payload['page'] = page
                pr = requests.get(address, payload)
                logger.debug('next requested url: %s', pr.url)
                if pr.status_code != 200:
                    logger.warning("response's status code is %s. Response text: %s", pr.status_code, pr.text)
                    next_data, next_meta = None, None
                else:
                    next_total_data = pr.json()
                    # with open('../sportmonks/response_texts/{}_total_data.txt'.format(self.__class__.__name__), 'a') as outfile:
                    #     json.dump(next_total_data, outfile, indent=4)
                    next_data = next_total_data.get('data')
                    next_meta = next_total_data.get('meta')
                if next_data:
                    data.extend(next_data)
                meta_list.append(next_meta)
            return data, meta, r.status_code  # Notice that only the status code of the initial call is returned
        except Exception as e:
            logger.warning('%s', e)
            return None, None, None


class Continents(Client):
    def __init__(self):
        super(Continents, self).__init__(main_endpoint='continents')

    def all(self, **params):
        return self.get(**params)

    def by_id(self, id, **params):
        children_endpoints = [id]
        return self.get(*children_endpoints, **params)


class Countries(Client):
    def __init__(self):
        super(Countries, self).__init__(main_endpoint='countries')

    def all(self, **params):
        return self.get(**params)

    def by_id(self, id, **params):
        children_endpoints = [id]
        return self.get(*children_endpoints, **params)


class Leagues(Client):
    def __init__(self):
        super(Leagues, self).__init__(main_endpoint='leagues')

    def all(self, **params):
        return self.get(**params)

    def by_id(self, id, **params):
        children_endpoints = [id]
        return self.get(*children_endpoints, **params)


class Seasons(Client):
    """ Seasons in sportmonks are not distinct. There are many "16/17" seasons each one connected
    with a specific league. There is the "16/17" season with id 100 for "premier league"
    and another one "16/17" with id 200 connected with "championship". They are like zakanda CompetitionSeasons """
    def __init__(self):
        super(Seasons, self).__init__(main_endpoint='seasons')

    def all(self, **params):
        return self.get(**params)

    def by_id(self, id, **params):
        children_endpoints = [id]
        return self.get(*children_endpoints, **params)


class Teams(Client):
    def __init__(self):
        super(Teams, self).__init__(main_endpoint='teams')

    def by_id(self, id, **params):
        children_endpoints = [id]
        return self.get(*children_endpoints, **params)

    def by_season(self, id, **params):
        children_endpoints = ['season', id]
        return self.get(*children_endpoints, **params)


class Fixtures(Client):
    def __init__(self):
        super(Fixtures, self).__init__(main_endpoint='fixtures')
        self.date_format = '%Y-%m-%d'

    def by_date_range(self, start_date, end_date, **params):
        start_date = self.reform_date(start_date)
        end_date = self.reform_date(end_date)
        children_endpoints = ['between', start_date, end_date]
        return self.get(*children_endpoints, **params)

    def by_exact_date(self, date, **params):
        date = self.reform_date(date)
        children_endpoints = ['date', date]
        return self.get(*children_endpoints, **params)

    def by_id(self, id, **params):
        children_endpoints = [id]
        return self.get(*children_endpoints, **params)


class Odds(Client):
    def __init__(self):
        super(Odds, self).__init__(main_endpoint='odds')

    def by_fixture_id(self, sid, **params):
        children_endpoints = ['fixture', sid]
        return self.get(*children_endpoints, **params)


class Rounds(Client):
    def __init__(self):
        super(Rounds, self).__init__(main_endpoint='rounds')

    def by_season_id(self, sid, **params):
        children_endpoints = ['season', sid]
        return self.get(*children_endpoints, **params)


class Bookmakers(Client):
    def __init__(self):
        super(Bookmakers, self).__init__(main_endpoint="bookmakers")

    def all(self, **params):
        return self.get(**params)

    def by_id(self, id, **params):
        children_endpoints = [id]
        return self.get(*children_endpoints, **params)


continents = Continents()
countries = Countries()
leagues = Leagues()
seasons = Seasons()
teams = Teams()
fixtures = Fixtures()
odds = Odds()
rounds = Rounds()
bookmakers = Bookmakers()
