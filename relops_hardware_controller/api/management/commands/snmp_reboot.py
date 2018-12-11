import logging
import subprocess
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from relops_hardware_controller.api.validators import validate_host


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reboots a server using snmp to powercycle its PDU.'
    doc_url = None

    # I don't fully understand OID, this was cribbed from sut-lib code.
    # http://oid-info.com/get/1.3.6.1.4.1.1718.3.2.3.1.11 describes what
    # this means in a bit more detail. In any case, this is the base OID
    # for doing any reboots via our PDUs - at least until we buy
    # PDUs that are different.

    # ftp://ftp.servertech.com/Pub/SNMP/sentry3/Sentry3OIDTree.txt
    #    |  |     +--outletControlAction(11) *+             |   |       +- .11 .<t> .<i> .<o>
    # <t>: tower
    # <i>: infeed
    # <o>: outlet
    base_oid = "1.3.6.1.4.1.1718.3.2.3.1.11"

    cmds = dict(on='1', off='2', reboot='3')

    port_mappings = {
        "a": "1",
        "b": "2",
        "c": "3"
    }

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'fqdn',
            type=str,
            help='Affected host.',
        )
        parser.add_argument(
            'pdu',
            type=str,
            help='PDU to connect to.',
        )
        parser.add_argument(
            'port',
            type=str,
            help='Wait N seconds before turning the power back on.',
        )

        # Named (optional) arguments

        # Not an snmp option
        parser.add_argument(
            '--delay',
            dest='delay',
            default=0,
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

    def _parse_port(self, port):
        try:
            tower, infeed, outlet = port[0].lower(), port[1].lower(), port[2:]
            for before, after in self.port_mappings.items():
                tower = tower.replace(before, after)
                infeed = infeed.replace(before, after)
            return tower, infeed, ''.join(outlet)
        except IndexError:
            logger.error("Couldn't parse port %s", port)
            raise

    def run_cmd(self, fqdn, cmd, **options):
        config = settings.WORKER_CONFIG

        # Append tower, infeed, and outlet
        oid = "%s.%s.%s.%s" % (self.base_oid, self.tower, self.infeed, self.outlet)

        snmp_community_string = config['snmp_community_string']

        # Example reboot command:
        # snmpset -v 2c -c comm_string 10.26.9.45 1.3.6.1.4.1.1718.3.2.3.1.11.1.1.8 i 3
        command = ' '.join([
            'snmpset',
            '-v', '2c',  # SNMP version to use
            '-c', 'snmp_community_string',
            fqdn,
            oid,
            'i', # cmd value type (i: integer)
            cmd,
        ])
        logger.info(command)

        return subprocess.check_output(command.replace('snmp_community_string', snmp_community_string),
                                       stderr=subprocess.STDOUT,
                                       encoding='utf-8',
                                       shell=True,
                                       timeout=options['timeout'])

    def handle(self, fqdn, pdu, port, *args, **options):
        self.tower, self.infeed, self.outlet = self._parse_port(port)

        logger.info("Powercycling {} via {}.".format(fqdn, pdu))
        output = "SNMP to {}: ".format(pdu)

        if options['delay'] > 0:
            logger.info('Powering down {} ...'.format(fqdn))
            output += self.run_cmd(pdu, self.cmds['off'], **options)

            delay_note = ' wait {}s ... '.format(options['delay'])
            logger.info(delay_note)
            time.sleep(options['delay'])
            output += delay_note

            logger.info('Powering up {} ...'.format(fqdn))
            output += self.run_cmd(pdu, self.cmds['on'], **options)
        else:
            output += self.run_cmd(pdu, self.cmds['reboot'], **options)

        return output
