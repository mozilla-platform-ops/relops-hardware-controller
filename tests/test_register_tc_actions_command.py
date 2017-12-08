# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from mock import patch
import pytest

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


def test_register_tc_actions_requires_provisioner_id(monkeypatch):
    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', 'email/you@yourdomain.com/tutorial')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w')

    with pytest.raises(CommandError):
        call_command('register_tc_actions')


def test_register_tc_actions_requires_client_id(monkeypatch):
    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', '')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w')

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'test-provisioner-id')


def test_register_tc_actions_requires_access_token(monkeypatch):
    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', 'email/you@yourdomain.com/tutorial')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '')

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'test-provisioner-id')


def test_register_tc_actions_rejects_invalid_provisioner_id(monkeypatch):
    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', 'email/you@yourdomain.com/tutorial')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w')

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', '; echo foo')


def test_register_tc_actions_rejects_invalid_client_id(monkeypatch):
    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', 'email/you@yourdomain.com/tutorial; echo foo')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w')

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'test-provisioner-id')


def test_register_tc_actions_rejects_invalid_access_token(monkeypatch):
    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', 'email/you@yourdomain.com/tutorial')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w; echo bar')

    with pytest.raises(ValidationError):
        call_command('register_tc_actions', 'test-provisioner-id')


def test_register_tc_actions_registers_actions(monkeypatch):
    # assuming we have at least one TASK_NAMES in settings

    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', 'email/you@yourdomain.com/tutorial')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w')

    with patch('taskcluster.Queue') as mocked_queue:
        call_command('register_tc_actions', 'test-provisioner-id')

        assert mocked_queue.called
        assert mocked_queue.return_value.declareProvisioner.called
