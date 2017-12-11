# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import pytest

from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.ipmi_reboot
@pytest.mark.parametrize(
    "args", [
        [
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
        ],
        [
            '-H', '127.0.0.1',
            '-P', 'test_ipmitool_pass',
        ],
        [
            '-H', '127.0.0.1',
            '-U', 'test_reboot_user',
        ],
    ], ids=['address', 'username', 'password']
)
def test_ipmi_reboot_requires_arg(args):
    with pytest.raises(CommandError):
        call_command('ipmi_reboot', *args)


@pytest.mark.ipmi_reboot
def test_ipmi_no_reboot_on_mc_info_failure():
    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.side_effect = Exception('Error fetching mc info.')

        with pytest.raises(Exception):
            call_command('ipmi_reboot', *[
                '-H', '127.0.0.1',
                '-U', 'test_reboot_user',
                '-P', 'test_ipmitool_pass',
            ], delay=1, power_status_wait=2, power_status_wait_interval=1)

        assert cmd_mock.called
        cmd_mock.assert_called_once_with([
            'ipmitool',
            '-H', '127.0.0.1',
            '-I', 'lanplus',
            '-L', 'ADMINISTRATOR',
            '-p', '623',
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
            'mc', 'info'], stderr=-2, timeout=5)


@pytest.mark.ipmi_reboot
def test_ipmi_soft_reboot_success_from_power_status_timeout():
    base_args = [
        'ipmitool',
        '-H', '127.0.0.1',
        '-I', 'lanplus',
        '-L', 'ADMINISTRATOR',
        '-p', '623',
        '-U', 'test_reboot_user',
        '-P', 'test_ipmitool_pass',
    ]

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.return_value = b''

        call_command('ipmi_reboot', *[
            '-H', '127.0.0.1',
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
        ], delay=1, power_status_wait=2, power_status_wait_interval=1)

        expected_calls = [mock.call(base_args + cmd, stderr=-2, timeout=5) for cmd in [
            ['mc', 'info'],
            ['power', 'soft'],
            ['power', 'status'],
            ['power', 'status'],
            ['power', 'status'],
            ['power', 'on'],
        ]]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call


@pytest.mark.ipmi_reboot
def test_ipmi_hard_reboot_success_from_power_status_off():
    base_args = [
        'ipmitool',
        '-H', '127.0.0.1',
        '-I', 'lanplus',
        '-L', 'ADMINISTRATOR',
        '-p', '623',
        '-U', 'test_reboot_user',
        '-P', 'test_ipmitool_pass',
    ]

    def cmd_side_effect(args, **kwargs):
        if args[-2:] == ['power', 'soft']:
            raise CommandError('Soft power off failed')
        elif args[-2:] == ['power', 'status']:
            return b'power is off'
        else:
            return b''

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.side_effect = cmd_side_effect

        call_command('ipmi_reboot', *[
            '-H', '127.0.0.1',
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
        ], delay=1, power_status_wait=2, power_status_wait_interval=1)

        expected_calls = [mock.call(base_args + cmd, stderr=-2, timeout=5) for cmd in [
            ['mc', 'info'],
            ['power', 'soft'],
            ['power', 'off'],
            ['power', 'status'],
            ['power', 'on'],
        ]]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call


@pytest.mark.ipmi_reboot
def test_ipmi_reboot_power_on_failure():
    base_args = [
        'ipmitool',
        '-H', '127.0.0.1',
        '-I', 'lanplus',
        '-L', 'ADMINISTRATOR',
        '-p', '623',
        '-U', 'test_reboot_user',
        '-P', 'test_ipmitool_pass',
    ]

    def cmd_side_effect(args, **kwargs):
        if args[-2:] == ['power', 'status']:
            return b'power is off'
        elif args[-2:] == ['power', 'on']:
            raise CommandError('power on failed')
        else:
            return b''

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.side_effect = cmd_side_effect

        with pytest.raises(CommandError):
            call_command('ipmi_reboot', *[
                '-H', '127.0.0.1',
                '-U', 'test_reboot_user',
                '-P', 'test_ipmitool_pass',
            ], delay=1, power_status_wait=2, power_status_wait_interval=1)

        expected_calls = [mock.call(base_args + cmd, stderr=-2, timeout=5) for cmd in [
            ['mc', 'info'],
            ['power', 'soft'],
            ['power', 'status'],
            ['power', 'on'],
        ]]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call
