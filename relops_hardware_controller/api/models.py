# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, you can obtain one at http://mozilla.org/MPL/2.0/.

from django.db import models
from django.conf import settings
import taskcluster


class TaskclusterUser:
    """Stubs out the is_authenticated permission and sets TC scopes.

    NB: not DB backed

    In the future we might want to make this a proper django user and
    map scopes to permissions.
    """

    def __init__(self, scopes, is_authenticated=False):
        self.is_authenticated = is_authenticated
        self.scopes = scopes

    def is_authenticated(self):
        return self.is_authenticated

    def has_required_scopes(self, required_scope_sets):
        # see: https://github.com/taskcluster/taskcluster-client.py#scopes
        return taskcluster.utils.scopeMatch(self.scopes, required_scope_sets)


class TaskClusterWorker(models.Model):
    "A Taskcluster Worker"

    tc_provisioner_id = models.CharField(max_length=128, blank=True)
    tc_worker_type = models.CharField(max_length=128, blank=True)
    tc_worker_group = models.CharField(max_length=128, blank=True)
    tc_worker_id = models.CharField(max_length=128)


class Machine(models.Model):
    "A machine or VM"

    # currently assigned TC workers
    workers = models.ManyToManyField('TaskClusterWorker', related_name='machines')

    host = models.CharField(max_length=255)
    ip = models.GenericIPAddressField()


class Job(models.Model):
    "An action queued or run on a machine"

    # which TC worker we're running the job for
    worker_id = models.CharField(max_length=128)
    tc_worker = models.ForeignKey(
        to='TaskClusterWorker',
        on_delete=models.DO_NOTHING,
        null=False,
    )

    # which machine to run the job on
    machine = models.ForeignKey(
        to='Machine',
        on_delete=models.DO_NOTHING,
        null=False,
    )

    TASK_CHOICES = sorted([(tn, tn) for tn in settings.TASK_NAMES])

    # what to do to the machine
    task_name = models.CharField(
        max_length=64,
        choices=TASK_CHOICES,
        blank=False,
    )

    # job results
    task_id = models.UUIDField(primary_key=True, editable=False)
