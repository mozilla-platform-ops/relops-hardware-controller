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


@app.task
def celery_call_command(job_data):
    """Loads a Django management command with task_name and passes it

    the single arg of a serialized job dict e.g.

    {
        'worker_id': 'tc_worker_id',
        'worker_group': 'tc_worker_group',
        'task_name': 'reboot'
    }
    """
    cmd_class = load_command_class('relops_hardware_controller.api', job_data['task_name'])
    return call_command(cmd_class, job_data)
