
import logging
import re
import subprocess

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_ipv46_address


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
            help='Remote server address, can be IP address or hostname. This option is required for lan and lanplus interfaces.',
            required=True,
        )
        parser.add_argument(
            '-P',
            dest='password',
            type=str,
            help='Remote server password is specified on the command line. If supported it will be obscured in the process list. Note! Specifying the password as a command line option is not recommended.',
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
            help='Selects IPMI interface to use. Supported interfaces that are compiled in are visible in the usage help output.',
        )
        parser.add_argument(
            '-L',
            dest='privlvl',
            type=str,
            default='ADMINISTRATOR',
            help='Force session privilege level. Can be CALLBACK, USER, OPERATOR, ADMINISTRATOR. Default is ADMINISTRATOR.',
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

    def validate_host(self, host):
        # from the django URLValidator without unicode
        hostname_re = r'^[\.a-z0-9](?:[\.a-z0-9-]{0,61}[\.a-z0-9])?$'
        if not re.match(hostname_re, host):
            validate_ipv46_address(host)

    def validate_privlvl(self, privlvl):
        if not privlvl in ['CALLBACK', 'USER', 'OPERATOR', 'ADMINISTRATOR']:
            raise ValidationError('Invalid privlvl must be one of CALLBACK, USER, OPERATOR, or ADMINISTRATOR')

    def handle(self, command, *args, **options):
        if not len(command):
            raise ValidationError('ipmitool requires a list of command args.')

        self.validate_host(options['address'])
        self.validate_privlvl(options['privlvl'])
        # TODO: validate all the other args and command

        call_args = [
            'ipmitool',
            '-H', options['address'],
            '-I', options['interface'],
            '-L', options['privlvl'],
            '-p', str(options['port']),

            '-U', options['username'],
            '-P', options['password'],
        ] + command

        # Raises exceptions for failure, non-zero returncode, and timeouts
        logger.debug('calling ipmitool with args: {}'.format(call_args))

        # for Python 3 decode to bytes to fix:
        # TypeError: endswith first arg must be bytes or a tuple of bytes, not str
        output = subprocess.check_output(call_args,
                                         stderr=subprocess.STDOUT,
                                         timeout=options['timeout'])
        if hasattr(output, 'decode'):
            return output.decode()
        else:
            return output
