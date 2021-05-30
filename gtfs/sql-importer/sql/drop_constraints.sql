SET search_path to :schema, public;

-- :schema.routes

ALTER TABLE :schema.routes
    DROP CONSTRAINT routes_fkey CASCADE;
ALTER TABLE :schema.routes
    DROP CONSTRAINT route_types_fkey CASCADE;

-- :schema.fare_attributes

ALTER TABLE :schema.fare_attributes
    DROP CONSTRAINT fare_attributes_fkey CASCADE;

-- :schema.calendar_dates

ALTER TABLE :schema.calendar_dates
    DROP CONSTRAINT calendar_fkey CASCADE;

-- :schema.fare_rules

ALTER TABLE :schema.fare_rules
    DROP CONSTRAINT fare_rules_service_fkey CASCADE;
ALTER TABLE :schema.fare_rules
    DROP CONSTRAINT fare_rules_route_id_fkey CASCADE;
ALTER TABLE :schema.fare_rules
    DROP CONSTRAINT fare_rules_fare_id_fkey CASCADE;

-- :schema.trips

ALTER TABLE :schema.trips
    DROP CONSTRAINT trips_route_id_fkey CASCADE;
ALTER TABLE :schema.trips
    DROP CONSTRAINT trips_calendar_fkey CASCADE;

-- :schema.stop_times

ALTER TABLE :schema.stop_times
    DROP CONSTRAINT stop_times_trips_fkey CASCADE;
ALTER TABLE :schema.stop_times
    DROP CONSTRAINT stop_times_stops_fkey CASCADE;
ALTER TABLE :schema.stop_times
  DROP CONSTRAINT continuous_pickup_fkey CASCADE;

-- :schema.frequencies

ALTER TABLE :schema.frequencies
    DROP CONSTRAINT frequencies_trip_fkey CASCADE;

-- :schema.transfers

ALTER TABLE :schema.transfers
    DROP CONSTRAINT transfers_from_stop_fkey CASCADE;
ALTER TABLE :schema.transfers
    DROP CONSTRAINT transfers_to_stop_fkey CASCADE;
ALTER TABLE :schema.transfers
    DROP CONSTRAINT transfers_from_route_fkey CASCADE;
ALTER TABLE :schema.transfers
    DROP CONSTRAINT transfers_to_route_fkey CASCADE;
ALTER TABLE :schema.transfers
    DROP CONSTRAINT transfers_service_fkey CASCADE;
