# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import subprocess

import mock
import pytest

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


# TODO: test missing and unknown host key errors


@pytest.mark.ssh_reboot
@pytest.mark.parametrize(
    "args", [
        [
            '-l', 'test_reboot_user',
            'sshd',
        ],
        [
            '-i', '~/.ssh/test_ipmitool_pass.key',
            'sshd',
        ],
        [
            '-l', 'test_reboot_user',
            '-i', '~/.ssh/test_ipmitool_pass.key',
        ],
    ], ids=['private_key', 'login_name', 'hostname']
)
def test_ssh_reboot_requires_arg(args):
    with pytest.raises(CommandError):
        call_command('ssh_reboot', *args)


reboot_commands = [
    'reboot',
    'shutdown -f -t 3 -r',
]

@pytest.mark.ssh_reboot
@pytest.mark.parametrize("reboot_command", reboot_commands, ids=lambda rc: rc)
def test_ssh_reboot_success_with_reboot_command(reboot_command):
    base_args = [
        'ssh',
        '-o', 'PasswordAuthentication=no',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-i', '~/.ssh/test_ipmitool_pass.key',
        '-l', 'test_reboot_user',
        '-p', '22',
        'sshd',  # name of sshd host in docker-compose
    ]

    def cmd_side_effect(args, *more_args, **kwargs):
        if args[-1] == reboot_command:
            return b''
        else:
            raise subprocess.CalledProcessError(cmd=reboot_command, returncode=-1)

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.side_effect = cmd_side_effect

        call_command('ssh_reboot', *[
            '-l', 'test_reboot_user',
            '-i', '~/.ssh/test_ipmitool_pass.key',
            'sshd',
        ])

        # expect calls up to the the reboot command we're testing for which should succeed
        expected_calls = [
            mock.call(base_args + [cmd], stderr=-2, timeout=5)
            for cmd in reboot_commands
            if reboot_commands.index(cmd) <= reboot_commands.index(reboot_command)
        ]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call


@pytest.mark.ssh_reboot
def test_ssh_reboot_all_reboot_commands_fail():
    base_args = [
        'ssh',
        '-o', 'PasswordAuthentication=no',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-i', '~/.ssh/test_ipmitool_pass.key',
        '-l', 'test_reboot_user',
        '-p', '22',
        'sshd',  # name of sshd host in docker-compose
    ]

    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.side_effect = subprocess.CalledProcessError(cmd='ssh reboot', returncode=-1)

        with pytest.raises(CommandError):
            call_command('ssh_reboot', *[
                '-l', 'test_reboot_user',
                '-i', '~/.ssh/test_ipmitool_pass.key',
                'sshd',
            ])

        # expect calls up to the the reboot command we're testing for which should succeed
        expected_calls = [
            mock.call(base_args + [cmd], stderr=-2, timeout=5)
            for cmd in reboot_commands
        ]
        for i, call in enumerate(expected_calls):
            assert cmd_mock.mock_calls[i] == call
