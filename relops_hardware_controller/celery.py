# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import os
import logging
import json
from io import StringIO
import re
import subprocess

import dns.resolver
import dns.name

from celery import Celery

from django.conf import settings
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


def dns_lookup(worker_id):
    try:
        result = res.query(worker_id)
        return result.canonical_name, result[0]
    except Exception as e:
        logging.warn('worker_id dns lookup failed: {}'.format(e))
        return worker_id, None

def send_notice(subject, message, job_data, email=True):
    notify = taskcluster.Notify()

    client_id = job_data['client_id']
    try:
        log_level = logging.getLogger().level
        # Ignore most Notify logging
        logging.getLogger().setLevel(logging.CRITICAL)

        if email:
            link = '{http_origin}/provisioners/{provisioner_id}/worker-types/{worker_type}/workers/{worker_group}/{worker_id}'.format(**job_data)
            text_link_max = 40
            mail_payload = {
                'subject': subject,
                'address': settings.NOTIFY_EMAIL,
                'replyTo': 'relops@mozilla.com',
                'content': message,
                'template': 'fullscreen',
                'link': { 'href':link, 'text':link[:text_link_max] },
            }

            notify.email(mail_payload)

            username = re.search('^mozilla(-auth0/ad\|Mozilla-LDAP\||-ldap\/)([^ @]+)(@mozilla\.com)?$', client_id).group(2)
            notify.email({**mail_payload, 'address': '{}@mozilla.com'.format(username)})
    except Exception as e:
        logging.exception(e)

    try:
        message = '{}: {}'.format(subject, message)
        irc_message_max = 510
        while message:
            chunk = message[:irc_message_max]
            notify.irc({ 'channel': settings.NOTIFY_IRC_CHANNEL, 'message': chunk })
            message = message[irc_message_max:]
    except Exception as e:
        logging.warn(e)

    logging.getLogger().setLevel(log_level)

@app.task
def celery_call_command(job_data):
    command = job_data['task_name']
    logging.debug('command_name:{}'.format(command))
    task = 'ipmi' if command.startswith('ipmi') else command
    logging.debug('task_name:{}'.format(task))

    logging.debug('job_data:{}'.format(job_data))
    (hostname, ip) = dns_lookup(job_data['worker_id'])
    job_data['ip'] = str(ip)

    cmd_class = load_command_class('relops_hardware_controller.api', task)
    logging.debug('cmd_class:{}'.format(cmd_class))

    subject = '{}[{}] {}'.format(job_data['worker_id'], ip, command)
    logging.info(subject)

    if command in ['reboot']:
        message = subject + ' [{}]'.format(job_data['client_id'])
        send_notice(subject, message, job_data, email=False)

    stdout = StringIO()
    try:
        call_command(cmd_class, hostname, json.dumps(job_data), stdout=stdout, stderr=stdout)
    except subprocess.TimeoutExpired as e:
        logging.exception(e)
        message = 'timed out'
    except subprocess.CalledProcessError as e:
        logging.exception(e)
        message = e.output
    except KeyError as e:
        logging.exception(e)
        message = 'Key error: {}'.format(e)
    except Exception as e:
        logging.exception(e)
        message = e
    else:
        message = stdout.getvalue()
        logging.info(message)

    send_notice(subject, message, job_data, email=True)
