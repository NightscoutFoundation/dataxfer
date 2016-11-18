import cStringIO
import gzip
import hashlib
import json

import arrow
import requests

OH_BASE = 'https://www.openhumans.org'
OH_EXCHANGE_TOKEN = OH_BASE + '/api/direct-sharing/project/exchange-member/'
OH_DELETE_FILES = OH_BASE + '/api/direct-sharing/project/files/delete/'
OH_UPLOAD = OH_BASE + '/api/direct-sharing/project/files/upload/'


def exchange_token_for_id(token, logger=None):
    """
    Exchange OAuth2 token for member data, return project member ID.
    """
    req = requests.get(
        OH_EXCHANGE_TOKEN,
        params={'access_token': token})
    oh_id = req.json()['project_member_id']
    if logger:
        logger.debug("Token '{}' exchanged for project member ID '{}'".format(
            token, oh_id))
    return oh_id


def delete_all_oh_files(token, project_member_id, logger=None):
    """
    Delete all current project files in Open Humans for this project member.
    """
    # Delete all current Nightscout files in Open Humans.
    req = requests.post(
        OH_DELETE_FILES,
        params={'access_token': token},
        data={'project_member_id': project_member_id,
              'all_files': True})
    if logger:
        logger.debug("Files deleted. Status code: {}".format(req.status_code))


def get_nightscout_entries(ns_url, before_date, after_date, logger=None):
    if not ns_url.startswith('http'):
        ns_url = 'https://' + ns_url
    logger.info("Retrieving Nightscout data from {}...".format(ns_url))
    ns_entries_url = ns_url + '/api/v1/entries.json'
    ns_params = {'count': 1000000}
    ns_params['find[date][$lte]'] = arrow.get(
        before_date).ceil('second').timestamp * 1000
    if after_date:
        ns_params['find[date][$gte]'] = arrow.get(
            after_date).floor('second').timestamp * 1000
    entries_req = requests.get(ns_entries_url, params=ns_params)
    logger.info(entries_req.url)
    logger.info("Got {} entries for {} to {}".format(
        len(entries_req.json()), after_date, before_date))
    return entries_req.json()


def prepare_json_gz_fileobj(filename, data, tags, description, logger=None):
    entries_file = cStringIO.StringIO()
    gzip_obj = gzip.GzipFile(filename=filename, mode='wb',
                             fileobj=entries_file)
    gzip_obj.write(json.dumps(data))
    gzip_obj.close()
    entries_file.seek(0)
    md5 = hashlib.md5()
    md5.update(entries_file.read())
    md5_hex = md5.hexdigest()
    entries_file.seek(0)
    metadata = {
        "tags": tags,
        "description": description,
        'md5': md5_hex,
    }
    return entries_file, metadata


def ns_to_oh(token, before_date, after_date, ns_url, logger):
    """
    Retrieve specified Nightscout data and upload to Open Humans.
    """
    # Get Open Humans ID and Nightscout data.
    oh_id = exchange_token_for_id(token)
    if not before_date:
        before_date = arrow.get().format('YYYY-MM-DD')
    ns_entries_data = get_nightscout_entries(
        ns_url=ns_url, before_date=before_date, after_date=after_date,
        logger=logger)

    # Prepare gzip-compressed data in filelike object, and associated metadata.
    entries_filename = 'entries.json.gz'
    entries_file, metadata = prepare_json_gz_fileobj(
        filename=entries_filename, data=ns_entries_data, tags=['json'],
        description="Nightscout entries data", logger=logger)
    metadata['end_date'] = arrow.get(before_date).format('YYYY-MM-DD')
    if after_date:
        metadata['start_date'] = arrow.get(after_date).format('YYYY-MM-DD')

    # Delete any existng Open Humans files and upload new file.
    delete_all_oh_files(token=token, project_member_id=oh_id, logger=logger)
    logger.debug("Uploading '{}' with metadata '{}', project_member_id='{}'".format(
        entries_filename, json.dumps(metadata), oh_id))
    upload_req = requests.post(
        OH_UPLOAD + '?access_token={}'.format(token),
        files={'data_file': (entries_filename, entries_file)},
        data={'project_member_id': oh_id,
              'metadata': json.dumps(metadata)})
    logger.info("Upload complete, status code: {}".format(
        upload_req.status_code))
    logger.debug("Upload response: {}".format(
        upload_req.text))
