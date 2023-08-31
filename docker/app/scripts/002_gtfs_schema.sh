#!/bin/bash

export PGPASSWORD="${POSTGRES_PASSWORD}"
export PGUSER=mocaf
export PGDATABASE=mocaf
export PGHOST=db

psql -t -c "SELECT COUNT(*) FROM gtfs.agency;" 2> /dev/null > /dev/null
if [ $? -ne 0 ] ; then
    make -C /code/gtfs/sql-importer init
fi
