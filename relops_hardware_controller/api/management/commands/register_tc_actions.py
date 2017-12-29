
import logging
import re

import taskcluster

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import load_command_class
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator
from django.utils.http import urlencode

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = '''Registers actions on a TC provisioner for HW management API tasks. Requires
TASKCLUSTER_CLIENT_ID and TASKCLUSTER_ACCESS_TOKEN in settings or env vars with
TC scope: queue:declare-provisioner:<my_provisioner_id>#actions.

Example usage:

./manage.py register_tc_actions --settings relops_hardware_controller.settings
http://localhost:8000 test-dummy-provisioner'''

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'base_url',
            type=str,
            help='A base url without a trailing slash for a '
            'user on the VPN to resolve roller service. '
            'e.g. http://127.0.0.1:8000 or https://roller-dev1.srv.releng.mdc1.mozilla.com')

        parser.add_argument(
            'provisioner_id',
            type=str,
            help='A taskcluster provisioner ID. e.g. test-dummy-provisioner or releng-hardware')

    def validate_credentials(self, credentials):
        if not credentials['clientId']:
            raise ValidationError('No TASKCLUSTER_CLIENT_ID in env.')

        if not credentials['accessToken']:
            raise ValidationError('No TASKCLUSTER_ACCESS_TOKEN in env.')

        if not re.match(r'^[-@_a-zA-Z0-9/\.]{1,256}$', credentials['clientId']):
            raise ValidationError('Invalid TASKCLUSTER_CLIENT_ID in env.')

        if not re.match(r'^[^ ;,]{1,256}$', credentials['accessToken']):
            raise ValidationError('Invalid TASKCLUSTER_ACCESS_TOKEN in env.')

    def validate_base_url(self, base_url):
        # only allow replacement params in the uri
        if 'workerId' in base_url or 'workerGroup' in base_url:
            raise ValidationError(
                'Invalid base_url. '
                'It cannnot include "workerId" or "workerGroup".')

        URLValidator(schemes=['http', 'https'])(base_url)

        if base_url.startswith('http://'):
            logger.warn('base_url with http scheme will be blocked as '
                        'a mixed content request from https://tools.taskcluster.net')

    def validate_provisioner_id(self, provisioner_id):
        # only allow replacement params in the uri
        if 'workerId' in provisioner_id or 'workerGroup' in provisioner_id:
            raise ValidationError(
                'Invalid provisioner_id. '
                'It cannnot include "workerId" or "workerGroup".')

        if not re.match(r'^[-_a-zA-Z0-9]{1,256}$', provisioner_id):
            raise ValidationError(
                'Invalid provisioner_id. '
                'Does not match regex for alphanumeric dash and underscore characters.')

    def handle(self, base_url, provisioner_id, *args, **options):
        self.validate_base_url(base_url)
        self.validate_provisioner_id(provisioner_id)

        credentials = dict(clientId=settings.TASKCLUSTER_CLIENT_ID,
                           accessToken=settings.TASKCLUSTER_ACCESS_TOKEN)

        self.validate_credentials(credentials)

        queue = taskcluster.Queue({'credentials': credentials})

        actions = []

        for task_name in settings.TASK_NAMES:
            cmd_class = load_command_class('relops_hardware_controller.api', task_name)

            query_params = urlencode(dict(task_name=task_name))
            uri = reverse('api:JobList', kwargs=dict(worker_id='workerId',
                                                     worker_group='workerGroup'))
            url = base_url + uri

            # work around for our url regex not allowing < and >
            url = url.replace('workerId', '<workerId>') \
                .replace('workerGroup', '<workerGroup>') + '?' + query_params

            # https://docs.taskcluster.net/reference/platform/taskcluster-queue/docs/actions#defining-actions
            actions.append(dict(name=task_name,
                                title=task_name,
                                context='worker-type',
                                method='POST',
                                url=url,
                                description=cmd_class.help))

        logger.info('registering actions with payload: %s', actions)

        # http://schemas.taskcluster.net/queue/v1/update-provisioner-request.json#
        payload = dict(actions=actions)

        # requires scope queue:declare-provisioner:$PROVISIONER_ID#actions
        queue.declareProvisioner(provisioner_id, payload)
