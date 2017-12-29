# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from mock import patch
import pytest

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


def test_register_tc_actions_requires_base_url(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(CommandError):
        call_command('register_tc_actions')


def test_register_tc_actions_requires_provisioner_id(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(CommandError):
        call_command('register_tc_actions', 'http://localhost:8000')


def test_register_tc_actions_requires_client_id(settings):
    settings.TASKCLUSTER_CLIENT_ID = ''
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'http://localhost:8000', 'test-provisioner-id')


def test_register_tc_actions_requires_access_token(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = ''

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'http://localhost:8000', 'test-provisioner-id')


def test_register_tc_actions_rejects_invalid_base_url(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'ftp://localhost:8000', 'test-provisioner-id')


def test_register_tc_actions_rejects_invalid_provisioner_id(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'http://localhost:8000', '; echo foo')


def test_register_tc_actions_rejects_invalid_client_id(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial; echo foo'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'http://localhost:8000', 'test-provisioner-id')


def test_register_tc_actions_rejects_invalid_base_url_containing_worker_param(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'http://workerId', 'test-provisioner-id')


def test_register_tc_actions_rejects_invalid_provisioner_id_containing_worker_param(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'http://localhost:8000', 'test-workerGroup')


def test_register_tc_actions_rejects_invalid_access_token(settings):
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w; echo bar'

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'http://localhost:8000', 'test-provisioner-id')


def test_register_tc_actions_registers_actions_success(settings):
    # need at least one task in settings.TASK_NAMES
    # and the task to exist in api management commands

    settings.TASK_NAMES = ['ping']
    settings.TASKCLUSTER_CLIENT_ID = 'email/you@yourdomain.com/tutorial'
    settings.TASKCLUSTER_ACCESS_TOKEN = '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w'

    with patch('taskcluster.Queue') as mocked_queue:
        call_command('register_tc_actions', 'http://localhost:8000', 'test-provisioner-id')

        mocked_queue.assert_called_once_with(
            {'credentials': dict(clientId='email/you@yourdomain.com/tutorial',
                                 accessToken='9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w')})
        mocked_queue.return_value.declareProvisioner.assert_called_once_with(
            'test-provisioner-id', {'actions': [{
                'name': 'ping',
                'title': 'ping',
                'context': 'worker-type',
                'method': 'POST',
                'url': 'http://localhost:8000/api/v1/workers/'
                '<workerId>/group/<workerGroup>/jobs?task_name=ping',
                'description': 'Tries to ICMP ping the host. '
                'Raises for exceptions for a lost packet or timeout.'}]})
