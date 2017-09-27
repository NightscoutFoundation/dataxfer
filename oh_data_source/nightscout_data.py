import datetime
import gzip
import hashlib
import json
import logging
import os
import random
import string
from urlparse import urlparse

import arrow
import requests

MAX_RETRIES = 4

# Set up logging.
logger = logging.getLogger(__name__)


def log_update(oh_member, update_msg):
    logger.debug(update_msg)
    oh_member.last_xfer_status = update_msg + ' ({})'.format(
        arrow.get().format())
    oh_member.save()


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


def sub_sensitive(targ_dict, subs_dict, keyval):
    """
    Sub potentially sensitive keyval in targ_dict w/random string in subs_dict
    """
    try:
        targ_dict[keyval] = subs_dict[targ_dict[keyval]]
    except KeyError:
        try:
            subs_dict[targ_dict[keyval]] = ''.join(random.choice(
                string.ascii_uppercase + string.digits) for _ in range(6))
            targ_dict[keyval] = subs_dict[targ_dict[keyval]]
        except KeyError:
            pass


def get_ns_entries(oh_member, ns_url, file_obj, before_date, after_date):
    """
    Get Nightscout entries data, ~60 days at a time.

    Retrieve ~60 days at a time until either (a) the start point is reached
    (after_date parameter) or (b) a run of 6 empty calls or (c) Jan 2010.
    """
    end = arrow.get(before_date).ceil('second').timestamp * 1000
    start = arrow.get('2010-01-01').floor('second').timestamp * 1000
    if after_date:
        start = arrow.get(after_date).floor('second').timestamp * 1000

    ns_entries_url = ns_url + '/api/v1/entries.json'

    # Start a JSON array.
    file_obj.write('[')
    initial_entry_done = False  # Entries after initial are preceded by commas.

    # Get 8 million second chunks (~ 1/4th year) until none, or start reached.
    complete = False
    curr_end = end
    curr_start = curr_end - 5000000000
    empty_run = 0
    retries = 0
    while not complete:
        if curr_start < start:
            curr_start = start
            complete = True
            logger.debug('Final round (starting date reached)...')
        log_update(oh_member, 'Querying entries from {} to {}...'.format(
            arrow.get(curr_start/1000).format(),
            arrow.get(curr_end/1000).format()))
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
        logger.debug('Retrieved {} entries...'.format(len(entries_req.json())))
        if entries_req.json():
            empty_run = 0
            for entry in entries_req.json():
                if initial_entry_done:
                    file_obj.write(',')  # JSON array separator
                else:
                    initial_entry_done = True
                json.dump(entry, file_obj)
            logger.debug('Wrote {} entries to file...'.format(len(entries_req.json())))
        else:
            empty_run += 1
            if empty_run > 6:
                logger.debug('>10 empty calls: ceasing entries queries.')
                break
        curr_end = curr_start
        curr_start = curr_end - 5000000000

    file_obj.write(']')  # End of JSON array.
    logger.debug('Done writing entries to file.')


def get_ns_devicestatus(oh_member, ns_url, file_obj, before_date, after_date):
    """
    Get Nightscout devicestatus data, 2 days at a time.

    Retrieve four days at a time until either (a) the start point is reached
    (after_date parameter) or (b) a run of 40 empty calls or (c) Oct 2014.
    """
    end = arrow.get(before_date).ceil('second')
    start = arrow.get('2014-10-01').floor('second')
    if after_date:
        start = arrow.get(after_date).floor('second')

    # Dict for consistent subs of recurring potentially sensitive strings.
    subs = dict()

    ns_entries_url = ns_url + '/api/v1/devicestatus.json'

    # Start a JSON array.
    file_obj.write('[')
    initial_entry_done = False  # Entries after initial are preceded by commas.

    # Get 8 million second chunks (~ 1/4th year) until none, or start reached.
    complete = False
    curr_end = end
    curr_start = curr_end - datetime.timedelta(days=2)
    empty_run = 0
    retries = 0
    while not complete:
        if curr_start < start:
            curr_start = start
            complete = True
            logger.debug('Final round (starting date reached)...')
        log_update(oh_member, 'Querying devicestatus from {} to {}...'.format(
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
        if devicestatus_req.json():
            empty_run = 0
            for item in devicestatus_req.json():
                sub_sensitive(item, subs, 'device')
                if initial_entry_done:
                    file_obj.write(',')  # JSON array separator
                else:
                    initial_entry_done = True
                json.dump(item, file_obj)
            logger.debug('Wrote {} devicestatus items to file...'.format(
                len(devicestatus_req.json())))
        else:
            # Quit if more than 10 empty weeks have been encountered.
            empty_run += 1
            if empty_run > 40:
                logger.debug('>10 empty weeks: ceasing devicestatus queries.')
                break
        curr_end = curr_start
        curr_start = curr_end - datetime.timedelta(days=2)

    file_obj.write(']')
    logger.debug('Done writing devicestatus items to file.')


def get_ns_treatments(oh_member, ns_url, file_obj, before_date, after_date):
    """
    Get Nightscout treatments data, 20 days at a time.

    Retrieve in chunks and write to file until (a) the start point is reached
    (after_date parameter) or (b) a run of 15 empty calls or (c) Jan 2012.
    """
    end = arrow.get(before_date).ceil('second')
    start = arrow.get('2012-01-01').floor('second')
    if after_date:
        start = arrow.get(after_date).floor('second')

    # Dict for consistent subs of recurring potentially sensitive strings.
    subs = dict()

    ns_entries_url = ns_url + '/api/v1/treatments.json'

    # Start a JSON array.
    file_obj.write('[')
    initial_entry_done = False  # Entries after initial are preceded by commas.

    # Get 8 million second chunks (~ 1/4th year) until none, or start reached.
    complete = False
    curr_end = end
    curr_start = curr_end - datetime.timedelta(days=20)
    empty_run = 0
    retries = 0
    while not complete:
        if curr_start < start:
            curr_start = start
            complete = True
            logger.debug('Final round (starting date reached)...')
        log_update(oh_member, 'Querying treatments from {} to {}...'.format(
            curr_start.isoformat(), curr_end.isoformat()))
        ns_params = {'count': 1000000}
        ns_params['find[created_at][$lte]'] = curr_end.isoformat()
        ns_params['find[created_at][$gt]'] = curr_start.isoformat()
        treatments_req = requests.get(ns_entries_url, params=ns_params)
        logger.debug('Request complete.')
        assert treatments_req.status_code == 200 or retries < MAX_RETRIES, \
            'NS treatments URL != 200 status'
        if treatments_req.status_code != 200:
            retries += 1
            logger.debug("RETRY {}: Status code is {}".format(
                retries, treatments_req.status_code))
            continue
        logger.debug('Status code 200.')
        retries = 0
        logger.debug('Retrieved {} treatments items...'.format(
            len(treatments_req.json())))
        if treatments_req.json():
            empty_run = 0
            for item in treatments_req.json():
                sub_sensitive(item, subs, 'enteredBy')
                if initial_entry_done:
                    file_obj.write(',')  # JSON array separator
                else:
                    initial_entry_done = True
                json.dump(item, file_obj)
            logger.debug('Wrote {} treatments items to file...'.format(
                len(treatments_req.json())))
        else:
            # Quit if more than 10 empty weeks have been encountered.
            empty_run += 1
            if empty_run > 15:
                logger.debug('>15 empty calls: ceasing treatments queries.')
                break
        curr_end = curr_start
        curr_start = curr_end - datetime.timedelta(days=20)

    file_obj.write(']')
    logger.debug('Done writing treatments items to file.')


def ns_data_file(oh_member, data_type, tempdir, ns_url,
                 before_date, after_date):
    """
    Retrieve data from a Nightscout URL, before and after dates.

    Return path to file and metadata, to be loaded in Open Humans.
    """
    assert data_type in ['treatments', 'profile', 'entries', 'devicestatus']

    logger.debug('Initializing {}.json.gz file...'.format(data_type))
    filepath = os.path.join(tempdir, '{}'.format(data_type) + '_' + after_date + '_to_' + before_date + '.json.gz')
    file_obj = gzip.open(filepath, 'wb')

    logger.info('Retrieving NS {} for {}...'.format(
        data_type, oh_member.oh_id))

    # A single query works for sparse data.
    if data_type == 'profile':
        oh_member.last_xfer_status = 'Retrieving profile data... ({})'.format(
            arrow.get().format())
        oh_member.save()
        ns_data_url = ns_url + '/api/v1/profile.json'
        ns_params = {'count': 1000000}
        data_req = requests.get(ns_data_url, params=ns_params)
        if data_req.json():
            json.dump(data_req.json(), file_obj)
    elif data_type == 'treatments':
        oh_member.last_xfer_status = 'Retrieving treatments data... ({})'.format(
            arrow.get().format())
        oh_member.save()
        oh_member.last_xfer_status = 'Retrieving treatment data...'
        get_ns_treatments(oh_member, ns_url, file_obj, before_date, after_date)
    elif data_type == 'entries':
        oh_member.last_xfer_status = 'Retrieving entries data... ({})'.format(
            arrow.get().format())
        oh_member.save()
        get_ns_entries(oh_member, ns_url, file_obj, before_date, after_date)
    elif data_type == 'devicestatus':
        oh_member.last_xfer_status = 'Retrieving devicestatus data... ({})'.format(
            arrow.get().format())
        oh_member.save()
        get_ns_devicestatus(oh_member, ns_url, file_obj, before_date, after_date)

    logger.debug('Closing {}.json.gz file...'.format(data_type))
    file_obj.close()

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
