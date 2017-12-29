

import functools
import json
import logging
import time

from django.conf import settings
from django.core.management import (
    call_command,
    load_command_class,
)
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def get_fqdn(worker_id, worker_group):
    '''
    Builds a fqdn from serialized job TC worker id and worker group with format:

    <shortname>.(win)?test.releng.<datacenter>.mozilla.com
    '''
    # TODO: handle {worker_id}.wintest... too
    return '{worker_id}.test.releng.{worker_group}.mozilla.com'\
        .format(worker_id=worker_id, worker_group=worker_group)


def can_ping(fqdn, count=4, timeout=5):
    ping_cls = load_command_class('relops_hardware_controller.api', 'ping')
    ping = functools.partial(call_command, ping_cls, fqdn, '-c', count, '-w', timeout)

    # try to ping the machine
    try:
        ping()
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
            'worker_id',
            type=str,
            help='A TC worker ID')

        parser.add_argument(
            'worker_group',
            type=str,
            help='A TC worker group')

    def handle(self, worker_id, worker_group, *args, **options):
        fqdn = get_fqdn(worker_id, worker_group)
        ssh_config = json.load(open(settings.FQDN_TO_SSH_FILE, 'r'))
        ipmi_config = json.load(open(settings.FQDN_TO_IPMI_FILE, 'r'))
        pdu_config = json.load(open(settings.FQDN_TO_PDU_FILE, 'r'))
        xen_config = json.load(open(settings.FQDN_TO_XEN_FILE, 'r'))

        for reboot_method in settings.REBOOT_METHODS:
            if reboot_method == 'ssh_reboot':
                if not can_ping(fqdn):
                    logger.info('skipping ssh reboot of %s since we can\'t ping the machine.', fqdn)
                    continue

                if fqdn not in ssh_config:
                    logger.info('skipping ssh reboot of %s since we can\'t'
                                ' find ssh creds in settings.FQDN_TO_SSH_FILE.', fqdn)
                    continue

                reboot_args = [
                    '-l', ssh_config[fqdn]['ssh']['user'],
                    '-i', ssh_config[fqdn]['ssh']['key_file'],
                    fqdn,
                ]
            elif reboot_method == 'ipmi_reboot':
                if fqdn not in ipmi_config:
                    logger.info('skipping ipmi reboot of %s since we can\'t'
                                ' find creds in settings.FQDN_TO_IPMI_FILE.', fqdn)
                    continue

                reboot_args = [
                    '-H', fqdn,
                    '-U', ipmi_config[fqdn]['ipmi']['user'],
                    '-P', ipmi_config[fqdn]['ipmi']['password'],
                ]
            elif reboot_method == 'snmp_reboot':
                if fqdn not in pdu_config:
                    logger.info('skipping snmp reboot of %s since we can\'t'
                                ' find creds in settings.FQDN_TO_PDU_FILE.', fqdn)
                    continue

                pdu_host, port_args = pdu_config[fqdn]['pdu'].rsplit(':', 1)

                reboot_args = [pdu_host] + list(port_args)
            elif reboot_method == 'xenapi_reboot':
                if fqdn not in xen_config:
                    logger.info('skipping xenapi reboot of %s since we can\'t'
                                ' find a host uuid in settings.FQDN_TO_XEN_FILE.', fqdn)
                    continue

                reboot_args = [xen_config[fqdn]['xen_uuid']]
            elif reboot_method == 'ilo_reboot':
                reboot_args = [fqdn]
            elif reboot_method == 'file_bugzilla_bug':
                reboot_args = [fqdn]
            else:
                raise NotImplementedError()

            # try the reboot method
            try:
                call_command(load_command_class('relops_hardware_controller.api', reboot_method),
                             *reboot_args)

                # reboot method succeeded wait for machine to go down then come back up
                if reboot_succeeded(fqdn):
                    break
            except Exception as error:
                # try the next reboot method without waiting for the machine to come up
                logger.info('reboot: %s of %s failed with error: %s', reboot_method, fqdn, error)
                continue

            # reboot method failed or didn't come up so try the next method
