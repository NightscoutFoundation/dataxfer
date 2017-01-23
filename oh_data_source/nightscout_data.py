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


def get_ns_entries(oh_member, tempdir, ns_url, before_date, after_date):
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

    parsed = urlparse(ns_url)

    ns_entries_url = (parsed.scheme + '://' + parsed.netloc +
                      '/api/v1/entries.json')
    ns_params = {'count': 1000000}
    ns_params['find[date][$lte]'] = arrow.get(
        before_date).ceil('second').timestamp * 1000
    if after_date:
        ns_params['find[date][$gte]'] = arrow.get(
            after_date).floor('second').timestamp * 1000

    try:
        entries_req = requests.get(ns_entries_url, params=ns_params)
    except requests.exceptions.SSLError:
        # Fall back to http if https didn't work.
        ns_entries_url = 'http://' + parsed.netloc + '/api/v1/entries.json'
        entries_req = requests.get(ns_entries_url, params=ns_params)

    logger.debug('Got entries data for {}, status code: {}'.format(
        oh_member.oh_id, entries_req.status_code))
    logger.info('Got {} entries for {} to {}'.format(
        len(entries_req.json()), after_date, before_date))

    entries_data = entries_req.json()
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
