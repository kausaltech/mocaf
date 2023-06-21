SET search_path to :schema, public;

ALTER TABLE :schema.agency
  DROP CONSTRAINT agency_pkey CASCADE;

ALTER TABLE :schema.calendar
  DROP CONSTRAINT calendar_pkey CASCADE;
DROP INDEX :schema.calendar_service_id;

ALTER TABLE :schema.stops
  DROP CONSTRAINT stops_pkey CASCADE;

ALTER TABLE :schema.routes
  DROP CONSTRAINT routes_pkey CASCADE;

DROP INDEX :schema.calendar_dates_dateidx;

ALTER TABLE :schema.fare_attributes
  DROP CONSTRAINT fare_attributes_pkey CASCADE;

DROP INDEX shapes_shape_key;

ALTER TABLE :schema.trips
  DROP CONSTRAINT trips_pkey CASCADE;
DROP INDEX trips_service_id;

ALTER TABLE :schema.stop_times
  DROP CONSTRAINT stop_times_pkey CASCADE;

DROP INDEX stop_times_key;
DROP INDEX arr_time_index;
DROP INDEX dep_time_index;

ALTER TABLE :schema.shape_geoms
  DROP CONSTRAINT shape_geom_pkey CASCADE;

ALTER TABLE :schema.frequencies
  DROP CONSTRAINT frequencies_pkey CASCADE;
