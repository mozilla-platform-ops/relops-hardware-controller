# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import pytest

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.bugzilla
def test_file_bugzilla_bug_requires_host():
    with pytest.raises(CommandError):
        call_command('file_bugzilla_bug')


@pytest.mark.bugzilla
def test_file_bugzilla_bug_rejects_invalid_host():
    with pytest.raises(ValidationError):
        call_command('file_bugzilla_bug', '; echo foo')


@pytest.mark.bugzilla
def test_file_bugzilla_bug_localhost_works():
    with mock.patch('requests.post') as post_mock:
        post_mock.return_value.json.return_value = {'id': 42}
        post_mock.return_value.content = 'mock bugzilla response'

        call_command('file_bugzilla_bug', 'localhost')

        assert post_mock.called
        post_mock.assert_called_once_with(
            'https://landfill.bugzilla.org/bugzilla-5.0-branch/rest/bug',
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                'Bugzilla_api_key': 'anything',
                'product': 'Infrastructure & Operations',
                'component': 'DCOps',
                'summary': 'localhost is unreachable',
                'version': 'other',
                'op_sys': 'All',
                'platform': 'All',
            })


@pytest.mark.bugzilla
def test_file_bugzilla_bug_error_response():
    with mock.patch('requests.post') as post_mock:
        post_mock.return_value.content = 'mock bugzilla response'
        post_mock.return_value.raise_for_status.side_effect = Exception('Bad Request')

        with pytest.raises(Exception):
            call_command('file_bugzilla_bug', 'localhost')

        assert post_mock.called
