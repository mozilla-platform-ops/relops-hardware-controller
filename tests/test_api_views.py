# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import os
from uuid import UUID

import mohawk
import pytest
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

from relops_hardware_controller.api.models import (
    Job,
    Machine,
    TaskClusterWorker,
)


def get_hawk_auth_header(method, url, client_id=None, access_token=None, content_type='application/json'):
    return mohawk.Sender(
        credentials={
            'id': client_id or os.environ['TASKCLUSTER_CLIENT_ID'],
            'key': access_token or os.environ['TASKCLUSTER_ACCESS_TOKEN'],
            'algorithm': 'sha256',
        },
        ext={},
        url=url,
        content='',
        content_type='application/json',
        method=method,
    ).request_header


def test_job_list_returns_cors_headers_for_get(client):
    query_params = urlencode(dict(task_name='reboot'))
    url = reverse('api:JobList',
                  kwargs=dict(worker_id='t-yosemite-r7-313',
                              worker_group='mdc1')) + '?' + query_params

    response = client.get(url)

    assert response.status_code == 405


def test_job_list_returns_cors_headers_for_options(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri

    response = client.options(uri)

    assert response.status_code == 200
    assert response.get('access-control-allow-origin') == 'localhost'
    assert response.get('access-control-allow-methods') == 'OPTIONS,POST'


@pytest.mark.django_db
def test_job_list_returns_404_for_unknown_worker_id(client):
    query_params = urlencode(dict(worker_id='tc-worker-1',
                                  task_name='reboot'))
    url = reverse('api:JobList',
                  kwargs=dict(worker_id='t-yosemite-r7-313',
                              worker_group='mdc1')) + '?' + query_params

    response = client.post(url)
    print(response.content)
    assert response.status_code == 404


@pytest.mark.django_db
def test_job_list_returns_404_for_tc_worker_on_machine_we_do_not_manage(client):
    worker = TaskClusterWorker.objects.create(tc_worker_id='tc-worker-1')
    worker.save()

    query_params = urlencode(dict(task_name='reboot'))
    url = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    response = client.post(url)
    print(response.content)
    assert response.status_code == 404


@pytest.mark.django_db
def test_job_list_queues_job_for_valid_post(client, monkeypatch, mocker):
    monkeypatch.setenv('TASKCLUSTER_CLIENT_ID', 'email/you@yourdomain.com/tutorial')
    monkeypatch.setenv('TASKCLUSTER_ACCESS_TOKEN', '9dTvVYdzMxAb6qnMPccfQhSzfrMZ1WQ46DgsL_I75S-w')

    tc_client = mocker.patch('taskcluster.Auth')
    tc_client.return_value.authenticateHawk.return_value = {
        'scopes': ['project:relops-hardware-controller:reboot'],
        'status': 'auth-success',
    }

    worker = TaskClusterWorker.objects.create(tc_worker_id='tc-worker-1')
    worker.save()
    machine = Machine.objects.create(host='localhost', ip='127.0.0.1')
    machine.workers.add(worker)
    machine.save()

    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    response = client.post(uri,
                           HTTP_HOST=host,
                           HTTP_CONTENT_TYPE='application/json',
                           HTTP_AUTHORIZATION=auth_header)
    print('response.content', response.content)

    tc_client.return_value.authenticateHawk.assert_called_once_with({
        'method': 'post',
        'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
        'host': '127.0.0.1',
        'port': 80,
        'authorization': auth_header,
    })

    assert response.status_code == 201
    assert response.get('access-control-allow-origin') == 'localhost'
    assert response.get('access-control-allow-methods') == 'OPTIONS,POST'
    # assert response.json()['status'] == 'PENDING'

    job_id = UUID(response.json()['task_id'])
    inserted_job = Job.objects.get(pk=job_id)
    assert inserted_job


@pytest.mark.django_db
def test_job_detail_returns_404_for_nonexistent_job(client):
    url = reverse('api:JobDetail', kwargs=dict(pk='e62c4d06-8101-4074-b3c2-c639005a4430'))
    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_job_detail_returns_job_status(client):
    worker = TaskClusterWorker.objects.create(tc_worker_id='tc-worker-1')
    worker.save()
    machine = Machine.objects.create(host='localhost', ip='127.0.0.1')
    machine.workers.add(worker)
    machine.save()
    job = Job.objects.create(worker_id='tc-worker-1',
                             task_name='reboot',
                             task_id='e62c4d06-8101-4074-b3c2-c639005a4430',
                             tc_worker=worker,
                             machine=machine)
    job.save()

    url = reverse('api:JobDetail', kwargs=dict(pk=job.task_id))
    response = client.get(url)
    assert response.status_code == 200
