## Release Operations Controller or "roller"

This is a service for managing Firefox release operations (RelOps)
hardware. It is a rewrite of [the
build-slaveapi](https://github.com/mozilla/build-slaveapi) based on
[tecken](https://github.com/mozilla-services/tecken) to help migrate
from [buildbot](http://buildbot.net/) to
[taskcluster](https://github.com/taskcluster).


### Architecture

The service consists of a [Django Rest
Framework](http://www.django-rest-framework.org/) web API,
[Redis](https://redis.io/)-backed
[Celery](http://www.celeryproject.org/) queue, and one or more Celery
workers. It should be run behind a VPN.

```
                 +-----------------------------------------------------------------------------+
                 | VPN                                                                         |
                 |                                                                             |
+------------+   |   +--------------+     +----------------+     +-----------+     +--------+  |
|            |   |   |    Roller    |     |    Roller      |     |  Roller   +----->        |  |
|  TC Dash.  +------->    API       +----->    Queue       +----->  Workers  |     |  HW 1  |  |
|            |   |   |              |     |                |     |           <-----+        |  |
|            <-------+              <-----+                <-----+           |     +--------+  |
|            |   |   |              |     |                |     |           |                 |
+------------+   |   +----+---+-----+     +----------------+     |           |     +--------+  |
                 |                                               |           +----->        |  |
                 |                                               |           |     |  HW 2  |  |
                 |                                               |           <-----+        |  |
                 |                                               |           |     +--------+  |
                 |                                               |           |                 |
                 |                                               |           |     +--------+  |
                 |                                               |           +----->        |  |
                 |                                               |           |     |  HW 3  |  |
                 |                                               |           <-----+        |  |
                 |                                               +-----------+     +--------+  |
                 |                                                                             |
                 |                                                                             |
                 +-----------------------------------------------------------------------------+
```


### Data Flow

After a Roller admin [registers an action with
taskcluster](#registering-actions), a sheriff or RelOps operator on [a
worker page of the taskcluster
dashboard](https://tools.taskcluster.net/provisioners/test-dummy-provisioner/worker-types/dummy-worker-packet)
can use the actions dropdown to trigger an action (ping, reboot,
reimage, etc.) on a RelOps managed machine.

Under the hood, the taskcluster dashboard makes a CORS request to
[Roller API](#api), which [checks the Taskcluster authorization
header](https://docs.taskcluster.net/reference/platform/taskcluster-auth/references/api#authenticateHawk)
and scopes then queues a Celery task for the Roller worker to
run. (There is [an open
issue](https://github.com/mozilla-services/relops-hardware-controller/issues/26)
for sending notifications back to the user).

[![data flow sequence diagram](docs/sequence_diagram.png)](https://mermaidjs.github.io/mermaid-live-editor/#/edit/c2VxdWVuY2VEaWFncmFtCiAgICBwYXJ0aWNpcGFudCB0YyBhcyBUYXNrY2x1c3RlciBEYXNoYm9hcmQKICAgIHBhcnRpY2lwYW50IHJhIGFzIFJvbGxlciBBUEkKICAgIHBhcnRpY2lwYW50IHRjYSBhcyBUYXNrY2x1c3RlciBBdXRoIFNlcnZpY2UKICAgIHBhcnRpY2lwYW50IHJxIGFzIFJvbGxlciBRdWV1ZQogICAgcGFydGljaXBhbnQgdyBhcyBSb2xsZXIgV29ya2VyCiAgICBwYXJ0aWNpcGFudCBodyBhcyBSZWxPcHMgTWFjaGluZQogICAgCiAgICBOb3RlIGxlZnQgb2YgdGM6IFNoZXJpZmYgb3IgUmVsT3BzIE9wIGNsaWNrcyBhbiBhY3Rpb24gYnV0dG9uIChyZWJvb3QsIHJlaW1hZ2UsIGxvYW4sIGV0Yy4pCgogICAgICAgIHRjLT4-cmE6IE9QVElPTlMgL2FwaS92MS93b3JrZXJzLyR3b3JrZXJfaWQvZ3JvdXAvJHdvcmtlcl9ncm91cC9qb2JzP3Rhc2tfbmFtZT0kYWN0aW9uCiAgICAgICAgcmEtPj50YzogMjAwIE9LCgogICAgICAgIHRjLT4-cmE6IFBPU1QgL2FwaS92MS93b3JrZXJzLyR3b3JrZXJfaWQvZ3JvdXAvJHdvcmtlcl9ncm91cC9qb2JzP3Rhc2tfbmFtZT0kYWN0aW9uCgogICAgICAgIHJhLT4-dGNhOiBQT1NUIC9hdXRoZW50aWNhdGUtaGF3ayAKICAgICAgICB0Y2EtPj5yYTogMjAwIE9LCgogICAgICAgIHJhLT4-cnE6IHF1ZXVlICRhY3Rpb24gb24gKCR3b3JrZXJfaWQsICR3b3JrZXJfZ3JvdXApCgogICAgICAgIHJhLT4-dGM6IDIwMSBDcmVhdGVkCgogICAgICAgIHJxLT4-dzogcnVuICRhY3Rpb24gb24gb24gKCR3b3JrZXJfaWQsICR3b3JrZXJfZ3JvdXApCgogICAgICAgIHctPj53OiBsb29rIHVwIEZRRE4sIFBEVSwgZXRjLiBmb3IgKCR3b3JrZXJfaWQsICR3b3JrZXJfZ3JvdXApIAoKICAgICAgICB3LT4-aHc6ICRhY3Rpb24KCiAgICAgICAgaHctPj53OiAkYWN0aW9uIGRvbmUKCiAgICAgICAgdy0-PnJxOiAkYWN0aW9uIHRhc2sgZmluaXNoZWQ)


### API

#### POST /api/v1/workers/$worker_id/group/$worker_group/jobs\?task_name\=$task_name

URL for [worker-context Taskcluster
actions](https://docs.taskcluster.net/reference/platform/taskcluster-queue/docs/actions#defining-actions)
that needs to be [registered](registering-actions).

URL params:

* `$worker_id` the Taskcluster Worker ID e.g. `ms1-10`. 1 to 128
  characters in long.

* `$worker_group` the Taskcluster Worker Group e.g. `mdc1` usually a
  datacenter for RelOps hardware. 1 to 128 characters in long.

Query param:

* `$task_name` the celery task to run. Must be in `TASK_NAMES` in `settings.py`

Taskcluster does not POST data/body params.

Example request from Taskcluster:

```
POST http://localhost:8000/api/v1/workers/dummy-worker-id/group/dummy-worker-group/jobs?task_name=ping
Authorization: Hawk ...
```

Example response:

```json
{"task_name":"ping","worker_id":"dummy-worker-id","worker_group":"dummy-worker-group","task_id":"e62c4d06-8101-4074-b3c2-c639005a4430"}
```

Where `task_name`, `worker_id`, and `worker_group` are as defined in the request and `task_id` is the task's [Celery AsyncResult UUID](http://docs.celeryproject.org/en/latest/reference/celery.result.html#celery.result.AsyncResult.id).
