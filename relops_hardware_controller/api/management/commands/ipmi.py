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
            'hostname',
            type=str,
            help='machine hostname')

        parser.add_argument(
            'command',
            type=str,
            help='IPMI command')

    def handle(self, hostname, command, *args, **options):
        config = settings.WORKER_CONFIG
        servers = config['servers']
        try:
            server = servers[hostname.split('.')[0]]
            hostname = hostname.split('.')[0]
        except:
            server = servers[hostname]

        args = []

        parent = server.get('parent', None)
        if parent is not None:
            addr = server.get('addr', None)
            hostname = parent
        else:
            addr = None

        hwtype = servers[hostname].get('type', None)
        remap = config['types'].get(hwtype, None)
        if remap is not None:
            args += remap.get('args', None)
            if addr is not None:
                args += remap['map'][addr]
            command = remap['commands'].get(command, [command])

        user = servers[hostname]['user']
        password = servers[hostname]['password']

        run_cmd = functools.partial(
            call_command,
            load_command_class('relops_hardware_controller.api', 'ipmitool'),
            '-H', hostname,
            '-U', user,
            '-P', password,
            *args)

        return run_cmd(*command)
