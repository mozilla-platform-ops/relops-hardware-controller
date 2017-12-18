# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf import settings
from django_celery_results.models import TaskResult
from rest_framework import serializers


class TaskResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResult
        fields = ('task_id', 'status', 'date_done', 'result')


class JobSerializer(serializers.Serializer):
    # Celery Task Result ID
    task_id = serializers.UUIDField(
        format='hex_verbose',
        required=False)

    # what task to run on the machine
    task_name = serializers.RegexField(
        r'^({})$'.format('|'.join(settings.TASK_NAMES)),
        required=True)

    # which TC worker we're running the job for
    taskcluster_worker_id = serializers.CharField(
        max_length=128,
        min_length=1,
        required=True)
