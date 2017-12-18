## relops-hardware-controller aka Release Operations Controller or "roller"

A service for managing Fx release operations (RelOps) hardware and
rewrite of [the
build-slaveapi](https://github.com/mozilla/build-slaveapi) to help
migrate from [buildbot](http://buildbot.net/) to
[taskcluster](https://github.com/taskcluster). The code is based on
[tecken](https://github.com/mozilla-services/tecken).

### Architecture

```
                 +-----------------------------------------------------------------------------+
                 | VPN                                                                         |
                 |                                                                             |
+------------+   |   +--------------+     +----------------+     +-----------+     +--------+  |
|            |   |   |              |     |                |     |           +----->        |  |
|  TC Dash.  +------->      API     +----->     Queue      +----->  Workers  |     |  HW 1  |  |
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

### Data flow

![sequence diagram from https://mermaidjs.github.io/mermaid-live-editor/#/edit/c2VxdWVuY2VEaWFncmFtCiAgICBwYXJ0aWNpcGFudCB0YyBhcyBVc2VyIGxvZ2dlZCBpbnRvIFRhc2tjbHVzdGVyIERhc2hib2FyZCAKICAgIHBhcnRpY2lwYW50IHJhIGFzIFJvbGxlciBBUEkKICAgIHBhcnRpY2lwYW50IHJkYiBhcyBSb2xsZXIgREIKICAgIHBhcnRpY2lwYW50IHJxIGFzIFJvbGxlciBRdWV1ZQogICAgcGFydGljaXBhbnQgdyBhcyBXb3JrZXIKICAKICAgIE5vdGUgbGVmdCBvZiB0YzogU2hlcmlmZiBvciBSZWxPcHMgT3AgY2xpY2tzIGFuIGFjdGlvbiBidXR0b24gKHJlYm9vdCwgcmVpbWFnZSwgbG9hbiwgZXRjLikKCiAgICAgICAgdGMtPj5yYTogT1BUSU9OUyAvYXBpL3YxL2pvYnM_dGFza19uYW1lPSRhY3Rpb24mdGNfd29ya2VyX2lkPXRjLXdvcmtlci11bm8KICAgICAgICByYS0-PnRjOiAyMDAgT0sKCiAgICAgICAgdGMtPj5yYTogUE9TVCAvYXBpL3YxL2pvYnM_dGFza19uYW1lPSRhY3Rpb24mdGNfd29ya2VyX2lkPXRjLXdvcmtlci11bm8KCiAgICAgICAgcmEtPj5yZGI6IEZpbmQgbWFjaGluZSBmb3IgJ3RjLXdvcmtlci11bm8nCiAgICAgICAgcmRiLT4-cmE6IEZvdW5kIG1hY2hpbmUgbTEgCgogICAgICAgIHJhLT4-cnE6IHF1ZXVlICRhY3Rpb24gb24gbTE_CiAgICAgICAgcnEtPj5yYTogcXVldWVkIHdpdGggdGFza19pZCAyCgogICAgICAgIHJxLT4-dzogcnVuICRhY3Rpb24gb24gbTEKCiAgICAgICAgcmEtPj5yZGI6IHNhdmUgam9iPwogICAgICAgIHJkYi0-PnJhOiBzYXZlZCEKCiAgICAgICAgcmEtPj50YzogMjAxIENyZWF0ZWQgeyJ0YXNrX2lkIjogMi4uLn0gCiAgICAgICAgdGMtPj5yYTogR0VUIC9hcGkvdjEvam9icy8yCiAgICAgICAgcmEtPj50YzogMjAwIE9LIHtzdGF0dXM6ICJSVU5OSU5HIn0KCiAgICAgICAgdy0-PnJxOiBGaW5pc2hlZCAkYWN0aW9uIG9uIG0xCgogICAgICAgIHRjLT4-cmE6IEdFVCAvYXBpL3YxL2pvYnMvMgogICAgICAgIHJhLT4-dGM6IDIwMCBPSyB7c3RhdHVzOiAiQ09NUExFVEUifQo](docs/sequence_diagram.png)

### API (TODO: add schemas)

#### POST /api/v1/jobs\?tc_worker_id\=tc-worker-1\&task_name\=ping

Requires query params `tc_worker_id` and `task_name`.

Param `task_name` must be in `settings.py`.
Param `tc_worker_id` must be in the data and have an associated machine.

Note: these are params and not in the body to support TC actions

Example response:

```json
{"task_name":"ping","tc_worker_id":"tc-worker-1","task_id":"e62c4d06-8101-4074-b3c2-c639005a4430"}
```

The task_id is the Celery Task ID.


### Development

#### Build and run the web and worker containers

1. `make start-web start-worker`

#### Adding a public HW management task

##### Add it

1. Create `relops_hardware_controller/api/management/commands/<command_name>.py` and `tests/test_<command_name>_command.py` e.g. [ping.py](https://github.com/mozilla-services/relops-hardware-controller/blob/3c1826174fca5face67cebd44e84c40602543a07/relops_hardware_controller/api/management/commands/ping.py) and [test_ping_command.py](https://github.com/mozilla-services/relops-hardware-controller/blob/3c1826174fca5face67cebd44e84c40602543a07/tests/test_ping_command.py)
1. Run `make shell` then `./manage.py` and check for the command in the api section of the output
1. Develop the command as a management command and from the test file.

##### Publish it

1. In `relops_hardware_controller/settings.py` add the command name to `TASK_NAMES` to make it API accessible
1. Add a method called `get_args_and_kwargs_from_job` to the command that takes args self, tc_worker_json, machine_json and returns a tuple of (array of args, dict of kwargs) to call the command with NB: these will be parsed.
1. Add any required shared secrets like ssh keys to the settings.py or .env-dist container (TODO: add example)

##### Test it

###### from the docker image

1. After running `make clean build`, try running it from docker e.g. with `docker-compose run web python manage.py ping 127.0.0.1`

###### from the API

1. Run a command like `curl -v -w '\n' -X POST -H 'Accept: application/json' -H 'Content-Type: application/json' http://localhost:8000/api/v1/jobs\?tc_worker_id\=tc-worker-1\&task_name\=ping` and check that the worker runs it.


##### TODO: permissions, deployment, register with TC

1. define permissions for it
1. deploy a worker using it and restart the API
1. register the action with taskcluster


#### TODO: Adding a machine or VM

1. open the django admin
1. add a machine (ip, hostname)
1. add it to appropriate groups (xen, hp) or toggle appropriate properties?
