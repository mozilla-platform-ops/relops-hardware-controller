# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import subprocess

import mock
import pytest

from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.snmp_reboot
@pytest.mark.parametrize(
    "args", [
        [
            'test_port',
        ],
        [
            'test_fqdn',
        ],
    ], ids=['fqdn', 'port']
)
def test_snmp_reboot_requires_arg(args):
    with pytest.raises(CommandError):
        call_command('snmp_reboot', *args)


# TODO: test invalid args


@pytest.mark.snmp_reboot
def test_snmp_reboot_power_off_failure():
    base_args = [
        'snmpset',
        '-v', '1',
        '-c', 'private',
        'l-yosemite-r0-0000.test.releng.scl3.mozilla.com',
        "1.3.6.1.4.1.1718.3.2.3.1.11.port_arg_0.port_arg_1.['port_arg_2']",
        'i',
    ]

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.side_effect = subprocess.CalledProcessError(cmd='snmpset power off failed', returncode=-1)

        with pytest.raises(subprocess.CalledProcessError):
            call_command('snmp_reboot', *[
                'l-yosemite-r0-0000.test.releng.scl3.mozilla.com',
                'port_arg_0',
                'port_arg_1',
                'port_arg_2',
            ], delay=1, timeout=5)

        expected_calls = [mock.call(base_args + cmd, stderr=-2, timeout=5) for cmd in [
            ['2'],  # off
        ]]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call


@pytest.mark.snmp_reboot
def test_snmp_reboot_power_on_failure():
    base_args = [
        'snmpset',
        '-v', '1',
        '-c', 'private',
        'l-yosemite-r0-0000.test.releng.scl3.mozilla.com',
        "1.3.6.1.4.1.1718.3.2.3.1.11.port_arg_0.port_arg_1.['port_arg_2']",
        'i',
    ]

    def cmd_side_effect(args, **kwargs):
        if args[-1] == '2':
            raise subprocess.CalledProcessError(cmd='snmpset power on failed', returncode=-1)
        else:
            return b''

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.side_effect = cmd_side_effect

        with pytest.raises(subprocess.CalledProcessError):
            call_command('snmp_reboot', *[
                'l-yosemite-r0-0000.test.releng.scl3.mozilla.com',
                'port_arg_0',
                'port_arg_1',
                'port_arg_2',
            ], delay=1, timeout=5)

        expected_calls = [mock.call(base_args + cmd, stderr=-2, timeout=5) for cmd in [
            ['2'],  # off
        ]]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call


@pytest.mark.snmp_reboot
def test_snmp_reboot_success():
    base_args = [
        'snmpset',
        '-v', '1',
        '-c', 'private',
        'l-yosemite-r0-0000.test.releng.scl3.mozilla.com',
        "1.3.6.1.4.1.1718.3.2.3.1.11.port_arg_0.port_arg_1.['port_arg_2']",
        'i',
    ]

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.return_value = b''

        call_command('snmp_reboot', *[
            'l-yosemite-r0-0000.test.releng.scl3.mozilla.com',
            'port_arg_0',
            'port_arg_1',
            'port_arg_2',
        ], delay=1, timeout=5)

        expected_calls = [mock.call(base_args + cmd, stderr=-2, timeout=5) for cmd in [
            ['2'],  # off
            ['1'],  # on
        ]]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call
