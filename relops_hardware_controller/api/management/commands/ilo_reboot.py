
import logging
import re
import subprocess
import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_ipv46_address
import hpilo


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reboots a server using HP\'s iLO interface.'
    doc_url = 'http://seveas.github.io/python-hpilo/index.html'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'hostname',
            type=str,
            help='Hostname or IP address of the iLO interface.',
        )

        # Named (optional) arguments
        # passed to the ilo client: http://seveas.github.io/python-hpilo/python.html#hpilo.Ilo
        parser.add_argument(
            '--login',
            dest='login',
            type=str,
            help='Loginname to use for authentication, not used for LOCAL connections.',
        )
        parser.add_argument(
            '--password',
            dest='password',
            type=str,
            help='Password to use for authentication, not used for LOCAL connections.',
        )
        parser.add_argument(
            '--timeout',
            dest='timeout',
            type=int,
            default=60,
            help='Timeout for creating connections or receiving data. Default is 60 seconds.',
        )

        parser.add_argument(
            '--delay',
            dest='delay',
            default=5,
            type=int,
            help='Wait N seconds before turning the power back on for hard powercycles.',
        )

    def validate_host(self, host):
        # from the django URLValidator without unicode
        hostname_re = r'^[\.a-z0-9](?:[\.a-z0-9-]{0,61}[\.a-z0-9])?$'
        if not re.match(hostname_re, host):
            validate_ipv46_address(host)


    def handle(self, hostname, *args, **options):
        self.validate_host(hostname)

        logger.info("Powercycling %s via HP iLO. %s", hostname, options)

        username = options.get('login', None) or settings.ILO_USERNAME
        password = options.get('password', None) or settings.ILO_PASSWORD

        ilo = hpilo.Ilo(hostname,
                        login=username,
                        password=password,
                        timeout=options['timeout'])

        power_status = ilo.get_host_power_status()
        logger.debug("Got power status %s for ilo server %s.", power_status, hostname)

        try:
            ilo.reset_server()
            logger.debug("Soft reset of ilo server %s complete.", hostname)
        except Exception as error:
            logger.debug("clean powercycle of ilo server %s failed with error: %s", hostname, error)
            ilo.set_host_power(host_power=False)
            logger.debug("hard shutdown of ilo sever %s complete.", hostname)

            logger.debug("Power is off, waiting %d seconds before turning it back on.", options['delay'])
            time.sleep(options['delay'])

            ilo.set_host_power(host_power=True)

        logger.info("Powercycle of %s completed.", hostname)
