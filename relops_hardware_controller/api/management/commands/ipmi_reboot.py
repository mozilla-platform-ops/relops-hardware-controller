
import functools
import logging
from time import sleep

from django.core.management import (
    call_command,
    load_command_class,
)
from django.core.management.base import BaseCommand, CommandError


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Tries to reboot a machine with ipmitool.'

    def add_arguments(self, parser):
        """ipmitool args except command and with the extra delay arg."""

        # Named (required) arguments
        parser.add_argument(
            '-H',
            dest='address',
            type=str,
            help='Remote server address, can be IP address or hostname. '
            'This option is required for lan and lanplus interfaces.',
            required=True,
        )
        parser.add_argument(
            '-P',
            dest='password',
            type=str,
            help='Remote server password is specified on the command line. '
            'If supported it will be obscured in the process list. Note! '
            'Specifying the password as a command line option is not recommended.',
            required=True,
        )
        parser.add_argument(
            '-U',
            dest='username',
            type=str,
            help='Remote server username, default is NULL user.',
            required=True,
        )

        # Named (optional) arguments
        parser.add_argument(
            '-I',
            dest='interface',
            type=str,
            default='lanplus',
            help='Selects IPMI interface to use. Supported interfaces that are '
            'compiled in are visible in the usage help output.',
        )
        parser.add_argument(
            '-L',
            dest='privlvl',
            type=str,
            default='ADMINISTRATOR',
            help='Force session privilege level. Can be CALLBACK, USER, OPERATOR,'
            ' ADMINISTRATOR. Default is ADMINISTRATOR.',
        )
        parser.add_argument(
            '-p',
            dest='port',
            type=int,
            default=623,
            help='Remote server UDP port to connect to. Default is 623.',
        )

        # Not ipmitool options
        parser.add_argument(
            '--power-status-wait',
            dest='power_status_wait',
            default=120,
            type=int,
            help='Wait N seconds before for the power status to be off.',
        )
        parser.add_argument(
            '--power-status-wait-interval',
            dest='power_status_wait_interval',
            default=15,
            type=int,
            help='Wait N seconds between each check if the power is off.',
        )
        parser.add_argument(
            '--delay',
            dest='delay',
            default=5,
            type=int,
            help='Wait N seconds before turning the power back on.',
        )

    def handle(self, *args, **options):
        run_cmd = functools.partial(
            call_command,
            load_command_class('relops_hardware_controller.api', 'ipmitool'),
            '-H', options['address'],
            '-U', options['username'],
            '-P', options['password'])

        # raises when "fqdn" doesn't have a working IPMI interface
        run_cmd('mc', 'info')
        logger.debug('{} ipmi got mc info attempting soft reboot'.format(options['address']))

        # TODO: check if power is off already and skip powercycle?

        # power cycle
        try:
            run_cmd('power', 'soft')
            logger.debug('{} ipmi soft reboot successful. Waiting for off status.'.format(options['address']))
        except CommandError as error:
            logger.debug('{} ipmi attempting hard reboot soft reboot failed with: {}'.format(options['address'], error))
            run_cmd('power', 'off')
            logger.debug('{} ipmi hard reboot successful. Waiting for off status.'.format(options['address']))

        # poll until 'off' in power status result or 120 seconds elapses
        seconds_waited = 0
        wait_interval = options['power_status_wait_interval']
        while True:
            try:
                output = run_cmd('power', 'status')
                logger.debug('{} ipmi power status output: {!r}'.format(options['address'], output))
                if 'off' in output:
                    logger.debug('{} ipmi found off in power status.'.format(options['address']))
                    break
            except CommandError as error:  # TODO: make this more specific
                logger.debug('{} ipmi power status command raised:'
                             ' {}'.format(options['address'], error))

            if seconds_waited >= options['power_status_wait']:
                logger.debug('{} ipmi did not get power status off in {} '
                             'seconds.'.format(options['address'], seconds_waited))
                break

            sleep(wait_interval)
            seconds_waited += wait_interval

        # sleep for configurable delay (default 5s)
        logger.debug('{} ipmi waiting for {} seconds before turning back'
                     ' on.'.format(options['address'], options['delay']))
        sleep(options['delay'])

        run_cmd('power', 'on')  # turn back on
        logger.debug('{} ipmi powering back on.'.format(options['address']))
