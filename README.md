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


### Operations

#### Running

To run the service fetch the roller image and redis:

```console
docker pull mozilla/relops-hardware-controller
docker pull redis:3.2
```

The roller web API and worker images run from one docker container.

Copy the example settings file (if you don't have the repo checked out: `wget https://raw.githubusercontent.com/mozilla-services/relops-hardware-controller/master/.env-dist`):

```console
cp .env-dist .env
```

**In production, use --env ENV_FOO=bar instead of an env var file.**

Then docker run the containers:

```console
docker run --name roller-redis --expose 6379 -d redis:3.2
docker run --name roller-web -p 8000:8000 --link roller-redis:redis --env-file .env mozilla/relops-hardware-controller -d web
docker run --name roller-worker --link roller-redis:redis --env-file .env mozilla/relops-hardware-controller -d worker
```

Check that it's running:

```console
docker ps
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                    NAMES
f45d4bcc5c3a        roller:build        "/bin/bash /app/bi..."   3 minutes ago       Up 3 minutes        8000/tcp                 roller-worker
c48a68ad887c        roller:build        "/bin/bash /app/bi..."   3 minutes ago       Up 3 minutes        0.0.0.0:8000->8000/tcp   roller-web
d1750321c4df        redis:3.2           "docker-entrypoint..."   9 minutes ago       Up 8 minutes        6379/tcp                 roller-redis

curl -w '\n' -X POST -H 'Accept: application/json' -H 'Content-Type: application/json' http://localhost:8000/api/v1/workers/tc-worker-1/group/ndc2/jobs\?task_name\=ping
<h1>Bad Request (400)</h1>

docker logs roller-web
[2018-01-10 08:27:23 +0000] [5] [INFO] Starting gunicorn 19.7.1
[2018-01-10 08:27:23 +0000] [5] [INFO] Listening at: http://0.0.0.0:8000 (5)
[2018-01-10 08:27:23 +0000] [5] [INFO] Using worker: egg:meinheld#gunicorn_worker
[2018-01-10 08:27:23 +0000] [8] [INFO] Booting worker with pid: 8
[2018-01-10 08:27:23 +0000] [10] [INFO] Booting worker with pid: 10
[2018-01-10 08:27:23 +0000] [12] [INFO] Booting worker with pid: 12
[2018-01-10 08:27:23 +0000] [13] [INFO] Booting worker with pid: 13
172.17.0.1 - - [10/Jan/2018:08:31:46 +0000] "POST /api/v1/workers/tc-worker-1/group/ndc2/jobs HTTP/1.1" 400 26 "-" "curl/7.43.0"
172.17.0.1 - - [10/Jan/2018:08:31:46 +0000] "- - HTTP/1.0" 0 0 "-" "-"
```

##### Configuration

Roller uses an environment variable called `DJANGO_CONFIGURATION` that
defaults to `Prod` to pick which [composable
configuration](https://django-configurations.readthedocs.io/en/stable/)
to use.

In addition to the usual Django, Django Rest Framework and Celery settings we have:

###### Web Server Environment Variables

* `TASKCLUSTER_CLIENT_ID`
  The Taskcluster CLIENT_ID to authenticate with

* `TASKCLUSTER_ACCESS_TOKEN`
  The Taskcluster access token to use

###### Web Server Settings

* `CORS_ORIGIN`
  Which origin to allow CORS requests from (returning CORS access-control-allow-origin header)
  Defaults to `localhost` in Dev and `tools.taskcluster.net` in Prod

* `TASK_NAMES`
  List of management commands can be run from the API. Defaults to `ping` in Dev and `reboot` in prod.

###### Worker Environment Variables

* `BUGZILLA_URL`
  URL for the Bugzilla REST API e.g. https://landfill.bugzilla.org/bugzilla-5.0-branch/rest/

* `BUGZILLA_API_KEY`
  API for using the [Bugzilla REST API](https://wiki.mozilla.org/Bugzilla:REST_API)

* `XEN_URL`
  URL for the Xen RPC API http://xapi-project.github.io/xen-api/usage.html

* `XEN_USERNAME`
  Username to authenticate with the Xen management server

* `XEN_PASSWORD`
  Password to authenticate with the Xen management server

* `ILO_USERNAME`
  Username to authenticate with the HP iLO management interface

* `ILO_PASSWORD`
  Password to authenticate with the HP iLO management interface

* `FQDN_TO_SSH_FILE`
  Path to the JSON file mapping FQDNs to SSH username and key file paths example in [settings.py](https://github.com/mozilla-services/relops-hardware-controller/blob/master/relops_hardware_controller/settings.py).
  The ssh keys need to [be mounted](https://docs.docker.com/engine/reference/commandline/run/#mount-volume--v-read-only) when docker is run. For example with `docker run -v host-ssh-keys:.ssh --name roller-worker`.
  The ssh user on the target machine should use [ForceCommand](https://www.freebsd.org/cgi/man.cgi?sshd_config(5)) to only allow the command `reboot` or `shutdown`
  default `ssh.json`

* `FQDN_TO_IPMI_FILE`
  Path to the JSON file mapping FQDNs to IPMI username and passwords example in [settings.py](https://github.com/mozilla-services/relops-hardware-controller/blob/master/relops_hardware_controller/settings.py)
  default `ipmi.json`

* `FQDN_TO_PDU_FILE`
  Path to the JSON file mapping FQDNs to pdu SNMP sockets example in [settings.py](https://github.com/mozilla-services/relops-hardware-controller/blob/master/relops_hardware_controller/settings.py)
  default `pdus.json`

* `FQDN_TO_XEN_FILE`
  Path to the JSON file mapping FQDNs to Xen VM UUIDs example in [settings.py](https://github.com/mozilla-services/relops-hardware-controller/blob/master/relops_hardware_controller/settings.py)
  default `xen.json`


#### Testing Actions

To list available actions/management commands:

```console
docker run --name roller-runner --link roller-redis:redis --env-file .env roller:build manage.py

Type 'manage.py help <subcommand>' for help on a specific subcommand.

Available subcommands:

[api]
    file_bugzilla_bug
    ilo_reboot
    ipmi_reboot
    ipmitool
    ping
    reboot
    register_tc_actions
    snmp_reboot
    ssh_reboot
    xenapi_reboot
```

To show help for one:

```console
docker run --link roller-redis:redis --env-file .env roller:build manage.py ping --help
usage: manage.py ping [-h] [--version] [-v {0,1,2,3}] [--settings SETTINGS]
                      [--pythonpath PYTHONPATH] [--traceback] [--no-color]
                      [-c COUNT] [-w TIMEOUT] [--configuration CONFIGURATION]
                      host

Tries to ICMP ping the host. Raises for exceptions for a lost packet or
timeout.

positional arguments:
  host                  A host

optional arguments:
  -h, --help            show this help message and exit
...
  -c COUNT              stop after sending NUMBER packets
  -w TIMEOUT            stop after N seconds
...
```

And test it:

```console
docker run --link roller-redis:redis --env-file .env roller:build manage.py ping -c 4 -w 5 localhost
PING localhost (127.0.0.1) 56(84) bytes of data.
64 bytes from localhost (127.0.0.1): icmp_seq=1 ttl=64 time=0.042 ms
64 bytes from localhost (127.0.0.1): icmp_seq=2 ttl=64 time=0.074 ms
64 bytes from localhost (127.0.0.1): icmp_seq=3 ttl=64 time=0.086 ms
64 bytes from localhost (127.0.0.1): icmp_seq=4 ttl=64 time=0.074 ms

--- localhost ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3141ms
rtt min/avg/max/mdev = 0.042/0.069/0.086/0.016 ms
```

In general, we should be able to run tasks as a manage.py commands and
tasks should do the same thing when run as commands as via the API.

#### Adding a new machine or VM

1. Create an ssh key and user limited to `shutdown` or `reboot` with ForceCommand on the target hardware
1. Add the ssh key and user to the mounted worker ssh keys directory
1. Add the machine's FQDN to any relevant `FQDN_TO_*` config files


