import datetime
import gzip
import hashlib
import json
import logging
import os
from urlparse import urlparse

import arrow
import requests

MAX_RETRIES = 4

# Set up logging.
logger = logging.getLogger(__name__)


def normalize_url(url_input):
    """
    Return URL with scheme + netloc only, e.g. 'https://www.example.com'.

    If no scheme is specified, try https, fall back to http.
    Return None if a GET to the normalized URL doesn't return a 200 status.
    """
    if not url_input.startswith('http'):
        url_input = 'https://' + url_input
    parsed = urlparse(url_input)
    url = parsed.scheme + '://' + parsed.netloc
    try:
        test_url = requests.get(url)
    except requests.exceptions.SSLError:
        url = 'http://' + parsed.netloc
        test_url = requests.get(url)
    if test_url.status_code != 200:
        return None
    return url


def get_ns_entries(ns_url, before_date, after_date):
    """
    Get Nightscout entries data, ~90 days at a time.

    Retrieve ~90 days at a time until either (a) the start point is reached
    (after_date parameter) or (b) there are no entries returned.
    """
    end = arrow.get(before_date).ceil('second').timestamp * 1000
    start = arrow.get('2010-01-01').floor('second').timestamp * 1000
    if after_date:
        start = arrow.get(after_date).floor('second').timestamp * 1000

    ns_entries_url = ns_url + '/api/v1/entries.json'

    # Get 8 million second chunks (~ 1/4th year) until none, or start reached.
    complete = False
    all_entries = []
    curr_end = end
    curr_start = curr_end - 8000000000
    retries = 0
    while not complete:
        if curr_start < start:
            curr_start = start
            complete = True
            logger.debug('Final round (starting date reached)...')
        logger.debug('Querying entries from {} to {}...'.format(
            curr_start, curr_end))
        ns_params = {'count': 1000000}
        ns_params['find[date][$lte]'] = curr_end
        ns_params['find[date][$gt]'] = curr_start
        entries_req = requests.get(ns_entries_url, params=ns_params)
        logger.debug('Request complete.')
        assert entries_req.status_code == 200 or retries < MAX_RETRIES, \
            'NS entries URL != 200 status'
        if entries_req.status_code != 200:
            retries +=1
            logger.debug("RETRY {}: Status code is {}".format(
                retries, entries_req.status_code))
            continue
        logger.debug('Status code 200.')
        retries = 0
        if entries_req.json():
            logger.debug('Retrieved {} entries...'.format(len(entries_req.json())))
            all_entries = all_entries + entries_req.json()
        else:
            complete = True
            logger.debug('Final round (no entries retrieved)')
        curr_end = curr_start
        curr_start = curr_end - 8000000000
    return all_entries


def get_ns_devicestatus(ns_url, before_date, after_date):
    """
    Get Nightscout devicestatus data, 90 days at a time.

    Retrieve four months at a time until either (a) the start point is reached
    (after_date parameter) or (b) 2012.
    """
    end = arrow.get(before_date).ceil('second')
    start = arrow.get('2014-10-01').floor('second')
    if after_date:
        start = arrow.get(after_date).floor('second')

    ns_entries_url = ns_url + '/api/v1/devicestatus.json'

    # Get 8 million second chunks (~ 1/4th year) until none, or start reached.
    complete = False
    all_entries = []
    curr_end = end
    curr_start = curr_end - datetime.timedelta(days=90)
    retries = 0
    while not complete:
        if curr_start < start:
            curr_start = start
            complete = True
            logger.debug('Final round (starting date reached)...')
        logger.debug('Querying devicestatus from {} to {}...'.format(
            curr_start.isoformat(), curr_end.isoformat()))
        ns_params = {'count': 1000000}
        ns_params['find[created_at][$lte]'] = curr_end.isoformat()
        ns_params['find[created_at][$gt]'] = curr_start.isoformat()
        devicestatus_req = requests.get(ns_entries_url, params=ns_params)
        logger.debug('Request complete.')
        assert devicestatus_req.status_code == 200 or retries < MAX_RETRIES, \
            'NS devicestatus URL != 200 status'
        if devicestatus_req.status_code != 200:
            retries += 1
            logger.debug("RETRY {}: Status code is {}".format(
                retries, devicestatus_req.status_code))
            continue
        logger.debug('Status code 200.')
        retries = 0
        logger.debug('Retrieved {} devicestatus items...'.format(
            len(devicestatus_req.json())))
        all_entries = all_entries + devicestatus_req.json()
        curr_end = curr_start
        curr_start = curr_end - datetime.timedelta(days=90)
    return all_entries


def ns_data_file(oh_member, data_type, tempdir, ns_url,
                 before_date, after_date):
    """
    Retrieve data from a Nightscout URL, before and after dates.

    Return path to file and metadata, to be loaded in Open Humans.
    """
    assert data_type in ['treatments', 'profile', 'entries', 'devicestatus']

    logger.info('Retrieving NS {} for {}...'.format(
        data_type, oh_member.oh_id))

    # A single query works for sparse data.
    if data_type in ['treatments', 'profile']:
        ns_data_url = ns_url + '/api/v1/{}.json'.format(data_type)
        ns_params = {'count': 1000000}
        if data_type == 'treatments':
            ns_params['find[created_at][$lte]'] = arrow.get(
                before_date).ceil('second').format()
            if after_date:
                ns_params['find[created_at][$gte]'] = arrow.get(
                    after_date).floor('second').format()

        data_req = requests.get(ns_data_url, params=ns_params)
        assert data_req.status_code == 200, 'NS treatments URL != 200 status'
        data = data_req.json()

    # Custom functions to iterate through chunks for bigger data.
    elif data_type == 'entries':
        data = get_ns_entries(ns_url, before_date, after_date)
    elif data_type == 'devicestatus':
        data = get_ns_devicestatus(ns_url, before_date, after_date)

    logger.debug('Creating {}.json.gz file...'.format(data_type))
    filepath = os.path.join(tempdir, '{}.json.gz'.format(data_type))
    with gzip.open(filepath, 'wb') as f:
        json.dump(data, f)

    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    md5_hex = md5.hexdigest()

    metadata = {
        'tags': ['json'],
        'description': 'Nightscout {} data'.format(data_type),
        'md5': md5_hex,
        'end_date': arrow.get(before_date).format('YYYY-MM-DD'),
    }
    if after_date:
        metadata['start_date'] = arrow.get(after_date).format('YYYY-MM-DD')

    return (filepath, metadata)
