
PYTHON = python3.14
PIP = pip3.14
NPM = npm

packages:
	$(PYTHON) -m venv ./local_venv; . ./local_venv/bin/activate; $(PIP) install -r requirements.txt

packages-clean:
	rm -fr ./local_venv

packages-js:
	$(NPM) install

packages-js-clean:
	rm -fr ./node_modules ./package-lock.json

run: staticfiles migrations
	. ./local_venv/bin/activate; cd ./src/smplfrm;  $(PYTHON) manage.py runserver 0.0.0.0:8321

run-gunicorn: staticfiles migrations
	. ./local_venv/bin/activate; cd ./src/smplfrm; \
	WORKERS=$$(python3.14 -c "import os; print(max(2, min(8, 2 * os.cpu_count() + 1)))"); \
	gunicorn smplfrm.wsgi:application \
		--bind 0.0.0.0:8321 \
		--workers $$WORKERS \
		--graceful-timeout 30 \
		--timeout 30

staticfiles:
	. ./local_venv/bin/activate; cd ./src/smplfrm;  $(PYTHON) manage.py collectstatic --noinput

migrations:
	. ./local_venv/bin/activate; cd ./src/smplfrm;  $(PYTHON) manage.py migrate

makemigrations:
	. ./local_venv/bin/activate; cd ./src/smplfrm; $(PYTHON) manage.py makemigrations

test:
	. ./local_venv/bin/activate; cd ./src/smplfrm; pytest

test-js:
	$(NPM) test

test-js-watch:
	$(NPM) run test:watch

test-js-coverage:
	$(NPM) run test:coverage

start-celery:
	. ./local_venv/bin/activate; cd ./src/smplfrm; $(PYTHON) -m celery -A smplfrm worker -E -l info
start-celery-beat:
	. ./local_venv/bin/activate; cd ./src/smplfrm; $(PYTHON) -m celery -A smplfrm beat -l info

docker-services:
	cd ./docker/compose; docker compose -f services.yaml up -d

docker-run:
	cd ./docker/compose; docker compose -f compose.yaml up

docker-run-no-cache:
	cd ./docker/compose; docker compose -f compose.yaml up --build

pre-commit: packages
	. ./local_venv/bin/activate; pre-commit install

ignore-format-commit:
	git config blame.ignoreRevsFile .git-blame-ignore-revs

version:
	. ./local_venv/bin/activate; ./scripts/generate_version.sh
