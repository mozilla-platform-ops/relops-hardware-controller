# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from django.conf import settings
from rest_framework import serializers


class JobSerializer(serializers.Serializer):
    task_id = serializers.UUIDField(
        format='hex_verbose',
        required=False)

    http_origin = serializers.CharField(
        required=False)

    client_id = serializers.RegexField(
        r'^(mozilla.*)$',
        required=False)

    provisioner_id = serializers.CharField(
        required=False)

    worker_type = serializers.CharField(
        required=False)

    worker_group = serializers.CharField(
        required=False)

    worker_id = serializers.CharField(
        max_length=128,
        min_length=1,
        required=True)

    # what task to run on the machine
    task_name = serializers.RegexField(
        r'^({})$'.format('|'.join(settings.TASK_NAMES)),
        required=True)

