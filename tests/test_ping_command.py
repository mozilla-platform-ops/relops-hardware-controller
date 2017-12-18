# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import subprocess
import pytest

from django.core.exceptions import ValidationError
from django.core.management import (
    call_command,
)
from django.core.management.base import CommandError


def test_ping_requires_host():
    with pytest.raises(CommandError):
        call_command('ping')


def test_ping_rejects_invalid_host():
    with pytest.raises(ValidationError):
        call_command('ping', '; echo foo')


@pytest.mark.requires_worker
def test_ping_localhost_works():
    call_command('ping', 'localhost', count=1, timeout=1)


@pytest.mark.skip(reason='IP isn\'t always unroutable')
@pytest.mark.requires_worker
def test_ping_unroutable_ip_timesout():
    with pytest.raises(subprocess.TimeoutExpired):
        call_command('ping', '198.51.100.0', count=1, timeout=1)
