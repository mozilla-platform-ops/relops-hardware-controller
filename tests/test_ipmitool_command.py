# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import pytest

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.ipmitool
@pytest.mark.parametrize(
    "args", [
        [
            '-H', '127.0.0.1',
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
        ],
        [
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
            'mc', 'info',
        ],
        [
            '-H', '127.0.0.1',
            '-P', 'test_ipmitool_pass',
            'mc', 'info',
        ],
        [
            '-H', '127.0.0.1',
            '-U', 'test_reboot_user',
            'mc', 'info',
        ],
    ], ids=['command', 'address', 'username', 'password']
)
def test_ipmitool_requires_arg(args):
    with pytest.raises(CommandError):
        call_command('ipmitool', *args)


@pytest.mark.ipmitool
@pytest.mark.parametrize(
    "kwargs", [
        dict(privlvl='root'),
    ], ids=['invalid_privlvl_root']
)
def test_ipmitool_rejects_invalid_kwargs(kwargs):
    args = [
        '-H', '127.0.0.1',
        '-U', 'test_reboot_user',
        '-P', 'test_ipmitool_pass',
        'mc', 'info',
    ]
    with pytest.raises(ValidationError):
        call_command('ipmitool', *args, **kwargs)


@pytest.mark.ipmitool
def test_ipmitool_localhost_success():
    with mock.patch('subprocess.check_output') as cmd_mock:
        cmd_mock.return_value = b'output'
        output = call_command('ipmitool', *[
            '-H', '127.0.0.1',
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
            'mc', 'info',
        ], timeout=1, stderr=-2)

        assert cmd_mock.called
        cmd_mock.assert_called_once_with([
            'ipmitool',
            '-H', '127.0.0.1',
            '-I', 'lanplus',
            '-L', 'ADMINISTRATOR',
            '-p', '623',
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
            'mc', 'info'], timeout=1, stderr=-2)

        assert output == 'output'
