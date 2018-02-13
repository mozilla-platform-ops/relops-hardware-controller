
import subprocess

from django.core.management.base import BaseCommand

from relops_hardware_controller.api.validators import validate_host


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

    def handle(self, host, *args, **options):
        validate_host(host)

        call_args = [
            'ping',
            '-c', str(options['count']),
            '-w', str(options['timeout']),
            host,
        ]

        return subprocess.check_output(call_args,
                                       stderr=subprocess.STDOUT,
                                       encoding='utf-8',
                                       timeout=options['timeout'])
