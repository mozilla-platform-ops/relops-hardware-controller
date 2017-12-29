# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError


def test_reboot_skips_ssh_reboot_when_ping_fails(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['ssh_reboot']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output') as check_output_mock, \
            patch('time.sleep'):

        run_mock.side_effect = CommandError()  # i.e. ping fails

        call_command('reboot', 'test_tc_worker_id', 'dne-dc-1')

        run_mock.assert_called_once_with([
            'ping', '-c', '4', '-w', '5',
            'test_tc_worker_id.test.releng.dne-dc-1.mozilla.com'], check=True, timeout=5)

        assert not check_output_mock.called


def test_reboot_skips_ssh_reboot_when_missing_creds(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['ssh_reboot']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output') as check_output_mock, \
            patch('time.sleep'):

        run_mock.return_value = 0  # i.e. ping succeeds

        call_command('reboot', 'dne_test_tc_worker_id', 'dne-dc-1')

        assert not check_output_mock.called


# ping succeeds then fails then succeeds again
# to simulate machine going down and coming back up
ping_success_side_effects = [
    None,
    None,
    CommandError("Ping failed!"),
    CommandError("Ping failed!"),
    None,
]


def test_reboot_ssh_success(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['ssh_reboot']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output') as check_output_mock, \
            patch('time.sleep'):

        run_mock.side_effect = ping_success_side_effects

        call_command('reboot', 'test_tc_worker_id', 'dne-dc-1')

        assert run_mock.call_count == 5

        check_output_mock.assert_called_once_with([
            'ssh',
            '-o', 'PasswordAuthentication=no',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-i', '~/.ssh/test_ipmitool_pass.key',
            '-l', 'reboot-forcecommand-user',
            '-p', '22',
            'test_tc_worker_id.test.releng.dne-dc-1.mozilla.com', 'reboot'], stderr=-2, timeout=5)


def test_reboot_ipmi_success(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['ipmi_reboot']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output') as check_output_mock, \
            patch('time.sleep'):

        run_mock.side_effect = ping_success_side_effects

        call_command('reboot', 'test_tc_worker_id', 'dne-dc-1')

        assert run_mock.call_count == 5

        # just check the last call since specifics tested in ipmi_reboot tests
        check_output_mock.assert_called_with([
            'ipmitool',
            '-H', 'test_tc_worker_id.test.releng.dne-dc-1.mozilla.com',
            '-I', 'lanplus',
            '-L', 'ADMINISTRATOR',
            '-p', '623',
            '-U', 'test_reboot_user',
            '-P', 'test_ipmitool_pass',
            'power', 'on'], stderr=-2, timeout=5)


def test_reboot_snmp_success(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['snmp_reboot']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output') as check_output_mock, \
            patch('time.sleep'):

        run_mock.side_effect = ping_success_side_effects

        call_command('reboot', 'test_tc_worker_id', 'dne-dc-1')

        assert run_mock.call_count == 5

        # just check the last call since specifics tested in ipmi_reboot tests
        check_output_mock.assert_called_with([
            'snmpset',
            '-v', '1',
            '-c', 'private',
            'pdu1.r201-6.ops.releng.dne1.mozilla.com',
            "1.3.6.1.4.1.1718.3.2.3.1.11.1.1.['1']", 'i', '1'], stderr=-2, timeout=60)


def test_reboot_xenapi_success(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['xenapi_reboot']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output'), \
            patch('time.sleep'), \
            patch('relops_hardware_controller.api.management.commands'
                  '.xenapi_reboot.XenAPI.Session') as mock_session_ctor:

        run_mock.side_effect = ping_success_side_effects

        call_command('reboot', 'test_tc_worker_id', 'dne-dc-1')

        # just check one call since specifics tested in xenapi_reboot tests
        mock_session_ctor.assert_called_once_with(uri='https://xenapiserver/')

        assert run_mock.call_count == 5


def test_reboot_ilo_success(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['ilo_reboot']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output'), \
            patch('time.sleep'), \
            patch('hpilo.Ilo') as mock_ilo_ctor:

        mock_ilo = mock_ilo_ctor.return_value
        mock_ilo.get_host_power_status.return_value = 'ON'
        mock_ilo.reset_server.side_effect = Exception('ilo.reset_server failed!')

        run_mock.side_effect = ping_success_side_effects

        call_command('reboot', 'test_tc_worker_id', 'dne-dc-1')

        # just check one call since specifics tested in ilo_reboot tests
        mock_ilo.reset_server.assert_called_once_with()

        assert run_mock.call_count == 5


def test_reboot_bugzilla_success(settings):
    settings.DOWN_TIMEOUT = 1
    settings.UP_TIMEOUT = 1
    settings.REBOOT_METHODS = ['file_bugzilla_bug']

    with patch('subprocess.run') as run_mock, \
            patch('subprocess.check_output'), \
            patch('time.sleep'), \
            patch('requests.post') as post_mock:

        run_mock.side_effect = ping_success_side_effects

        call_command('reboot', 'test_tc_worker_id', 'dne-dc-1')

        # just check one call since specifics tested in file_bugzilla_bug tests
        assert post_mock.called
        assert run_mock.call_count == 5
