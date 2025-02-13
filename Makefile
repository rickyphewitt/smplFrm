
packages:
	python -m venv ./local_venv; . ./local_venv/bin/activate; pip install -r requirements.txt

run: migrations
	. ./local_venv/bin/activate; cd ./src/smplfrm;  python manage.py runserver 0.0.0.0:8321

migrations:
	. ./local_venv/bin/activate; cd ./src/smplfrm;  python manage.py migrate

makemigrations:
	. ./local_venv/bin/activate; cd ./src/smplfrm; python manage.py makemigrations

test:
	. ./local_venv/bin/activate; cd ./src/smplfrm; pytest

start-celery:
	. ./local_venv/bin/activate; cd ./src/smplfrm; python -m celery -A smplfrm worker -E -l info
start-celery-beat:
	. ./local_venv/bin/activate; cd ./src/smplfrm; python -m celery -A smplfrm beat -l info

docker-services:
	cd ./docker/compose; docker compose -f services.yaml up -d

docker-run:
	cd ./docker/compose; docker compose -f compose.yaml up

docker-run-no-cache:
	cd ./docker/compose; docker compose -f compose.yaml up --build