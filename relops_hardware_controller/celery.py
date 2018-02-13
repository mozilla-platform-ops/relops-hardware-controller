# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import os
import logging
import json
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import re

import dns.resolver
import dns.name

from celery import Celery
from django.core.management import (
    call_command,
    load_command_class,
)

import taskcluster


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

search = [dns.name.from_text('')]
for os in ['', 'win']:
    for datacenter in ['mdc1', 'mdc2', 'scl3']:
        search.append(dns.name.from_text('{os}test.releng.{datacenter}.mozilla.com'.format(
            datacenter=datacenter,
            os=os,
        )))
res = dns.resolver.get_default_resolver()
res.search = search


def get_hostname(worker_id):
    logging.debug('worker_id: {}'.format(worker_id))
    try:
        ip = res.query(worker_id)
        logging.debug('worker_id -> ip: {}'.format(ip[0]))
        return ip[0]
    except Exception as e:
        logging.warn('worker_id -> ip. dns lookup failed: {}'.format(e))
        return worker_id


@app.task
def celery_call_command(job_data):
    """Loads a Django management command with task_name
    """

    command = job_data['task_name']
    logging.debug('command_name:{}'.format(command))
    task = 'ipmi' if command.startswith('ipmi') else command
    logging.debug('task_name:{}'.format(task))

    logging.debug('job_data:{}'.format(job_data))
    hostname=get_hostname(job_data['worker_id'])
    cmd_class = load_command_class('relops_hardware_controller.api', task)
    logging.debug('cmd_class:{}'.format(cmd_class))

    stdout = StringIO()
    call_command(cmd_class, hostname, command, stdout=stdout)

    notify = taskcluster.Notify()
    subject = '{}[{}] {}'.format(job_data['worker_id'], hostname, command)
    message = stdout.getvalue()
    link = '{http_origin}/provisioners/{provisioner_id}/worker-types/{worker_type}/workers/{worker_group}/{worker_id}'.format(**job_data)

    client_id = job_data['client_id']
    try:
        username = re.search('^mozilla-ldap\/([^ @]+)@mozilla\.com$', client_id).group(1)

        mail_payload = {
            'subject': subject,
            'address': '{}@mozilla.com'.format(username),
            'replyTo': 'relops@mozilla.com',
            'content': message,
            'link': { 'href':link, 'text':link[:40] },
        }
        notify.email(mail_payload)

        l = 500 - len(subject)
        irc_payload = {
            'user': username,
            'message': subject + (message[:l] + ' ...') if len(message) > l else message,
        }
        notify.irc(irc_payload)
    except Exception as e:
        logging.warn(e)
        pass
