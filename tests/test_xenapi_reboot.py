# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import subprocess

import mock
import pytest

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.xenapi_reboot
@pytest.mark.parametrize(
    "args", [
        [
        ],
    ], ids=['host_uuid']
)
def test_xenapi_reboot_requires_arg(args):
    with pytest.raises(CommandError):
        call_command('xenapi_reboot', *args)


# TODO: test invalid args


@pytest.mark.xenapi_reboot
def test_xenapi_reboot_login_failure():
    with mock.patch('relops_hardware_controller.api.management.commands.xenapi_reboot.XenAPI.Session') as mock_session_ctor:
        mock_session = mock_session_ctor.return_value

        mock_session.login_with_password.side_effect = Exception("XenAPI login failed.")

        call_command('xenapi_reboot', 'test_xen_vm_uuid', delay=1)

        mock_session_ctor.assert_called_once_with(uri='https://xenapiserver/')

        mock_session.login_with_password.assert_called_once_with('xen_dev_username', 'anything_zen_password')

        mock_session.xenapi.session.logout.assert_called_once_with()


@pytest.mark.xenapi_reboot
def test_xenapi_soft_reboot_success():
    with mock.patch('relops_hardware_controller.api.management.commands.xenapi_reboot.XenAPI.Session') as mock_session_ctor:
        mock_session = mock_session_ctor.return_value
        mock_vm = mock_session.xenapi.VM.get_by_uuid.return_value

        call_command('xenapi_reboot', 'test_xen_vm_uuid', delay=1)

        mock_session_ctor.assert_called_once_with(uri='https://xenapiserver/')

        mock_session.login_with_password.assert_called_once_with('xen_dev_username', 'anything_zen_password')

        mock_session.xenapi.VM.get_by_uuid.assert_called_once_with('test_xen_vm_uuid')
        mock_session.xenapi.VM.clean_shutdown.assert_called_once_with(mock_vm)

        mock_session.xenapi.VM.start.assert_called_once_with(mock_vm, False, False)

        mock_session.xenapi.session.logout.assert_called_once_with()


@pytest.mark.xenapi_reboot
def test_xenapi_hard_reboot_success():
    with mock.patch('relops_hardware_controller.api.management.commands.xenapi_reboot.XenAPI.Session') as mock_session_ctor:
        mock_session = mock_session_ctor.return_value
        mock_vm = mock_session.xenapi.VM.get_by_uuid.return_value

        mock_session.xenapi.VM.clean_shutdown.side_effect = Exception("XenAPI clean shutdown failed.")

        call_command('xenapi_reboot', 'test_xen_vm_uuid', delay=1)

        mock_session_ctor.assert_called_once_with(uri='https://xenapiserver/')

        mock_session.login_with_password.assert_called_once_with('xen_dev_username', 'anything_zen_password')

        mock_session.xenapi.VM.get_by_uuid.assert_called_once_with('test_xen_vm_uuid')
        mock_session.xenapi.VM.clean_shutdown.assert_called_once_with(mock_vm)
        mock_session.xenapi.VM.hard_shutdown.assert_called_once_with(mock_vm)
        mock_session.xenapi.VM.start.assert_called_once_with(mock_vm, False, False)

        mock_session.xenapi.session.logout.assert_called_once_with()


@pytest.mark.xenapi_reboot
def test_xenapi_reboot_shutdown_failure():
    with mock.patch('relops_hardware_controller.api.management.commands.xenapi_reboot.XenAPI.Session') as mock_session_ctor:
        mock_session = mock_session_ctor.return_value
        mock_vm = mock_session.xenapi.VM.get_by_uuid.return_value

        mock_session.xenapi.VM.clean_shutdown.side_effect = Exception("XenAPI clean shutdown failed.")
        mock_session.xenapi.VM.hard_shutdown.side_effect = Exception("XenAPI hard shutdown failed.")

        with pytest.raises(Exception):
            call_command('xenapi_reboot', 'test_xen_vm_uuid', delay=1)

        mock_session_ctor.assert_called_once_with(uri='https://xenapiserver/')

        mock_session.login_with_password.assert_called_once_with('xen_dev_username', 'anything_zen_password')

        mock_session.xenapi.VM.get_by_uuid.assert_called_once_with('test_xen_vm_uuid')
        mock_session.xenapi.VM.clean_shutdown.assert_called_once_with(mock_vm)
        mock_session.xenapi.VM.hard_shutdown.assert_called_once_with(mock_vm)

        mock_session.xenapi.session.logout.assert_called_once_with()
