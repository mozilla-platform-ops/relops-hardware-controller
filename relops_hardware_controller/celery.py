# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import os

from celery import Celery
from django.core.management import (
    call_command,
    load_command_class,
)


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'relops_hardware_controller.settings')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Dev')


import configurations  # noqa
configurations.setup()


app = Celery('relops_hardware_controller')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')


MISSING_METHOD_ERROR = '''Django management command {} is missing a
get_args_and_kwargs_from_job method to convert TaskClusterWorker and Machine
json to a list of python args and a dict of python kwargs.'''


@app.task
def celery_call_command(name, tc_worker, machine):
    """
    Loads a Django management command with param name.
    The command then converts the TaskClusterWorker and Machine JSON to
    python args and kwargs and calls the command with them.
    """
    cmd_class = load_command_class('relops_hardware_controller.api', name)

    if not hasattr(cmd_class, 'get_args_and_kwargs_from_job'):
        raise NotImplementedError(MISSING_METHOD_ERROR.format(name))

    args, kwargs = cmd_class.get_args_and_kwargs_from_job(tc_worker, machine)

    return call_command(cmd_class, *args, **kwargs)
