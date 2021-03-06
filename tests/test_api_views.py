# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import mock
import mohawk
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.http import urlencode


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
    query_params = urlencode(dict(task_name='ping'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    response = client.options(uri)

    assert response.status_code == 200
    has_cors_headers(response)


def test_job_list_returns_405_for_authed_get(client):
    query_params = urlencode(dict(task_name='ping'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('GET', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:ping'],
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


# TODO: test invalid worker ids and groups too?


def test_job_list_queues_job_for_valid_post(client):
    query_params = urlencode(dict(task_name='ping'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:ping'],
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


def test_job_list_requires_auth_header_for_post(client):
    query_params = urlencode(dict(task_name='ping'))
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


def test_job_list_requires_status_in_auth_response(client):
    query_params = urlencode(dict(task_name='ping'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:ping'],
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


def test_job_list_returns_403_for_status_failed_in_auth_response(client):
    query_params = urlencode(dict(task_name='ping'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:ping'],
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


def test_job_list_returns_403_for_wtf_status_in_auth_response(client):
    query_params = urlencode(dict(task_name='ping'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:ping'],
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


def test_job_list_returns_403_for_no_task_name_scopes(client):
    query_params = urlencode(dict(task_name='ping'))
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


def test_job_list_returns_403_for_different_task_name_scope(client):
    query_params = urlencode(dict(task_name='ping'))
    uri = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    host = '127.0.0.1:9091'
    url = 'http://' + host + uri
    auth_header = get_hawk_auth_header('POST', url)

    with mock.patch('taskcluster.Auth') as tc_auth_ctor:
        tc_client = tc_auth_ctor.return_value
        tc_client.authenticateHawk.return_value = {
            'scopes': ['project:relops-hardware-controller:not-ping'],
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
