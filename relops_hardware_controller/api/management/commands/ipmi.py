import functools
import json

from django.conf import settings
from django.core.management import (
    call_command,
    load_command_class,
)
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Use ipmitool to perform command.'

    def add_arguments(self, parser):
        parser.add_argument(
            'ip',
            type=str,
            help='machine ip address')

        parser.add_argument(
            'command',
            type=str,
            help='IPMI command')

    def handle(self, ip, command, *args, **options):
        ipmi_config = json.load(open(settings.FQDN_TO_IPMI_FILE, 'r'))

        args = []

        parent = ipmi_config[ip]['ipmi'].get('ip', None)
        if parent is not None:
            addr = ipmi_config[ip]['ipmi'].get('addr', None)
            ip = parent
        else:
            addr = None

        hwtype = ipmi_config[parent]['ipmi'].get('type', None)
        remap = ipmi_config['types'].get(hwtype, None)
        if remap is not None:
            args += remap.get('args', None)
            if addr is not None:
                args += remap['map'][addr]
            command = remap['commands'].get(command, [command])

        user = ipmi_config[ip]['ipmi']['user']
        password = ipmi_config[ip]['ipmi']['password']

        run_cmd = functools.partial(
            call_command,
            load_command_class('relops_hardware_controller.api', 'ipmitool'),
            '-H', ip,
            '-U', user,
            '-P', password,
            *args)

        return run_cmd(*command)
