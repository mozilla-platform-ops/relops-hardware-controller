#!/usr/bin/env bash
set -eo pipefail

# default variables
: "${PORT:=8000}"
: "${SLEEP:=1}"
: "${TRIES:=60}"
: "${GUNICORN_WORKERS:=4}"

usage() {
  echo "usage: ./bin/run.sh web|web-dev|worker|test|bash|manage.py"
  exit 1
}

wait_for() {
  tries=0
  echo "Waiting for $1 to listen on $2..."
  while true; do
    [[ $tries -lt $TRIES ]] || return
    (echo > /dev/tcp/$1/$2) >/dev/null 2>&1
    result=
    [[ $? -eq 0 ]] && return
    sleep $SLEEP
    tries=$((tries + 1))
  done
}

[ $# -lt 1 ] && usage

# Only wait for backend services in development
# http://stackoverflow.com/a/13864829
# For example, bin/test.sh sets 'DEVELOPMENT' to something
[ ! -z ${DEVELOPMENT+check} ] && wait_for redis 6379

case $1 in
  web)
    ${CMD_PREFIX} gunicorn relops_hardware_controller.wsgi:application -b 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS} --worker-class="egg:meinheld#gunicorn_worker" --access-logfile -
    ;;
  web-dev)
    exec python manage.py runserver 0.0.0.0:${PORT}
    ;;
  worker)
    exec celery -A relops_hardware_controller.celery:app worker -l debug
    ;;
  worker-purge)
    # Start worker but first purge ALL old stale tasks.
    # Only useful in local development where you might have accidentally
    # started waaaay too make background tasks when debugging something.
    # Or perhaps the jobs belong to the wrong branch as you stop/checkout/start
    # the docker container.
    exec celery -A relops_hardware_controller.celery:app worker -l debug --purge
    ;;
  watch-worker-purge)
    # For developing workers purge the queue and restart the worker when a python file changes
    exec watchmedo auto-restart --recursive -d /app -p '*.py' -- celery -A relops_hardware_controller.celery:app worker -l debug --purge
    ;;
  manage.py)
    # For testing custom management commands directly from docker
    exec python manage.py "${@:2}"
    ;;
  test)
    # python manage.py collectstatic --noinput
    coverage erase
    coverage run -m pytest --flake8 "${@:2}"
    coverage report -m
    # generate code coverage to disk
    mkdir -p /app/htmlcov
    coverage html --skip-covered -d /app/htmlcov
    # submit coverage
    coverage xml
    ;;
  bash)
    echo "For high-speed test development, run: ptw"
    exec "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
