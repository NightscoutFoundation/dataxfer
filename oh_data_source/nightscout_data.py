import gzip
import hashlib
import json
import logging
import os
from urlparse import urlparse

import arrow
import requests

# Set up logging.
logger = logging.getLogger(__name__)


def get_ns_entries(ns_url, before_date, after_date):
    end = arrow.get().ceil('second').timestamp * 1000
    if before_date:
        end = arrow.get(before_date).ceil('second').timestamp * 1000
    start = arrow.get('2010-01-01').floor('second').timestamp * 1000
    if after_date:
        start = arrow.get(after_date).floor('second').timestamp * 1000

    # Assume https if protocol wasn't included.
    if not ns_url.startswith('http'):
        ns_url = 'https://' + ns_url
    parsed = urlparse(ns_url)
    try:
        requests.get(ns_url)
        ns_entries_url = (parsed.scheme + '://' + parsed.netloc +
                          '/api/v1/entries.json')
    except requests.exceptions.SSLError:
        ns_entries_url = 'http://' + parsed.netloc + '/api/v1/entries.json'

    # Get 8 million second chunks (~ 1/4th year) until none, or start reached.
    complete = False
    all_entries = []
    curr_end = end
    curr_start = curr_end - 8000000000
    while not complete:
        if curr_start < start:
            curr_start = start - 1
            complete = True
            logger.debug('Final round (starting date reached)...')
        logger.debug('Querying entries from {} to {}...'.format(
            curr_start, curr_end))
        ns_params = {'count': 1000000}
        ns_params['find[date][$lte]'] = curr_end
        if after_date:
            ns_params['find[date][$gt]'] = curr_start
        entries_req = requests.get(ns_entries_url, params=ns_params)
        assert entries_req.status_code == 200, 'Nightscout URL not 200 status'
        if entries_req.json():
            all_entries = entries_req.json() + all_entries
        else:
            complete = True
            logger.debug('Final round (no entries retrieved)')
        curr_end = curr_start
        curr_start = curr_end - 8000000000
    return all_entries


def ns_entries_files(oh_member, tempdir, ns_url, before_date, after_date):
    """
    Retrieve entries data given a Nightscout URL, before and after dates.

    Return path to file and metadata, to be loaded in Open Humans.
    """

    logger.info('Retrieving Nightscout data for {}...'.format(oh_member.oh_id))

    if not before_date:
        before_date = arrow.get().format('YYYY-MM-DD')

    # Assume https if protocol wasn't included.
    if not ns_url.startswith('http'):
        ns_url = 'https://' + ns_url

    entries_data = get_ns_entries(ns_url, before_date, after_date)

    logger.debug('Creating entries.json.gz file...')
    filepath = os.path.join(tempdir, 'entries.json.gz')
    with gzip.open(filepath, 'wb') as f:
        json.dump(entries_data, f)

    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    md5_hex = md5.hexdigest()

    metadata = {
        'tags': ['json'],
        'description': 'Nightscout entries data',
        'md5': md5_hex,
        'end_date': arrow.get(before_date).format('YYYY-MM-DD'),
    }
    if after_date:
        metadata['start_date'] = arrow.get(after_date).format('YYYY-MM-DD')

    return (filepath, metadata)