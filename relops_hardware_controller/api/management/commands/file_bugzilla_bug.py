import logging
import string
import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from relops_hardware_controller.api.validators import validate_host

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('host', type=str)
        parser.add_argument('--cc', dest='cc', default='', type=str)
        parser.add_argument('--log', dest='log', default='', type=str)

    def handle(self, host, *args, **options):
        url = settings.BUGZILLA_URL + '/rest/bug'
        basic_payload = { 'api_key': settings.BUGZILLA_API_KEY }
        json_header = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        reopen_state = 'REOPENED'
        short_hostname = host.split('.')[0]
        tracker_template = settings.BUGZILLA_WORKER_TRACKER_TEMPLATE
        reboot_template = settings.BUGZILLA_REBOOT_TEMPLATE

        if 'bugzilla-dev' in url:
            # bugzilla-dev has some differences
            short_hostname = short_hostname.replace('-', '')
            reopen_state = 'UNCONFIRMED'
            tracker_template = string.Template(
                tracker_template.template.replace('CIDuty', 'RelOps'))

        # Find, reopen, or create parent tracker bug.
        try:
            response = requests.get(
                url + '?alias={}'.format(short_hostname),
                json=basic_payload,
                headers=json_header,
            )
            logger.warn('get bug: {}'.format(response.json()))
            response = response.json()['bugs'][0]
            parent = response.get('id', None)
            if not response['is_open']:
                response = requests.put(
                    '{}/{}'.format(url, parent),
                    json={**basic_payload,
                          **{'status': reopen_state}},
                    headers=json_header,
                )
                logger.debug('update bug response: {}'.format(response.content))
        except IndexError as e:
            logger.debug('parent bug not found')
            data = tracker_template.safe_substitute(
                hostname=host,
                alias=short_hostname,
                **basic_payload
            )
            logger.warn('payload:{}'.format(data))
            response = requests.post(
                url,
                data=data,
                headers=json_header,
            )
            parent = response.json().get('id', None)
            logger.info('created parent bug {}'.format(parent))

        # Get (if not closed) or create reboot bug.
        payload = reboot_template.safe_substitute(
            hostname=host,
            blocks=parent,
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
            if bug['is_open']:
                updates['status'] = reopen_state
            updates['comment'] = {
                'body': json.loads(payload)['description'],
            }
        except Exception as e:
            logger.exception(e)

            logger.warn(payload)
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
