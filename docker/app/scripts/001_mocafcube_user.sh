#!/bin/bash

export CUBE_USER=mocafcube
export PGPASSWORD="${POSTGRES_PASSWORD}"

psql -U mocaf -h db mocaf <<EOF
DROP OWNED BY ${CUBE_USER};
DROP ROLE IF EXISTS ${CUBE_USER};
CREATE USER ${CUBE_USER} WITH PASSWORD '${CUBEJS_DB_PASS}';
GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${CUBE_USER};
GRANT SELECT ON TABLE
    analytics_dailymodesummary,
    analytics_dailytripsummary,
    analytics_areatype,
    analytics_area,
    trips_transportmode
    TO ${CUBE_USER};
EOF
