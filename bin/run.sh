#!/usr/bin/env bash
set -eo pipefail

# default variables
: "${PORT:=8000}"
: "${SLEEP:=1}"
: "${TRIES:=60}"
: "${GUNICORN_WORKERS:=4}"

usage() {
  echo "usage: ./bin/run.sh web|web-dev|worker|test|bash|superuser"
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
[ ! -z ${DEVELOPMENT+check} ] && wait_for db 5432 && wait_for redis 6379

case $1 in
  web)
    ${CMD_PREFIX_PYTHON:-python} manage.py migrate --noinput
    ${CMD_PREFIX} gunicorn relops_hardware_controller.wsgi:application -b 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS} --worker-class="egg:meinheld#gunicorn_worker" --access-logfile -
    ;;
  web-dev)
    python manage.py migrate --noinput
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
  superuser)
    exec python manage.py superuser "${@:2}"
    ;;
  test)
    # python manage.py collectstatic --noinput
    coverage erase
    coverage run -m pytest --flake8 "${@:2}"
    coverage report -m
    if [[ -z ${CI+check} ]]; then
      # generate code coverage to disk
      coverage html --skip-covered
    fi
    # Temporarily disabled. The team is small and codecov's report inside
    # pull requests (as comments) is more noise than help.
    # Also, code coverage is mostly useful when contributors help and
    # add more code without adding tests to cover.
    # if [[ ! -z ${CI+check} ]]; then
    #   # submit coverage
    #   coverage xml
    #   env
    #   bash <(curl -s https://codecov.io/bash) -s /tmp
    # fi
    ;;
  bash)
    # The likelyhood of needing pytest-watch when in shell is
    # big enough that it's worth always installing it before going
    # into the shell. This is up for debate as time and main developers
    # make.
    echo "For high-speed test development, run: pip install pytest-watch"
    exec "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
