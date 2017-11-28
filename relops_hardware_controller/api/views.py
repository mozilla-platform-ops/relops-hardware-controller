# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from uuid import UUID

import django.http
from rest_framework import (
    status,
)
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Job, Machine, TaskClusterWorker
from .serializers import (
    JobSerializer,
    MachineSerializer,
    TaskClusterWorkerSerializer,
)


from relops_hardware_controller.celery import celery_call_command


logger = logging.getLogger(__name__)


class JobList(APIView):
    """
    Create a new job to queue it.
    """
    def post(self, request, worker_id, worker_group, format=None):
        serializer = JobSerializer(data=dict(
            worker_id=worker_id,
            worker_group=worker_group,
            task_name=request.GET.get('task_name', '')
        ))

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        job_tc_worker_id = serializer.validated_data['worker_id']
        tc_worker = TaskClusterWorker.objects.filter(tc_worker_id=job_tc_worker_id).first()
        if not tc_worker:
            logger.info('Failed to find TC worker id: %s' % job_tc_worker_id)
            return Response(dict(tc_worker_id='TC worker with that ID not found.'),
                            status=status.HTTP_404_NOT_FOUND)

        logger.debug('Found TC worker id: %s' % tc_worker.id)
        serializer.validated_data['tc_worker_id'] = tc_worker.id

        machine = tc_worker.machines.first()
        if not machine:
            return Response(dict(tc_worker_id='Not managing hardware running that TC worker.'),
                            status=status.HTTP_404_NOT_FOUND)
        serializer.validated_data['machine_id'] = machine.id

        # STATUS_QUEUED = Job.TASK_STATUSES[0][0]
        # duplicate_job = Job.objects.filter(status=STATUS_QUEUED,
        #                                    task_name=serializer.validated_data['task_name']).first()
        # if duplicate_job:
        #     return Response(dict(task_name='Task already scheduled for that TC worker\'s machine.'), status=status.HTTP_409_CONFLICT)

        result = celery_call_command.delay(
            serializer.validated_data['task_name'],
            TaskClusterWorkerSerializer(tc_worker).data,
            MachineSerializer(machine).data,
        )
        logger.info('queued a {} task with id: {}'.format(serializer.validated_data['task_name'], result.id))

        serializer.validated_data['task_id'] = result.id
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JobDetail(APIView):
    """
    Returns a job's status.
    """
    def get_object(self, pk):
        try:
            return Job.objects.get(pk=UUID(pk))
        except Job.DoesNotExist:
            raise django.http.Http404

    def get(self, request, pk, format=None):
        serializer = JobSerializer(self.get_object(pk))
        return Response(serializer.data, status=status.HTTP_200_OK)
