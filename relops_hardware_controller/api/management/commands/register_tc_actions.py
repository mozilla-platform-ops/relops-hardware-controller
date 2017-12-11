
import os
import re

import taskcluster

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import load_command_class
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse
from django.utils.http import urlencode


class Command(BaseCommand):
    help = '''Registers actions on a TC provisioner for HW management API
tasks. Requires env vars TASKCLUSTER_CLIENT_ID and TASKCLUSTER_ACCESS_TOKEN
with TC scope: queue:declare-provisioner:<my_provisioner_id>#actions'''

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('provisioner_id',
                            type=str,
                            help='A taskcluster provisioner ID')

    def validate_credentials(self, credentials):
        # TODO: confirm check with TC team for what's valid
        if not credentials['clientId']:
            raise ValidationError('No TASKCLUSTER_CLIENT_ID in env.')

        if not credentials['accessToken']:
            raise ValidationError('No TASKCLUSTER_ACCESS_TOKEN in env.')

        if not re.match(r'^[-@_a-zA-Z0-9/\.]{1,256}$', credentials['clientId']):
            raise ValidationError('Invalid TASKCLUSTER_CLIENT_ID in env.')

        if not re.match(r'^[^ ;,]{1,256}$', credentials['accessToken']):
            raise ValidationError('Invalid TASKCLUSTER_ACCESS_TOKEN in env.')

    def validate_provisioner_id(self, provisioner_id):
        # TODO: confirm check with TC team for what's valid
        if not re.match(r'^[-_a-zA-Z0-9]{1,256}$', provisioner_id):
            raise ValidationError('Invalid provisioner_id')

    def handle(self, provisioner_id, *args, **options):
        credentials = dict(clientId=os.environ['TASKCLUSTER_CLIENT_ID'],
                           accessToken=os.environ['TASKCLUSTER_ACCESS_TOKEN'])

        self.validate_credentials(credentials)
        self.validate_provisioner_id(provisioner_id)

        queue = taskcluster.Queue({'credentials': credentials})

        actions = []

        for task_name in settings.TASK_NAMES:
            cmd_class = load_command_class('relops_hardware_controller.api', task_name)

            query_params = urlencode(dict(task_name=task_name))
            url = reverse('api:JobList',
                          kwargs=dict(worker_id='workerId',
                                      worker_group='workerGroup'))

            # work around for our url regex not allowing < and >
            assert 'workerId' not in provisioner_id and 'workerGroup' not in provisioner_id
            url = url.replace('workerId', '<workerId>').replace('workerGroup', '<workerGroup>') + '?' + query_params

            # https://docs.taskcluster.net/reference/platform/taskcluster-queue/docs/actions#defining-actions
            actions.append(dict(name=task_name,
                                title=task_name,
                                context='worker',
                                method='POST',
                                url=url,
                                description=cmd_class.help))

        print('registering actions:', actions)

        # http://schemas.taskcluster.net/queue/v1/update-provisioner-request.json#
        payload = dict(actions=actions)

        # requires scope queue:declare-provisioner:$PROVISIONER_ID#actions
        queue.declareProvisioner(provisioner_id, payload)
