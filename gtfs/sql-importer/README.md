# About

Import GTFS data into a PostgreSQL database. Includes all the constraints in the GTFS spec with some basic tools for dealing with improper data

## Requirements

* PostGres database (9.5+) with a PostGIS (2.2+) extension

## Links

* [GTFS (General Transit Feed Specification)](https://gtfs.org/reference/static)
* [Transitfeeds](http://transitfeeds.com) (index and archive of GTFS data sets)
* [Transit.land](http://transit.land) A community-edited service with an achive of GTFS.

## Initial import

This importer uses a Makefile to organize a series of SQL commands. The file `src/load.sh` is a shell script that does the heavy lifting of loading the contents of a GTFS zip file into a PostgreSQL database.

Before importing data, set up database with:
```
PGDATABASE=mydbname
make init
```
This will create the necessary tables, as well as useful indices and foreign keys. (It will create a database named `mydbname` if one does not exist).

Next, download a ZIP file containing a GTFS feed. You do not need to decompress it to import it.

To import the GTFS dataset in file named `gtfs.zip` into a local Postgres database named `mydbname`:
````
make load GTFS=gtfs.zip
````

## Connecting to the db

Use the standard [Postgres environment variables](https://www.postgresql.org/docs/current/static/libpq-envars.html) to specify your connection parameters. For example:
````
PGDATABASE=mydbname
PGHOST=example.com
PGUSER=username
make load GTFS=gtfs.zip
````

If you're connecting over the socket, and your postgres username and database match your system username, you don't have to use environment variables.

### Schema

By default, your GTFS data will be loaded into a schema named `gtfs`. You can always rename it when you're done.

## Big datasets

For large feeds, you may find that loading is faster with indices. Don't forget to add them back, or all your queries will be very slow:
````
make drop_indices load add_indices GTFS=gtfs.zip
````

## Feed indexes

GTFS data is regularly updated, and it's reasonable to want to include multiple iterations in the same database. This tool includes a `feed_index` column in each table. This index is part of the primary key of each table.

## Troubleshooting common errors in GTFS data

Most GTFS data has errors in it, so you may encounter an error when running the step above.
Common errors include missing `service_id`s, which cause foreign key errors. To load data despite these violations, remove contraints with `make drop_constraints`. Then load the data and try repair the data. When you're ready, restore the constraints with `make add_constraints`.

### General violation checking

Run the script `sql/violations.sql`, which will perform several queries looking for rows that violate foreign key constraints and bad geometries in the `shapes` table.
```
psql -q -c sql/violations.sql
```
The resulting report will tell you which tables have contrainst violations, and what the errors are. You may wish to manually add these values to your tables.

### Extra columns

The loading script checks for extra columns in a GTFS table and adds them to database as `text` columns. You may wish to alter or remove these columns.

### Null data
```
ERROR:  null value in column "example_id" violates not-null constraint
```
This might occur if an "id" column (e.g. `route_id`) is improperly empty. One solution: edit the file to add a non-empty value.
Another solution: drop indices from the database and reload the data:
```
make drop_indices load
```
Then edit the database to add a non-empty value and recreate the indices (`make add_indices`).

# License
Released under the MIT (X11) license. See LICENSE in this directory.
