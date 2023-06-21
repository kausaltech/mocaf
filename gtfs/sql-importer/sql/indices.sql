SET search_path to :schema, public;

ALTER TABLE :schema.agency
  ADD CONSTRAINT agency_pkey
  PRIMARY KEY (feed_index, agency_id);

ALTER TABLE :schema.calendar
  ADD CONSTRAINT calendar_pkey
  PRIMARY KEY (feed_index, service_id);

CREATE INDEX IF NOT EXISTS calendar_service_id
  ON :schema.calendar (feed_index, service_id);

ALTER TABLE :schema.stops
  ADD CONSTRAINT stops_pkey
  PRIMARY KEY (feed_index, stop_id);

ALTER TABLE :schema.routes
  ADD CONSTRAINT routes_pkey
  PRIMARY KEY (feed_index, route_id);

CREATE INDEX IF NOT EXISTS calendar_dates_dateidx
  ON :schema.calendar_dates (date);

ALTER TABLE :schema.fare_attributes
  ADD CONSTRAINT fare_attributes_pkey
  PRIMARY KEY (feed_index, fare_id);

CREATE INDEX IF NOT EXISTS shapes_shape_key
  ON :schema.shapes (shape_id);

ALTER TABLE :schema.trips
  ADD CONSTRAINT trips_pkey
  PRIMARY KEY (feed_index, trip_id);

CREATE INDEX IF NOT EXISTS trips_service_id
  ON :schema.trips (feed_index, service_id);

ALTER TABLE :schema.stop_times
  ADD CONSTRAINT stop_times_pkey
  PRIMARY KEY (feed_index, trip_id, stop_sequence);

CREATE INDEX IF NOT EXISTS stop_times_key
  ON :schema.stop_times (feed_index, trip_id, stop_id);

CREATE INDEX IF NOT EXISTS arr_time_index
  ON :schema.stop_times (arrival_time_seconds);

CREATE INDEX IF NOT EXISTS dep_time_index
  ON :schema.stop_times (departure_time_seconds);

ALTER TABLE :schema.shape_geoms
  ADD CONSTRAINT shape_geom_pkey
  PRIMARY KEY (feed_index, shape_id);

ALTER TABLE :schema.frequencies
  ADD CONSTRAINT frequencies_pkey
  PRIMARY KEY (feed_index, trip_id, start_time);

CREATE INDEX IF NOT EXISTS shape_geoms_geom_idx
  ON :schema.shape_geoms
  USING GIST (the_geom);
