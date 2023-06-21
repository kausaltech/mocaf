SHELL = bash

TABLES = stop_times trips routes \
	calendar_dates calendar \
	shapes stops \
	transfers frequencies \
	fare_attributes fare_rules agency feed_info

PGUSER ?= $(USER)
PGDATABASE ?= $(PGUSER)
SCHEMA = gtfs
psql = $(strip psql -v schema=$(SCHEMA) $(PSQLFLAGS))

.PHONY: all load vacuum init clean \
	drop_constraints add_constraints \
	drop_indices add_indices \
	add_triggers drop_triggers

export PGUSER PGDATABASE PGHOST

all:

add_constraints add_indices add_triggers: add_%: sql/%.sql
	$(psql) -f $<

drop_indices drop_constraints drop_triggers: drop_%: sql/drop_%.sql
	$(psql) -f $<

load: $(GTFS)
	[[ -z "$$(psql -Atc "select feed_index from $(SCHEMA).feed_info where feed_file = '$(GTFS)'")" ]] && \
		$(SHELL) src/load.sh $(GTFS) $(SCHEMA)
	@$(psql) -F' ' -tAc "SELECT 'loaded feed with index: ', feed_index FROM $(SCHEMA).feed_info WHERE feed_file = '$(GTFS)'"

vacuum: ; $(psql) -c "VACUUM ANALYZE"


clean:
	[[ $(words $(FEED_INDEX)) -eq 1 ]] && \
	for t in $(TABLES); \
	do echo "DELETE FROM $(SCHEMA).$$t WHERE feed_index = $(FEED_INDEX);"; done \
	| $(psql); 

truncate:
	for t in $(TABLES); \
	do echo "TRUNCATE TABLE $(SCHEMA).$$t RESTART IDENTITY CASCADE;"; done \
	| $(psql)

init: sql/schema.sql
	$(psql) -f $<
	$(psql) -c "\copy $(SCHEMA).route_types FROM 'data/route_types.txt'"
	$(psql) -f sql/constraints.sql
