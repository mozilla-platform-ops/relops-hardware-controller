# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from uuid import UUID

import pytest
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

from relops_hardware_controller.api.models import (
    Job,
    Machine,
    TaskClusterWorker,
)


def test_job_list_returns_405_for_get(client):
    query_params = urlencode(dict(task_name='reboot'))
    url = reverse('api:JobList',
                  kwargs=dict(worker_id='t-yosemite-r7-313',
                              worker_group='mdc1')) + '?' + query_params

    response = client.get(url)

    assert response.status_code == 405


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
def test_job_list_queues_job_for_valid_post(client):
    worker = TaskClusterWorker.objects.create(tc_worker_id='tc-worker-1')
    worker.save()
    machine = Machine.objects.create(host='localhost', ip='127.0.0.1')
    machine.workers.add(worker)
    machine.save()

    query_params = urlencode(dict(task_name='reboot'))
    url = reverse('api:JobList',
                  kwargs=dict(worker_id='tc-worker-1',
                              worker_group='mdc1')) + '?' + query_params

    response = client.post(url)
    print(response.content)
    assert response.status_code == 201
    # assert response.json()['status'] == 'QUEUED'

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
