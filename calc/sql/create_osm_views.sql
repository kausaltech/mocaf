DROP MATERIALIZED VIEW planet_osm_car_ways CASCADE;
DROP MATERIALIZED VIEW planet_osm_transit_routes CASCADE;
DROP MATERIALIZED VIEW planet_osm_rail_ways CASCADE;


CREATE MATERIALIZED VIEW IF NOT EXISTS planet_osm_car_ways AS
    SELECT
        osm_id,
        name,
        highway,
        way
    FROM planet_osm_line
    WHERE
        highway IN (
            'minor', 'road', 'unclassified', 'residential', 'tertiary_link', 'tertiary',
            'secondary_link', 'secondary', 'primary_link', 'primary', 'trunk_link',
            'trunk', 'motorway_link', 'motorway',
            'service'
        );

CREATE INDEX planet_osm_car_ways_geom_idx
  ON planet_osm_car_ways
  USING GIST (way);


CREATE MATERIALIZED VIEW IF NOT EXISTS planet_osm_transit_routes AS
    SELECT
        osm_id,
        name,
        route,
        way
    FROM planet_osm_line
    WHERE
        route IN (
            'bus', 'ferry', 'railway', 'subway', 'tram'
        );

CREATE INDEX planet_osm_transit_routes_geom_idx
  ON planet_osm_transit_routes
  USING GIST (way);


CREATE MATERIALIZED VIEW IF NOT EXISTS planet_osm_rail_ways AS
    SELECT
        osm_id,
        name,
        railway,
        way
    FROM planet_osm_line
    WHERE
        railway IN (
            'light_rail', 'tram', 'rail'
        );


CREATE INDEX planet_osm_rail_ways_geom_idx
  ON planet_osm_rail_ways
  USING GIST (way);
