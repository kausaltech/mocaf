#!/bin/bash

set -e

if [ "$1" = 'uwsgi' -o "$1" = 'celery' ]; then
    /wait-for-it.sh db:5432
    cd /code
    python manage.py migrate --no-input
    if [ -d '/docker-entrypoint.d' ]; then
        for scr in /docker-entrypoint.d/*.sh ; do
            echo "Running $scr"
            /bin/bash $scr
        done
    fi
fi

if [ "$1" = 'uwsgi' ]; then
    # Log to stdout
    exec uwsgi --http-socket :8000 --socket :8001 --processes 4 \
        --enable-threads \
        --buffer-size=32768 \
        --log-master \
        --static-map /static=/srv/static \
        --static-map /media=/srv/media \
        --module mocaf.wsgi
elif [ "$1" = 'celery' ]; then
    if [ "$2" = 'worker' ]; then
        exec celery -A mocaf worker -Q "$3" -l info
    else
        exec celery -A mocaf "$2" -l INFO
    fi
fi

exec "$@"
