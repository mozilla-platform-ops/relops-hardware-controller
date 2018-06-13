import functools
import json
import logging
from datetime import datetime
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
        logger.warn('pinging %s failed: %s', fqdn, error)
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

        parser.add_argument('job_data', type=json.loads)

    def handle(self, hostname, job_data, *args, **options):
        start = time.time()
        result_template = '{command}: {stdout}. Completed in {time:.3g} seconds'
        reboot_attempt_log = '\\n'
        config = settings.WORKER_CONFIG
        try:
            server = config['servers'][hostname.split('.')[0]]
        except:
            server = config['servers'][hostname]

        logger.debug('reboot_methods:{}'.format(settings.REBOOT_METHODS))
        stdout = StringIO()
        for reboot_method in settings.REBOOT_METHODS:
            reboot_args = []
            logger.debug('reboot_method:{}'.format(reboot_method))
            check = reboot_succeeded
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
                    reboot_args = server['pdu'].rsplit(':', 1)
                elif reboot_method == 'xenapi_reboot':
                    reboot_args = server['xen']['reboot']
                elif reboot_method == 'ilo_reboot':
                    hostname, reboot_args = server['ilo']
                elif reboot_method == 'file_bugzilla_bug':
                    result_template = 'failed. bug {stdout}'
                    reboot_args = [
                        json.dumps(job_data),
                        '--log', reboot_attempt_log,
                    ]
                    check = logger.info
                else:
                    raise NotImplementedError()

                call_command(load_command_class('relops_hardware_controller.api', reboot_method),
                             hostname,
                             *reboot_args,
                             stdout=stdout)

                if check(hostname):
                    break

            except Exception as e:
                logger.exception(e)
                reboot_attempt_log += '{} {} {} {}\\n'.format(
                    datetime.utcnow().isoformat(),
                    reboot_method,
                    ' '.join(reboot_args),
                    e.__class__.__name__)

        elapsed = time.time() - start
        return result_template.format(command=reboot_method, stdout=stdout.getvalue().rstrip('\n'), time=elapsed)
