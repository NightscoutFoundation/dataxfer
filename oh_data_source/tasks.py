"""
A template for an asynchronous task that updates data in Open Humans.

This example task:
  1. deletes any current files in OH if they match the planned upload filename
  2. adds a data file
"""
from __future__ import absolute_import

import json
import logging
import os
import shutil
import tempfile
import textwrap
from urllib2 import HTTPError

from celery import shared_task
from django.utils import lorem_ipsum
import requests

from .models import OpenHumansMember
from .nightscout_data import get_ns_entries

OH_API_BASE = 'https://www.openhumans.org/api/direct-sharing'
OH_EXCHANGE_TOKEN = OH_API_BASE + '/project/exchange-member/'
OH_DELETE_FILES = OH_API_BASE + '/project/files/delete/'
OH_DIRECT_UPLOAD = OH_API_BASE + '/project/files/upload/direct/'
OH_DIRECT_UPLOAD_COMPLETE = OH_API_BASE + '/project/files/upload/complete/'

# Set up logging.
logger = logging.getLogger(__name__)


@shared_task
def xfer_to_open_humans(oh_id, ns_before, ns_after, ns_url, num_submit=0):
    """
    Transfer data to Open Humans.

    num_submit is an optional parameter in case you want to resubmit failed
    tasks (see comments in code).
    """
    logger.debug('Trying to transfer data for {} to Open Humans'.format(oh_id))
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    oh_member.last_xfer_status = 'Initiated'
    oh_member.save()

    # Make a tempdir for all temporary files.
    # Delete this even if an exception occurs.
    tempdir = tempfile.mkdtemp()
    try:
        add_data_to_open_humans(
            oh_member, ns_before, ns_after, ns_url, tempdir)
        oh_member.last_xfer_status = 'Complete'
        oh_member.save()
    except:
        oh_member.last_xfer_status = 'Failed'
        oh_member.save()
    finally:
        shutil.rmtree(tempdir)


def add_data_to_open_humans(oh_member, ns_before, ns_after, ns_url, tempdir):
    """
    Add demonstration file to Open Humans.

    This might be a good place to start editing, to add your own project data.

    This template is written to provide the function with a tempdir that
    will be cleaned up later. You can use the tempdir to stage the creation of
    files you plan to upload to Open Humans.
    """
    # Create example file.
    entries_filepath, entries_metadata = get_ns_entries(
        oh_member=oh_member, tempdir=tempdir, ns_url=ns_url,
        before_date=ns_before, after_date=ns_after)

    # Remove all files previously added to Open Humans.
    delete_all_oh_files(oh_member)

    # Upload this file to Open Humans.
    upload_file_to_oh(oh_member, entries_filepath, entries_metadata)


def make_example_datafile(tempdir):
    """
    Make a lorem-ipsum file in the tempdir, for demonstration purposes.
    """
    filepath = os.path.join(tempdir, 'example_data.txt')
    paras = lorem_ipsum.paragraphs(3, common=True)
    output_text = '\n'.join(['\n'.join(textwrap.wrap(p)) for p in paras])
    with open(filepath, 'w') as f:
        f.write(output_text)
    metadata = {
        'tags': ['example', 'text', 'demo'],
        'description': 'File with lorem ipsum text for demonstration purposes',
    }
    return filepath, metadata


def delete_all_oh_files(oh_member):
    """
    Delete all current project files in Open Humans for this project member.
    """
    # Delete all current Nightscout files in Open Humans.
    req = requests.post(
        OH_DELETE_FILES,
        params={'access_token': oh_member.get_access_token()},
        data={'project_member_id': oh_member.oh_id,
              'all_files': True})
    logger.debug('Files deleted. Status code: {}'.format(req.status_code))


def upload_file_to_oh(oh_member, filepath, metadata):
    """
    This demonstrates using the Open Humans "large file" upload process.

    The small file upload process is simpler, but it can time out. This
    alternate approach is required for large files, and still appropriate
    for small files.

    This process is "direct to S3" using three steps: 1. get S3 target URL from
    Open Humans, 2. Perform the upload, 3. Notify Open Humans when complete.
    """
    # Get the S3 target from Open Humans.
    upload_url = '{}?access_token={}'.format(
        OH_DIRECT_UPLOAD, oh_member.get_access_token())
    req1 = requests.post(
        upload_url,
        data={'project_member_id': oh_member.oh_id,
              'filename': os.path.basename(filepath),
              'metadata': json.dumps(metadata)})
    if req1.status_code != 201:
        raise HTTPError(code=req1.status_code,
                        text='Bad response when starting file upload.')

    # Upload to S3 target.
    with open(filepath, 'rb') as fh:
        req2 = requests.put(url=req1.json()['url'], data=fh)
    if req2.status_code != 200:
        raise HTTPError(code=req2.status_code,
                        text='Bad response when uploading to target.')

    # Report completed upload to Open Humans.
    complete_url = ('{}?access_token={}'.format(
        OH_DIRECT_UPLOAD_COMPLETE, oh_member.get_access_token()))
    req3 = requests.post(
        complete_url,
        data={'project_member_id': oh_member.oh_id,
              'file_id': req1.json()['id']})
    if req3.status_code != 200:
        raise HTTPError(code=req2.status_code,
                        text='Bad response when uploading to target.')

    logger.debug('Upload done: "{}" for member {}.'.format(
        os.path.basename(filepath), oh_member.oh_id))
