# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from uuid import UUID

import mock
import mohawk
import pytest
from django.conf import settings
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
            'id': client_id or settings.TASKCLUSTER_CLIENT_ID,
            'key': access_token or settings.TASKCLUSTER_ACCESS_TOKEN,
            'algorithm': 'sha256',
        },
        ext={},
        url=url,
        content='',
        content_type='application/json',
        method=method,
    ).request_header


def has_cors_headers(response):
    assert response.get('access-control-allow-origin') == 'localhost'
    assert response.get('access-control-allow-methods') == 'OPTIONS,POST'


def test_job_list_returns_cors_headers_for_unauthed_options(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    response = client.options(uri)

    assert response.status_code == 200
    has_cors_headers(response)


def test_job_list_returns_405_for_authed_get(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('GET', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:reboot'],
            'status': 'auth-success',
        }
        response = client.get(url,
                              HTTP_HOST=host,
                              HTTP_CONTENT_TYPE='application/json',
                              HTTP_AUTHORIZATION=auth_header)

        assert response.status_code == 405
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'get',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


@pytest.mark.django_db
def test_job_list_returns_404_for_unknown_worker_id(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='t-yosemite-r7-313',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:reboot'],
            'status': 'auth-success',
        }
        response = client.post(url,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)

        assert response.status_code == 404
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/t-yosemite-r7-313/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


# TODO: test unknown or invalid worker group too?


@pytest.mark.django_db
def test_job_list_returns_404_for_tc_worker_on_machine_we_do_not_manage(client):
    worker = TaskClusterWorker.objects.create(tc_worker_id='tc-worker-1')
    worker.save()

    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:reboot'],
            'status': 'auth-success',
        }

        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)
        print(response.content)
        assert response.status_code == 404
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


@pytest.mark.django_db
def test_job_list_queues_job_for_valid_post(client):
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

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:reboot'],
            'status': 'auth-success',
        }

        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)

        print('response.content', response.content, response.json())

        assert response.status_code == 201
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called

        # assert response.json()['status'] == 'PENDING'

        job_id = UUID(response.json()['task_id'])
        inserted_job = Job.objects.get(pk=job_id)
        assert inserted_job


@pytest.mark.django_db
def test_job_list_requires_auth_header_for_post(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'status': 'auth-failed',
            'message': 'Unauthorized',
        }
        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json')

        print('response.content', response.content, response.json())

        assert response.status_code == 403
        has_cors_headers(response)
        assert response.json() == {'detail': 'Unauthorized'}


@pytest.mark.django_db
def test_job_list_requires_status_in_auth_response(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:reboot'],
        }

        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)

        print('response.content', response.content, response.json())

        assert response.status_code == 403
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


@pytest.mark.django_db
def test_job_list_returns_403_for_status_failed_in_auth_response(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:reboot'],
            'status': 'auth-failed',
        }

        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)

        print('response.content', response.content, response.json())

        assert response.status_code == 403
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


@pytest.mark.django_db
def test_job_list_returns_403_for_wtf_status_in_auth_response(client):
    query_params = urlencode(dict(task_name='reboot'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:reboot'],
            'status': 'wtf',
        }

        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)

        print('response.content', response.content, response.json())

        assert response.status_code == 403
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


@pytest.mark.django_db
def test_job_list_returns_403_for_no_task_name_scopes(client):
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

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': [],
            'status': 'auth-success',
        }

        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)

        print('response.content', response.content, response.json())

        assert response.status_code == 403
        assert response.json() == {'detail': 'You do not have permission to perform this action.'}
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


@pytest.mark.django_db
def test_job_list_returns_403_for_different_task_name_scope(client):
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

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:not-reboot'],
            'status': 'auth-success',
        }

        response = client.post(uri,
                               HTTP_HOST=host,
                               HTTP_CONTENT_TYPE='application/json',
                               HTTP_AUTHORIZATION=auth_header)

        print('response.content', response.content, response.json())

        assert response.status_code == 403
        assert response.json() == {'detail': 'You do not have permission to perform this action.'}
        has_cors_headers(response)

        tc_client.authenticateHawk.assert_called_once_with({
            'method': 'post',
            'resource': '/api/v1/workers/tc-worker-1/group/mdc1/jobs',
            'host': '127.0.0.1',
            'port': 80,
            'authorization': auth_header,
        })
        assert tc_auth_ctor.called


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
