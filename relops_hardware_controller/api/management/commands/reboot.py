import functools
import json
import logging
import time
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
        call_command(ping_cls, fqdn, 'ping', '-c', count, '-w', timeout)
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
    help = '''Tries reboot actions from REBOOT_METHODS environment var.'''

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
        config = settings.WORKER_CONFIG
        try:
            server = config['servers'][hostname.split('.')[0]]
        except:
            server = config['servers'][hostname]

        logger.debug('reboot_methods:{}'.format(settings.REBOOT_METHODS))
        stdout = StringIO()
        for reboot_method in settings.REBOOT_METHODS:
            logger.debug('reboot_method:{}'.format(reboot_method))
            try:
                if reboot_method == 'ssh_reboot':
                    reboot_args = [
                        '-l', server['ssh']['user'],
                        '-i', server['ssh']['key_file'],
                    ]
                elif reboot_method == 'ipmi_reset':
                    reboot_args = [ reboot_method ]
                    reboot_method = 'ipmi'
                elif reboot_method == 'ipmi_cycle':
                    reboot_args = [ reboot_method ]
                    reboot_method = 'ipmi'
                elif reboot_method == 'snmp_reboot':
                    hostname, port_args = server['pdu'].rsplit(':', 1)
                    reboot_args = list(port_args)
                elif reboot_method == 'xenapi_reboot':
                    reboot_args = server['xen']['reboot']
                elif reboot_method == 'ilo_reboot':
                    hostname, reboot_args = server['ilo']
                elif reboot_method == 'file_bugzilla_bug':
                    pass
                else:
                    raise NotImplementedError()

                call_command(load_command_class('relops_hardware_controller.api', reboot_method),
                             hostname,
                             stdout=stdout,
                             *reboot_args)

                if reboot_succeeded(hostname):
                    break
            except Exception as error:
                # try the next reboot method without waiting for the machine to come up
                logger.info('reboot: %s of %s failed with error: %s', reboot_method, hostname, error)
                continue

            # reboot method failed or didn't come up so try the next method

        elapsed = time.time() - start
        return '{}: {}. Completed in {:.3g} seconds'.format(reboot_method, stdout.getvalue().rstrip('\n'), elapsed)
