.PHONY: build current-shell clean django-shell load-fixtures psql root-shell shell start start-web start-worker stop test test-ping

help:
	@echo "Commands for local development:\n"
	@echo "  build            Builds the docker images for the docker-compose setup"
	@echo "  clean            Stops and removes all docker containers"
	@echo "  current-shell     Opens a Bash shell into existing running 'web' container"
	@echo "  django-shell     Django integrative shell"
	@echo "  load-fixtures    Load worker and machine fixtures"
	@echo "  psql             Open the psql cli"
	@echo "  root-shell       Opens a Bash shell as root"
	@echo "  start-web        Runs the development web server on http://localhost:8000/"
	@echo "  start-worker     Runs the development worker"
	@echo "  shell            Opens a Bash shell"
	@echo "  stop             Stops the docker containers"
	@echo "  test             Runs the Python test suite"
	@echo "  test-ping        POSTs to the API to start a ping task"

# Dev configuration steps
.docker-build:
	make build

.env:
	./bin/cp-env-file.sh

build: .env
	docker-compose build base
	touch .docker-build

current-shell: .env .docker-build
	docker-compose exec web bash

clean: .env stop
	docker-compose rm -f
	rm -rf coverage/ .coverage
	rm -fr .docker-build

django-shell: .env .docker-build
	docker-compose run web python manage.py shell

load-fixtures: .env .docker-build
	docker-compose run web python manage.py loaddata /app/tests/fixtures/machine_fixtures.json /app/tests/fixtures/worker_fixtures.json

psql: .env .docker-build
	docker-compose run db psql -h db -U postgres

start-web: .env .docker-build
	docker-compose up web

start-worker: .env .docker-build
	docker-compose up watch-worker

shell: .env .docker-build
	docker-compose run web bash

root-shell: .env .docker-build
	docker-compose run --user 0 web bash

stop: .env
	docker-compose stop

test: .env .docker-build
	@bin/test.sh

test-ping:
	curl -v -w '\n' -X POST -H 'Accept: application/json' -H 'Content-Type: application/json' http://localhost:8000/api/v1/workers/tc-worker-1/group/ndc2/jobs\?task_name\=ping
