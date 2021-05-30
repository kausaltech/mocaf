#!/bin/bash
TABLES="agency calendar calendar_dates routes shapes stops trips stop_times transfers frequencies fare_attributes fare_rules"

# This script takes two arguments: 
# A zip file containing gtfs files, and a schema name (defaults to gtfs)
ZIP=$1
SCHEMA=${2=gtfs}
FILES=$(unzip -l "${ZIP}" | awk '{print $NF}' | grep .txt)
set -e

# Called with name of table
function import_stdin()
{
    local hed
    # remove possible BOM
    hed=$(unzip -p "$ZIP" "${1}.txt" | head -n 1 | awk '{sub(/^\xef\xbb\xbf/,"")}{print}')
    # Add unknown custom columns as text fields
    echo "$hed" | awk -v schema=$SCHEMA -v FS=, -v table="$1" '{for (i = 1; i <= NF; i++) print "ALTER TABLE " schema "." table " ADD COLUMN IF NOT EXISTS " $i " TEXT;"}' | psql
    echo "COPY ${SCHEMA}.${1}" 1>&2
    unzip -p "$ZIP" "${1}.txt" | awk '{ sub(/\r$/, ""); sub("^\"\",", ","); gsub(",\"\"", ","); gsub(/,[[:space:]]+/, ","); if (NF > 0) print }' | psql -c "COPY ${SCHEMA}.${1} (${hed}) FROM STDIN WITH DELIMITER AS ',' HEADER CSV"
}

ADD_DATES=
# Insert feed info
if [[ "${FILES/feed_info}" != "$FILES" ]]; then
    # Contains feed info, so load that into the table
    echo "Loading feed_info from dataset"
    import_stdin "feed_info"
    psql -c "UPDATE ${SCHEMA}.feed_info SET feed_file = '$1' WHERE feed_index = (SELECT max(feed_index) FROM ${SCHEMA}.feed_info)"
else
    ADD_DATES=true
    # get the min and max calendar dates for this
    echo "No feed_info file found, constructing one"
    echo "INSERT INTO ${SCHEMA}.feed_info" 1>&2
    psql -c "INSERT INTO ${SCHEMA}.feed_info (feed_file) VALUES ('$1');"
fi

# Save the current feed_index
feed_index=$(psql --pset format=unaligned -t -c "SELECT max(feed_index) FROM ${SCHEMA}.feed_info")

echo "SET feed_index = $feed_index" 1>&2

# for each table, check if file exists
for table in $TABLES; do
    if [[ ${FILES/${table}.txt} != "$FILES" ]]; then
        # set default feed_index
        psql -c "ALTER TABLE ${SCHEMA}.${table} ALTER COLUMN feed_index SET DEFAULT ${feed_index}"

        # read it into db
        import_stdin "$table"

        # unset default feed_index
        psql -c "ALTER TABLE ${SCHEMA}.${table} ALTER COLUMN feed_index DROP DEFAULT"
    fi
done

if [ -n "$ADD_DATES" ]; then
    echo "UPDATE ${SCHEMA}.feed_info"
    psql -c "UPDATE ${SCHEMA}.feed_info SET feed_start_date=s, feed_end_date=e FROM (SELECT MIN(start_date) AS s, MAX(end_date) AS e FROM ${SCHEMA}.calendar WHERE feed_index=${feed_index}) a WHERE feed_index = ${feed_index}"
else
    psql -c "UPDATE ${SCHEMA}.feed_info SET feed_file ='${ZIP}' WHERE feed_index = ${feed_index}"
fi
