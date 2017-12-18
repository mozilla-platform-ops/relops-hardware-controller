
import re
import subprocess

from django.core.management.base import BaseCommand
from django.core.validators import validate_ipv46_address


class Command(BaseCommand):
    help = 'Tries to ICMP ping the host. Raises for exceptions for a lost packet or timeout.'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'host',
            type=str,
            help='A host',
        )

        # Named (optional) arguments
        parser.add_argument(
            '-c',
            dest='count',
            default=4,
            type=int,
            help='stop after sending NUMBER packets',
        )
        parser.add_argument(
            '-w',
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

    def handle(self, host, *args, **options):
        self.validate_host(host)

        call_args = [
            'ping',
            '-c', str(options['count']),
            '-w', str(options['timeout']),
            host,
        ]

        # Raises exceptions for failure, non-zero returncode, and timeouts
        subprocess.run(
            call_args,
            timeout=options['timeout'],
            check=True)
