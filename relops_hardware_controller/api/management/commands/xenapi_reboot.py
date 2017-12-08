
import contextlib
import logging
import re
import subprocess
import time

import relops_hardware_controller.XenAPI as XenAPI

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_ipv46_address


logger = logging.getLogger(__name__)


@contextlib.contextmanager
def xen_session(api_server_uri, username, password):
    session = XenAPI.Session(uri=api_server_uri)
    try:
        session.login_with_password(username, password)
    except Exception as error:
        logger.info('Error logging into XenAPI session %s', error)

    try:
        yield session
    finally:
        session.xenapi.session.logout()


class Command(BaseCommand):
    help = 'Reboots a server using XenAPI to performa a soft or hard powercycle.'
    doc_url = 'https://wiki.xenproject.org/wiki/Shutting_down_a_VM'

    def add_arguments(self, parser):
        # Positional arguments

        # TODO: validate uuid
        parser.add_argument(
            'host_uuid',
            type=str,
            help='Xen VM UUID to power cycle.',
        )

        # Named (optional) arguments
        parser.add_argument(
            '--delay',
            dest='delay',
            default=5,
            type=int,
            help='Wait N seconds before turning the power back on.',
        )

    def handle(self, host_uuid, *args, **options):
        logger.info("Powercycling %s via XenAPI.", host_uuid)

        with xen_session(settings.XEN_URL,
                         settings.XEN_USERNAME,
                         settings.XEN_PASSWORD) as session:
            vm = session.xenapi.VM.get_by_uuid(host_uuid)
            logger.debug("Found xen VM %s. powering off.", vm)

            try:
                session.xenapi.VM.clean_shutdown(vm)
                logger.debug("clean shutdown of xen VM %s complete.", vm)
            except Exception as error:
                logger.debug("Found xen VM %s. powering off.", vm)
                session.xenapi.VM.hard_shutdown(vm)  # if this fails it raises and error and we logout
                logger.debug("hard shutdown of xen VM %s complete.", vm)

            logger.debug("Power is off, waiting %d seconds before turning it back on.", options['delay'])
            time.sleep(options['delay'])

            session.xenapi.VM.start(vm, False, False)
            logger.info("Powercycle of %s completed.", host_uuid)
            # TODO: poll for VM_guest_metrics?
