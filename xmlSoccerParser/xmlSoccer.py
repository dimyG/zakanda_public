__author__ = 'xene'

import requests
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class NoDataException(Exception):
    pass


class XmlSoccer(object):
    def __init__(self, api_key=None, use_demo=False):
        """Inits xmlsoccer class
        :param api_key: your api key
        :param use_demo: boolean whether to use the xmlsoccer demo account or not
        """
        self.api_key = api_key
        self.service_address = '''http://www.xmlsoccer.com/FootballData.asmx/'''
        self.demo_address = '''http://www.xmlsoccer.com/FootballDataDemo.asmx/'''
        self.demo = use_demo

    def set_api_key(self, api_key):
        """
        :param api_key: can set your api key here if not set via constructor
        """
        self.api_key = api_key

    def set_service_address(self, service_address):
        """
        :param service_address: can override xmlsoccer api address if required
        """
        self.service_address = service_address

    def set_demo_address(self, demo_address):
        """
        :param demo_address: can override demo api address if required
        """
        self.demo_address = demo_address

    def set_use_demo(self, use_demo):
        """
        :param use_demo: boolean whether to use xmlsoccer demo api or not
        """
        self.demo = use_demo

    def call_api(self, method=None, *args, **kwargs):
        """ Call the XMLSoccer API
        :param method: XMLSoccer function, e.g 'GetHistoricMatchesByLeagueAndSeason'
        :param args: E.g league, seasonString etc
        :param kwargs: .g league, seasonString etc
        :return: output from xmlsoccer as list of dicts
        :raise (Exception('Error: Method not passed to get_xmlsoccer')):
        """
        if method is None:
            raise(Exception('Error: Method not passed to call_api'))
        # create the url
        if not self.demo:
            address = self.service_address + method
        else:
            address = self.demo_address + method
        # create the request parameters
        params = dict()
        params['ApiKey'] = self.api_key
        for kwarg in kwargs:
            params[kwarg] = kwargs[kwarg]
        # list to store the data in
        data = []
        try:
            r = requests.get(address, params=params)    # make the request
            # logger.debug('response content: %s', r.content)
            try:
                root = etree.XML(r.text.encode('utf-8'))    # parse the xml

                if len(root) == 0:
                    # Some api info messages come directly under the root element and others under a child
                    raise(NoDataException("Root element has no children, (root el): %s" % root.text))
                # I deactivate it since I want to avoid missing a valid response with only one direct child
                # elif len(root) == 1:
                #     raise(NoDataException("Root element has one children, (%s el): %s" % (list(root)[0].tag, list(root)[0].text)))

                if method == 'GetAllOddsByFixtureMatchId':
                    # GetAllOddsByFixtureMatchId for future events has different format. The elements of interest
                    # are the grandchildren of root.
                    # TODO But for past events they are the children, I have to deal with this
                    for child in list(root):
                        if child.tag != 'AccountInformation':
                            for grandchild in list(child):
                                tmp = dict()
                                for element in list(grandchild):
                                    tmp[element.tag] = element.text
                                data.append(tmp)
                else:
                    for child in list(root):
                        if child.tag != 'AccountInformation':
                            tmp = dict()
                            for element in list(child):
                                tmp[element.tag] = element.text
                            data.append(tmp)
            except NoDataException, e:
                logger.warning(str(e))
            except Exception, e:
                # in some cases (wrong argument format) response is not in xml format
                logger.debug("request to: %s with params: %s", address, params)
                logger.debug(e)
                logger.debug("Api Response: %s", r.text)
        except Exception as e:
            logger.warning("%s. request failed", e)

        logger.info("Api response's data length: %s", len(list(data)))
        return data
