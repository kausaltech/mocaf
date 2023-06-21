SET search_path to :schema, public;

-- routes

ALTER TABLE routes
  ADD CONSTRAINT route_types_fkey
  FOREIGN KEY (route_type)
  REFERENCES route_types (route_type) ON DELETE CASCADE;

ALTER TABLE routes
  ADD CONSTRAINT routes_fkey
  FOREIGN KEY (feed_index, agency_id)
  REFERENCES agency (feed_index, agency_id) ON DELETE CASCADE;

-- calendar_dates

--ALTER TABLE calendar_dates
--  ADD CONSTRAINT calendar_fkey
--  FOREIGN KEY (feed_index, service_id)
--  REFERENCES calendar (feed_index, service_id) ON DELETE CASCADE;

ALTER TABLE fare_attributes
  ADD CONSTRAINT fare_attributes_fkey
  FOREIGN KEY (feed_index, agency_id)
  REFERENCES agency (feed_index, agency_id) ON DELETE CASCADE;

-- fare_rules

ALTER TABLE fare_rules
  ADD CONSTRAINT fare_rules_service_fkey 
  FOREIGN KEY (feed_index, service_id)
  REFERENCES calendar (feed_index, service_id) ON DELETE CASCADE;

ALTER TABLE fare_rules
  ADD CONSTRAINT fare_rules_fare_id_fkey
  FOREIGN KEY (feed_index, fare_id)
  REFERENCES fare_attributes (feed_index, fare_id) ON DELETE CASCADE;

ALTER TABLE fare_rules
  ADD CONSTRAINT fare_rules_route_id_fkey
  FOREIGN KEY (feed_index, route_id)
  REFERENCES routes (feed_index, route_id) ON DELETE CASCADE;

-- trips

ALTER TABLE trips
  ADD CONSTRAINT trips_route_id_fkey
  FOREIGN KEY (feed_index, route_id)
  REFERENCES routes (feed_index, route_id) ON DELETE CASCADE;

--ALTER TABLE trips
--  ADD CONSTRAINT trips_calendar_fkey
--  FOREIGN KEY (feed_index, service_id)
--  REFERENCES calendar (feed_index, service_id) ON DELETE CASCADE;

-- stop_times

ALTER TABLE stop_times
  ADD CONSTRAINT stop_times_trips_fkey
  FOREIGN KEY (feed_index, trip_id)
  REFERENCES trips (feed_index, trip_id) ON DELETE CASCADE;

ALTER TABLE stop_times
  ADD CONSTRAINT stop_times_stops_fkey
  FOREIGN KEY (feed_index, stop_id)
  REFERENCES stops (feed_index, stop_id) ON DELETE CASCADE;

ALTER TABLE stop_times
  ADD CONSTRAINT continuous_pickup_fkey
  FOREIGN KEY (continuous_pickup)
  REFERENCES continuous_pickup (continuous_pickup) ON DELETE CASCADE;

-- frequencies

ALTER TABLE frequencies
  ADD CONSTRAINT frequencies_trip_fkey
  FOREIGN KEY (feed_index, trip_id)
  REFERENCES trips (feed_index, trip_id) ON DELETE CASCADE;

-- transfers

ALTER TABLE transfers
  ADD CONSTRAINT transfers_from_stop_fkey
  FOREIGN KEY (feed_index, from_stop_id)
  REFERENCES stops (feed_index, stop_id) ON DELETE CASCADE;

ALTER TABLE transfers
  ADD CONSTRAINT transfers_to_stop_fkey
  FOREIGN KEY (feed_index, to_stop_id)
  REFERENCES stops (feed_index, stop_id) ON DELETE CASCADE;

ALTER TABLE transfers
  ADD CONSTRAINT transfers_from_route_fkey
  FOREIGN KEY (feed_index, from_route_id)
  REFERENCES routes (feed_index, route_id) ON DELETE CASCADE;

ALTER TABLE transfers
  ADD CONSTRAINT transfers_to_route_fkey
  FOREIGN KEY (feed_index, to_route_id)
  REFERENCES routes (feed_index, route_id) ON DELETE CASCADE;

ALTER TABLE transfers
  ADD CONSTRAINT transfers_service_fkey
  FOREIGN KEY (feed_index, service_id)
  REFERENCES calendar (feed_index, service_id) ON DELETE CASCADE;
