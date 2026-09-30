
# Python targets run through uv (https://docs.astral.sh/uv/).
# UV: uv executable; override with `make UV=/path/to/uv <target>`.
# UV_SYNC_FLAGS: flags for `uv sync` in `packages`. `--locked` fails if uv.lock
#   is out of date with pyproject.toml instead of rewriting it.
# UV_RUN_FLAGS: flags for `uv run`. `--locked` keeps the environment in sync and
#   fails on a stale lock. The container sets `--no-sync` so runtime targets never
#   resolve, download, or modify the environment built into the image.
UV ?= uv
UV_SYNC_FLAGS ?= --locked
UV_RUN_FLAGS ?= --locked
UV_RUN = $(UV) run $(UV_RUN_FLAGS)
NPM = npm

check-uv:
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "error: uv not found (UV=$(UV))." >&2; \
		echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2; \
		echo "Or point to it with: make UV=/path/to/uv <target>" >&2; \
		exit 1; }

packages: check-uv
	$(UV) sync $(UV_SYNC_FLAGS)

packages-clean:
	rm -fr ./.venv ./local_venv

packages-js:
	$(NPM) install

packages-js-clean:
	rm -fr ./node_modules ./package-lock.json

lock: check-uv
	$(UV) lock

run: staticfiles migrations
	cd ./src/smplfrm; $(UV_RUN) python manage.py runserver 0.0.0.0:8321

run-gunicorn: staticfiles migrations
	cd ./src/smplfrm; \
	WORKERS=$$($(UV_RUN) python -c "import os; print(max(2, min(8, 2 * os.cpu_count() + 1)))"); \
	$(UV_RUN) gunicorn smplfrm.wsgi:application \
		--bind 0.0.0.0:8321 \
		--workers $$WORKERS \
		--graceful-timeout 30 \
		--timeout 30

staticfiles: check-uv
	cd ./src/smplfrm; $(UV_RUN) python manage.py collectstatic --noinput

migrations: check-uv
	cd ./src/smplfrm; $(UV_RUN) python manage.py migrate

makemigrations: check-uv
	cd ./src/smplfrm; $(UV_RUN) python manage.py makemigrations

test: check-uv
	cd ./src/smplfrm; $(UV_RUN) pytest

test-js:
	$(NPM) test

test-js-watch:
	$(NPM) run test:watch

test-js-coverage:
	$(NPM) run test:coverage

start-celery: check-uv
	cd ./src/smplfrm; $(UV_RUN) python -m celery -A smplfrm worker -E -l info
start-celery-beat: check-uv
	cd ./src/smplfrm; $(UV_RUN) python -m celery -A smplfrm beat -l info

docker-services:
	cd ./docker/compose; docker compose -f services.yaml up -d

docker-run:
	cd ./docker/compose; docker compose -f compose.yaml up

docker-run-no-cache:
	cd ./docker/compose; docker compose -f compose.yaml up --build

pre-commit: packages
	$(UV_RUN) pre-commit install

ignore-format-commit:
	git config blame.ignoreRevsFile .git-blame-ignore-revs

version:
	./scripts/generate_version.sh
