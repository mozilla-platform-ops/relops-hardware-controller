# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import pytest

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.ilo_reboot
@pytest.mark.parametrize(
    "args", [
        [],
    ], ids=['hostname']
)
def test_ilo_reboot_requires_arg(args):
    with pytest.raises(CommandError):
        call_command('ilo_reboot', *args)


@pytest.mark.ilo_reboot
@pytest.mark.parametrize(
    "args", [
        ['test_ilo_hostname'],
    ], ids=['hostname']
)
def test_ilo_reboot_requires_valid_arg(args):
    with pytest.raises(ValidationError):
        call_command('ilo_reboot', *args)


# TODO: test invalid kwargs


@pytest.mark.ilo_reboot
def test_ilo_login_fails():
    with mock.patch('hpilo.Ilo') as mock_ilo_ctor:
        mock_ilo_ctor.side_effect = Exception('ilo error logging in!')

        with pytest.raises(Exception):
            call_command('ilo_reboot', 'test.ilo.hostname', delay=1)

        mock_ilo_ctor.assert_called_once_with('test.ilo.hostname',
                                              login='ilo_dev_username',
                                              password='anything_ilo_password',
                                              timeout=60)


@pytest.mark.ilo_reboot
def test_ilo_get_power_status_fails():
    with mock.patch('hpilo.Ilo') as mock_ilo_ctor:
        mock_ilo = mock_ilo_ctor.return_value
        mock_ilo.get_host_power_status.side_effect = Exception('ilo.get_power_status failed!')

        with pytest.raises(Exception):
            call_command('ilo_reboot', 'test.ilo.hostname', delay=1)

        mock_ilo_ctor.assert_called_once_with('test.ilo.hostname',
                                              login='ilo_dev_username',
                                              password='anything_ilo_password',
                                              timeout=60)

        mock_ilo.get_host_power_status.assert_called_once_with()


@pytest.mark.ilo_reboot
def test_ilo_soft_reboot_success():
    with mock.patch('hpilo.Ilo') as mock_ilo_ctor:
        mock_ilo = mock_ilo_ctor.return_value
        mock_ilo.get_host_power_status.return_value = 'ON'

        call_command('ilo_reboot', 'test.ilo.hostname', delay=1)

        mock_ilo_ctor.assert_called_once_with('test.ilo.hostname',
                                              login='ilo_dev_username',
                                              password='anything_ilo_password',
                                              timeout=60)

        mock_ilo.get_host_power_status.assert_called_once_with()
        mock_ilo.reset_server.assert_called_once_with()


@pytest.mark.ilo_reboot
def test_ilo_hard_reboot_success():
    with mock.patch('hpilo.Ilo') as mock_ilo_ctor:
        mock_ilo = mock_ilo_ctor.return_value
        mock_ilo.get_host_power_status.return_value = 'ON'
        mock_ilo.reset_server.side_effect = Exception('ilo.reset_server failed!')

        call_command('ilo_reboot', 'test.ilo.hostname', delay=1)

        mock_ilo_ctor.assert_called_once_with('test.ilo.hostname',
                                              login='ilo_dev_username',
                                              password='anything_ilo_password',
                                              timeout=60)

        mock_ilo.get_host_power_status.assert_called_once_with()
        mock_ilo.reset_server.assert_called_once_with()

        assert len(mock_ilo.set_host_power.mock_calls) == 2, 'set_host_power not called twice'
        mock_ilo.set_host_power.mock_calls[0] == mock.call(host_power=False)
        mock_ilo.set_host_power.assert_called_with(host_power=True)  # check last call


@pytest.mark.ilo_reboot
def test_ilo_hard_reboot_power_off_fails():
    with mock.patch('hpilo.Ilo') as mock_ilo_ctor:
        mock_ilo = mock_ilo_ctor.return_value
        mock_ilo.get_host_power_status.return_value = 'ON'
        mock_ilo.reset_server.side_effect = Exception('ilo.reset_server failed!')
        mock_ilo.set_host_power.side_effect = Exception('ilo.set_host_power off failed!')

        with pytest.raises(Exception):
            call_command('ilo_reboot', 'test.ilo.hostname', delay=1)

        mock_ilo_ctor.assert_called_once_with('test.ilo.hostname',
                                              login='ilo_dev_username',
                                              password='anything_ilo_password',
                                              timeout=60)

        mock_ilo.get_host_power_status.assert_called_once_with()
        mock_ilo.reset_server.assert_called_once_with()

        mock_ilo.set_host_power.assert_called_once_with(host_power=False)


@pytest.mark.ilo_reboot
def test_ilo_hard_reboot_power_on_fails():
    with mock.patch('hpilo.Ilo') as mock_ilo_ctor:
        mock_ilo = mock_ilo_ctor.return_value
        mock_ilo.get_host_power_status.return_value = 'ON'
        mock_ilo.reset_server.side_effect = Exception('ilo.reset_server failed!')
        mock_ilo.set_host_power.side_effect = [
            None,
            Exception('ilo.set_host_power off failed!')
        ]

        with pytest.raises(Exception):
            call_command('ilo_reboot', 'test.ilo.hostname', delay=1)

        mock_ilo_ctor.assert_called_once_with('test.ilo.hostname',
                                              login='ilo_dev_username',
                                              password='anything_ilo_password',
                                              timeout=60)

        mock_ilo.get_host_power_status.assert_called_once_with()
        mock_ilo.reset_server.assert_called_once_with()

        assert len(mock_ilo.set_host_power.mock_calls) == 2, 'set_host_power not called twice'
        mock_ilo.set_host_power.mock_calls[0] == mock.call(host_power=False)
        mock_ilo.set_host_power.assert_called_with(host_power=True)  # check last call
