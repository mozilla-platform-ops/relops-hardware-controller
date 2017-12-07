
import logging
import re
import subprocess
import time

from django.core.management.base import BaseCommand
from django.core.validators import validate_ipv46_address


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reboots a server using snmp to powercycle its PDU.'
    doc_url = None

    # I don't fully understand OID, this was cribbed from sut-lib code.
    # http://oid-info.com/get/1.3.6.1.4.1.1718.3.2.3.1.11 describes what
    # this means in a bit more detail. In any case, this is the base OID
    # for doing any reboots via our PDUs - at least until we buy
    # PDUs that are different.
    base_oid = "1.3.6.1.4.1.1718.3.2.3.1.11"

    cmds = dict(on='1', off='2', reboot='3')

    port_mappings = {
        "A": "1",
        "B": "2",
        "C": "3"
    }

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'fqdn',
            type=str,
            help='Remote fqdn to connect to.',
        )
        parser.add_argument(
            'port',
            nargs='+',
            type=str,
            help='Wait N seconds before turning the power back on.',
        )

        # Named (required) arguments

        # Named (optional) arguments

        # Not an snmp option
        parser.add_argument(
            '--delay',
            dest='delay',
            default=5,
            type=int,
            help='Wait N seconds before turning the power back on.',
        )
        parser.add_argument(
            '--timeout',
            dest='timeout',
            default=60,
            type=int,
            help='Stop each subcommand after N seconds.',
        )

    def validate_host(self, host):
        # from the django URLValidator without unicode
        hostname_re = r'^[\.a-z0-9](?:[\.a-z0-9-]{0,61}[\.a-z0-9])?$'
        if not re.match(hostname_re, host):
            validate_ipv46_address(host)

    def _parse_port(self, port):
        try:
            tower, infeed, outlet = port[0], port[1], port[2:]
            for before, after in self.port_mappings.items():
                tower = tower.replace(before, after)
                infeed = infeed.replace(before, after)
            return tower, infeed, outlet
        except IndexError:
            logger.error("Couldn't parse port %s", port)
            raise

    def run_cmd(self, fqdn, cmd, **options):
        # Append tower, infeed, and outlet
        oid = "%s.%s.%s.%s" % (self.base_oid, self.tower, self.infeed, self.outlet)

        return subprocess.check_output([
                'snmpset',
                '-v', '1',  # SNMP version to use
                '-c', 'private',  # SNMP community string
                fqdn,
                oid,
                'i',
                cmd
            ],
            stderr=subprocess.STDOUT,
            timeout=options['timeout'])

    def handle(self, fqdn, port, *args, **options):
        self.validate_host(fqdn)

        self.tower, self.infeed, self.outlet = self._parse_port(port)

        logger.info("Powercycling %s via PDU.", fqdn)
        self.run_cmd(fqdn, self.cmds['off'], **options)

        logger.debug("Power is off, waiting %d seconds before turning it back on.", options['delay'])
        time.sleep(options['delay'])

        self.run_cmd(fqdn, self.cmds['on'], **options)
        logger.info("Powercycle of %s completed.", fqdn)
