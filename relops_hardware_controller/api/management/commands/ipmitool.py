import logging
import subprocess

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from relops_hardware_controller.api.validators import validate_host


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Runs a command with ipmitool. Raises exception on timeout.'
    doc_url = 'https://linux.die.net/man/1/ipmitool'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'command',
            nargs='+',
            type=str,
            help='IPMI command to run',
        )

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
            help='Selects IPMI interface to use. Supported interfaces that'
            'are compiled in are visible in the usage help output.',
        )
        parser.add_argument(
            '-L',
            dest='privlvl',
            type=str,
            default='OPERATOR',
            help='Force session privilege level. Can be CALLBACK, USER, '
            'OPERATOR, ADMINISTRATOR. Default is OPERATOR.',
        )
        parser.add_argument(
            '-p',
            dest='port',
            type=int,
            default=623,
            help='Remote server UDP port to connect to. Default is 623.',
        )

        # Not an ipmitool option
        parser.add_argument(
            '--timeout',
            dest='timeout',
            default=5,
            type=int,
            help='stop after N seconds',
        )

    def validate_privlvl(self, privlvl):
        if privlvl not in ['CALLBACK', 'USER', 'OPERATOR', 'ADMINISTRATOR']:
            raise ValidationError('Invalid privlvl must be one of CALLBACK, USER, OPERATOR, or ADMINISTRATOR')

    def handle(self, command, *args, **options):
        if not len(command):
            raise ValidationError('ipmitool requires a list of command args.')

        validate_host(options['address'])
        self.validate_privlvl(options['privlvl'])

        call_args = [
            'ipmitool',
            '-H', options['address'],
            '-I', options['interface'],
            '-L', options['privlvl'],
            '-p', str(options['port']),

            '-U', options['username'],
            '-P', options['password'],
        ] + command

        log_command = ' '.join(call_args).replace(options['password'], 'secret')
        logger.info(log_command)

        try:
            return subprocess.check_output(call_args,
                                           stderr=subprocess.STDOUT,
                                           encoding='utf-8',
                                           timeout=options['timeout'])
        except subprocess.TimeoutExpired as e:
            raise subprocess.TimeoutExpired(log_command, timeout=options['timeout'])
