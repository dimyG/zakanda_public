import requests
import logging
import hashlib
import settings

logger = logging.getLogger(__name__)

mqi_url = settings.MQI_URL
api_url = settings.API_URL
merchant_email = settings.PAY_TO_EMAIL
merchant_password = settings.API_PASSWORD


class MerchantQueryInterface(object):
    """ Skrill Merchant Query Interface"""

    # ERROR statuses: 401, 402, 403, 404, 405
    # example of a response: 404\t\tIllegal parameter value: 17651712043534553\n
    # content type of MQI response: text/html
    # content type of API response: text/xml
    # content type of history response: application/vnd.ms-excel;charset=UTF-8
    # api settings you need to allow specific IPs

    def __init__(self):
        self.mqi_url = mqi_url
        self.email = merchant_email
        self.password = merchant_password

    def password_hash(self):
        m = hashlib.md5()
        m.update(self.password)
        return m.hexdigest().lower()

    def post(self, **kwargs):
        """ POST parameters are encoded using Content-Type: application/x-www-form-urlencoded. """
        address = self.mqi_url
        payload = dict()
        payload["email"] = self.email
        payload["password"] = self.password_hash()
        for key, value in kwargs.iteritems():
            payload[key] = value
        # headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post(address, payload)
        logger.info("requested url: %s", r.url)
        if r.status_code != 200:
            logger.error("response's status code is %s. Response text: %s", r.status_code, r.text)
        logger.debug("response status code: %s response text: %s", r.status_code, r.text)
        extracted_status_code = self.get_response_code(r.text)
        # extracted_response_text = self.get_response_text(r.text)
        # logger.debug("extracted response status code: %s extracted response text: %s", extracted_status_code, extracted_response_text)
        return extracted_status_code

    def get_response_code(self, response_text):
        """ the response's status code is always 200 no matter what. Skrill returns the status code and the
        text as a string all together. So the status code is extracted and returned """
        try:
            status_code = response_text[:3]
            logger.debug("status code: %s", status_code)
        except Exception as e:
            logger.exception("%s", e)
            return
        return status_code

    def get_response_text(self, response_text):
        text = response_text[3:].strip('\t').strip('\n')
        logger.debug("text: %s", text)
        return text

    def status_repost(self, transaction_id, mb_transaction_id=None, status_url=None):
        """
        If no status report was posted initially, this action will return a '403 Transaction not found: TRN_ID' error
        Either trn_id or mb_trn_id must be supplied. If both are given, trn_id will be used.
        If status_url is not provided, the status_url given at the time the transaction was created will be used.
        For a successful HTTP request, the HTTP response body 200\t\tOK\n\n is returned
        (using escape sequences to represent special characters).
        If no status report was posted initially, this action will return a '403 Transaction not found: TRN_ID' error.
        :param transaction_id: Zakanda transaction ID
        :param mb_transaction_id: Skrill transaction ID
        :param status_url: Where to post the notification (not required)
        :return:
        """
        kwargs = dict()
        kwargs['action'] = "repost"
        if not transaction_id and not mb_transaction_id:
            logger.warning("transaction_id or mb_transaction_id must be given")
            return
        elif not transaction_id and mb_transaction_id:
            kwargs['mb_trn_id'] = mb_transaction_id
        elif not mb_transaction_id and transaction_id:
            kwargs['trn_id'] = transaction_id
        elif transaction_id and mb_transaction_id:
            kwargs['trn_id'] = transaction_id
            kwargs['mb_trn_id'] = mb_transaction_id
        if status_url:
            # logger.debug("status url: %s", status_url)
            kwargs['status_url'] = status_url
        return self.post(**kwargs)

    def status_view(self):
        """
        This action gives a direct response with the status of the payment. It includes the same details as in
        the 'repost' action, but sends a direct response to the request rather than to the old status URL
        """
        return self.post(action="status_trn")

    def history(self):
        return
