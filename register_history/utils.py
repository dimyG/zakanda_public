import logging
import boto3
import boto3.session
import xlrd
from xlrd import open_workbook
import pytz
import pytz.exceptions
from django.utils import timezone
import zakanda.settings


logger = logging.getLogger(__name__)


def get_s3_obj(bucket, filename):
    logger.info('getting object %s from s3 bucket %s ...', filename, bucket)
    session = boto3.session.Session(region_name='eu-central-1')
    client = boto3.client(
        's3',
        config=boto3.session.Config(signature_version='s3v4'),
        aws_access_key_id=zakanda.settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=zakanda.settings.AWS_SECRET_ACCESS_KEY,
        # aws_session_token=SESSION_TOKEN,
    )
    obj = client.get_object(Bucket=bucket, Key=filename)
    return obj


def read_data(obj):
    logger.info('reading object...')
    wb = open_workbook(file_contents=obj['Body'].read())  # you pass directly the bytecode (reading from stream)
    # wb = open_workbook(obj)  # it reads a local file

    sheet = wb.sheet_by_index(0)
    number_of_rows = sheet.nrows
    # number_of_columns = sheet.ncols

    rows_list = []
    for row in range(number_of_rows):
        row_values = sheet.row_values(row)  # row_values returns a python list
        rows_list.append(row_values)
    return wb, rows_list


def make_aware(naive, tz):
    try:
        # If you pass None as the is_dst flag to localize(), pytz will refuse to guess and raise
        # exceptions if you try to build ambiguous or non-existent times. (Due to DST see pytz docs)
        local_py_date = tz.localize(naive, is_dst=None)
    except pytz.exceptions.AmbiguousTimeError, pytz.exceptions.NonExistentTimeError:
        logger.error('The ambiguous/non-existent time %s was used, is_dst argument must be defined', naive)
        return None
    utc_py_date = local_py_date.astimezone(pytz.utc)
    # print(naive, local_py_date, utc_py_date)
    return utc_py_date


def parse_excel_date(cell_value, datemode, tz):
    try:
        year, month, day, hour, minute, second = xlrd.xldate_as_tuple(cell_value, datemode)
        naive_date = timezone.datetime(year, month, day, hour, minute, second)
        utc_date = make_aware(naive_date, tz)
    except Exception as e:
        logger.debug(e)
        return None
    return utc_date


def remove_empty_rows(data):
    to_remove_indexes = []
    for row_index, row in enumerate(data):  # row is a list with the values of the excel row
        if all(row_val == "" for row_val in row):
            to_remove_indexes.append(row_index)

    for index in reversed(to_remove_indexes):
        data.pop(index)


def check_validity(read_tbs):
    """
    :param read_tbs: a list of ReadTotalBet objects
    :return:
    """
    invalid_read_tbs = []
    valid_read_tbs = []
    for read_tb in read_tbs:
        is_valid = read_tb.is_valid()
        if not is_valid:
            invalid_read_tbs.append(read_tb)
        else:
            valid_read_tbs.append(read_tb)

    read_tbs_len = len(read_tbs)
    logger.info('valid read tbs: %s/%s', len(valid_read_tbs), read_tbs_len)
    logger.info('invalid read tbs: %s/%s', len(invalid_read_tbs), read_tbs_len)

    # for tb in read_tbs:
    #     logger.debug('%s %s %s %s', tb.get_utc_date(), tb.stake, tb.get_bookmaker(), tb.get_bet_group())
    #     for index, read_bet_event in enumerate(tb.read_bet_events):
    #         logger.debug('  -> %s, %s, %s, %s', read_bet_event.get_event(), read_bet_event.get_utc_date(),
    #                      read_bet_event.get_market(), read_bet_event.choice)
    #         logger.debug('  %s', tb.bet_slip_events[index])

    return valid_read_tbs, invalid_read_tbs


def create_zakanda_bet_trees(read_tbs):
    """ It will create the zakanda trees only if all the given read_tbs are valid. This in order to avoid
    issues with the balance, since the balance snapshot is calculated based on the current balance
    :param read_tbs: a list of ReadTotalBet objects
    :return:
    """
    if not read_tbs:
        return
    valid_read_tbs, invalid_read_tbs = check_validity(read_tbs)
    if invalid_read_tbs:
        logger.error('invalid read_tbs found, no zakanda bet tress will be created')
        return
    for read_tb in read_tbs:
        res = read_tb.create_zakanda_bet_tree(validate=False)  # validation check has already been made
    return True

