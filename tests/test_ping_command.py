# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import subprocess
import pytest

from django.core.exceptions import ValidationError
from django.core.management import (
    call_command,
    load_command_class,
)
from django.core.management.base import CommandError
from django.utils.six import StringIO

from relops_hardware_controller.api.serializers import (
    MachineSerializer,
)
from relops_hardware_controller.api.models import (
    Machine,
)


def test_ping_requires_host():
    with pytest.raises(CommandError):
        call_command('ping')


def test_ping_rejects_invalid_host():
    with pytest.raises(ValidationError):
        call_command('ping', '; echo foo')


@pytest.mark.slowtest
def test_ping_localhost_works():
    call_command('ping', 'localhost', count=1, timeout=1)


@pytest.mark.slowtest
def test_ping_unroutable_ip_timesout():
    with pytest.raises(subprocess.TimeoutExpired):
        # Note: IP won't necessarily be unroutable
        call_command('ping', '198.51.100.0', count=1, timeout=1)


@pytest.mark.slowtest
@pytest.mark.django_db
def test_ping_using_machine_id_works():
    tc_worker = {}
    machine = Machine.objects.create(host='localhost', ip='127.0.0.1')
    machine.save()

    cmd_class = load_command_class('relops_hardware_controller.api', 'ping')

    args, kwargs = cmd_class.get_args_and_kwargs_from_job(tc_worker, MachineSerializer(machine).data)

    call_command(cmd_class, *args, **kwargs)
