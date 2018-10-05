
import logging
import string
import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from relops_hardware_controller.api.validators import validate_host

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Files a new bugzilla bug for the host. Raises for exceptions for bad or invalid responses.'
    doc_url = 'https://github.com/mozbhearsum/bzrest/blob/master/bzrest/client.py'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'host',
            type=str,
            help='A host',
        )
        parser.add_argument('job_data', type=json.loads)
        parser.add_argument('--cc', dest='cc', default='', type=str)
        parser.add_argument('--log', dest='log', default='', type=str)

    def handle(self, host, job_data, *args, **options):
        url = settings.BUGZILLA_URL + '/rest/bug'
        basic_payload = { 'api_key': settings.BUGZILLA_API_KEY }
        json_header = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        reopen_state = settings.BUGZILLA_REOPEN_STATE
        tracker_template = string.Template(settings.BUGZILLA_WORKER_TRACKER_TEMPLATE)
        reboot_template = string.Template(settings.BUGZILLA_REBOOT_TEMPLATE)
        short_hostname = host.split('.')[0]
        datacenter = host.split('.')[3].upper()
        if 'bugzilla-dev' in url:
            # bugzilla-dev aliases fail with dashes
            short_hostname = short_hostname.replace('-', '')

        def create_or_update_bug(bug_id=None, alias=None, data='{}', reopen_state=None):
            bug_url = '{}/{}'.format(url, bug_id if bug_id else alias)

            try:
                response = requests.get(
                    bug_url,
                    json=basic_payload,
                    headers=json_header,
                )
                logger.debug('get bug result: {}'.format(response.json()))
                response = response.json()['bugs'][0]
                parent = response.get('id', None)
                if reopen_state and not response['is_open']:
                    response = requests.put(
                        '{}/{}'.format(url, parent),
                        json={**basic_payload,
                              **{'status': reopen_state}},
                        headers=json_header,
                    )
                    logger.debug('update bug response: {}'.format(response.content))
            except:
                logger.debug('bug not found. creating new bug')
                response = requests.post(
                    url,
                    data=data,
                    headers=json_header,
                )
                parent = response.json().get('id', None)
                logger.info('created bug {}'.format(parent))

            return parent

        # Find, reopen, or create parent tracker bug.
        parent = create_or_update_bug(
            alias=short_hostname,
            data=tracker_template.safe_substitute(
                hostname=host,
                alias=short_hostname,
                DC=datacenter,
                **basic_payload
            ),
            reopen_state=reopen_state,
        )

        # Get (if not closed) or create reboot bug.
        payload = reboot_template.safe_substitute(
            hostname=host,
            blocks=parent,
            **job_data,
            **options,
            **basic_payload
        )

        updates = dict()
        try:
            params = {k:v for k,v in json.loads(payload).items()
                if k in [ 'summary', 'product', 'component' ]}
            params['resolution'] = '---'
            response = requests.get(
                url,
                params=params,
                json=basic_payload,
                headers=json_header,
            )
            bug = response.json()['bugs'][0]
            bug_id = bug['id']
            logger.info('existing bug found: {}'.format(bug_id))
            updates['comment'] = {
                'body': json.loads(payload)['description'],
            }
        except Exception:
            logger.debug('creating new bug')

            response = requests.post(
                url,
                data=payload,
                headers=json_header,
            )
            logger.debug('file bug response: {}'.format(response.content))
            response.raise_for_status()
            bug_id = response.json()['id']
            logger.info('bug created: {}'.format(bug_id))

        # Confirm blocking parent and add any updates.
        response = requests.put(
            '{}/{}'.format(url, bug_id),
            json={**basic_payload,
                  **{'blocks': {'add': [ parent ]}},
                  **updates,
            },
            headers=json_header,
        )
        logger.debug('update bug response: {}'.format(response.content))

        return '{}/show_bug.cgi?id={}'.format(settings.BUGZILLA_URL, bug_id)
