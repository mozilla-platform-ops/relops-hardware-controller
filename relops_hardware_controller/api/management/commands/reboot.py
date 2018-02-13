import functools
import json
import logging
import time
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from django.conf import settings
from django.core.management import (
    call_command,
    load_command_class,
)
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def can_ping(fqdn, count=4, timeout=5):
    ping_cls = load_command_class('relops_hardware_controller.api', 'ping')

    try:
        call_command(ping_cls, fqdn, '-c', count, '-w', timeout)
        logger.debug('pinging %s succeeded', fqdn)
        return True
    except Exception as error:
        logger.info('pinging %s failed: %s', fqdn, error)
        return False


def wait_for_state(fn, timeout, interval):
    '''
    Waits param timeout seconds in param interval seconds for
    predicate function param fn to return True.

    returns True when predicate succeeds
    returns False when predicate fails repeatedly until param timeout is exceeded.
    '''
    state_name = fn.__name__
    logger.info("Waiting %d seconds for %s", timeout, state_name)
    start = time.time()
    while True:
        if fn():
            logger.debug('Entered state %s', state_name)
            return True

        time.sleep(interval)
        elapsed = time.time() - start
        if elapsed >= timeout:
            logger.error("Timeout of %d exceeded waiting for %s", timeout, state_name)
            return False
            break


def reboot_succeeded(fqdn):
    def is_down():
        return not can_ping(fqdn, count=1, timeout=2)

    def is_up():
        return can_ping(fqdn)

    return wait_for_state(is_down, timeout=settings.DOWN_TIMEOUT, interval=1) and \
        wait_for_state(is_up, timeout=settings.UP_TIMEOUT, interval=5)


class Command(BaseCommand):
    help = '''Tries to reboot a machine using ssh, ipmi, snmp, xen, then ilo.
    When all of those methods fail it files a bug in bugzilla.'''

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument(
            'hostname',
            type=str,
            help='A TC worker ID')

        parser.add_argument(
            'command',
            type=str,
            help='A TC worker group')

    def handle(self, hostname, command, *args, **options):
        start = time.time()
        ssh_config = json.load(open(settings.FQDN_TO_SSH_FILE, 'r'))
        ipmi_config = json.load(open(settings.FQDN_TO_IPMI_FILE, 'r'))
        pdu_config = json.load(open(settings.FQDN_TO_PDU_FILE, 'r'))
        xen_config = json.load(open(settings.FQDN_TO_XEN_FILE, 'r'))

        logger.debug('reboot_methods:{}'.format(settings.REBOOT_METHODS))
        stdout = StringIO()
        for reboot_method in settings.REBOOT_METHODS:
            logger.debug('reboot_method:{}'.format(reboot_method))
            if reboot_method == 'ssh_reboot':
                if hostname not in ssh_config:
                    logger.info('skipping ssh reboot of %s since we can\'t'
                                ' find ssh creds in settings.FQDN_TO_SSH_FILE.', hostname)
                    continue

                if not can_ping(hostname):
                    logger.info('skipping ssh reboot of %s since we can\'t ping the machine.', hostname)
                    continue

                reboot_args = [
                    '-l', ssh_config[hostname]['ssh']['user'],
                    '-i', ssh_config[hostname]['ssh']['key_file'],
                    hostname,
                ]
            elif reboot_method == 'ipmi_reset':
                reboot_method = 'ipmi'
                if hostname not in ipmi_config:
                    logger.info('skipping ipmi reset of %s since we can\'t'
                                ' find creds in settings.FQDN_TO_IPMI_FILE.', hostname)
                    continue

                reboot_args = [
                    hostname,
                    'ipmi_reset'
                ]
            elif reboot_method == 'ipmi_cycle':
                reboot_method = 'ipmi'
                if hostname not in ipmi_config:
                    logger.info('skipping ipmi cycle of %s since we can\'t'
                                ' find creds in settings.FQDN_TO_IPMI_FILE.', hostname)
                    continue

                reboot_args = [
                    hostname,
                    'ipmi_cycle'
                ]
            elif reboot_method == 'snmp_reboot':
                if hostname not in pdu_config:
                    logger.info('skipping snmp reboot of %s since we can\'t'
                                ' find creds in settings.FQDN_TO_PDU_FILE.', hostname)
                    continue

                pdu_host, port_args = pdu_config[hostname]['pdu'].rsplit(':', 1)

                reboot_args = [pdu_host] + list(port_args)
            elif reboot_method == 'xenapi_reboot':
                if hostname not in xen_config:
                    logger.info('skipping xenapi reboot of %s since we can\'t'
                                ' find a host uuid in settings.FQDN_TO_XEN_FILE.', hostname)
                    continue

                reboot_args = [xen_config[hostname]['xen_uuid']]
            elif reboot_method == 'ilo_reboot':
                reboot_args = [hostname]
            elif reboot_method == 'file_bugzilla_bug':
                reboot_args = [hostname]
            else:
                raise NotImplementedError()

            # try the reboot method
            try:
                call_command(load_command_class('relops_hardware_controller.api', reboot_method),
                             stdout=stdout,
                             *reboot_args)

                # reboot method succeeded wait for machine to go down then come back up
                if reboot_succeeded(hostname):
                    break
            except Exception as error:
                # try the next reboot method without waiting for the machine to come up
                logger.info('reboot: %s of %s failed with error: %s', reboot_method, hostname, error)
                continue

            # reboot method failed or didn't come up so try the next method

        elapsed = time.time() - start
        return '{}: {}. Completed in {:.3g} seconds'.format(reboot_method, stdout.getvalue().rstrip('\n'), elapsed)
