# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from rest_framework import serializers
from django_celery_results.models import TaskResult

from .models import Job, Machine, TaskClusterWorker


class TaskClusterWorkerSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskClusterWorker
        fields = '__all__'


class MachineSerializer(serializers.ModelSerializer):

    class Meta:
        model = Machine
        fields = '__all__'


class TaskResultSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskResult
        fields = ('task_id', 'status', 'date_done', 'result')


class JobSerializer(serializers.ModelSerializer):

    task_id = serializers.CharField(required=False)

    class Meta:
        model = Job
        fields = ('task_name', 'worker_id', 'task_id')
