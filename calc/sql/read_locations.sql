PREPARE read_locations (uuid, timestamp with time zone, timestamp with time zone) AS
SELECT
    l.time AS time,
    -- ST_X(ST_Transform(l.loc, 4326)) AS lon,
    -- ST_Y(ST_Transform(l.loc, 4326)) AS lat,
    ST_X(l.loc) AS x,
    ST_Y(l.loc) AS y,
    l.loc_error,
    l.atype,
    l.aconf,
    l.speed,
    l.heading,
    l.is_moving,
    l.manual_atype,
    l.odometer,
    l.battery_charging,
    ROUND(ccw.closest_car_way_dist :: numeric, 1) AS closest_car_way_dist,
    ccw.closest_car_way_name,
    ccw.closest_car_way_type,
    ccw.closest_car_way_id :: varchar,
    ROUND(crw.closest_rail_way_dist :: numeric, 1) AS closest_rail_way_dist,
    crw.closest_rail_way_name,
    crw.closest_rail_way_type,
    crw.closest_rail_way_id :: varchar,
    l.created_at AS created_at
FROM
    trips_ingest_location AS l
LEFT JOIN LATERAL (
    SELECT
        osm_id AS closest_car_way_id,
        name AS closest_car_way_name,
        ST_Distance(cw.way, l.loc) AS closest_car_way_dist,
        highway AS closest_car_way_type
    FROM planet_osm_car_ways AS cw
    WHERE
        cw.way && ST_Expand(l.loc, 50)
    ORDER BY ST_Distance(cw.way, l.loc) ASC
    LIMIT 1
) AS ccw ON true
LEFT JOIN LATERAL (
    SELECT
        osm_id AS closest_rail_way_id,
        name AS closest_rail_way_name,
        ST_Distance(rw.way, l.loc) AS closest_rail_way_dist,
        ST_LineLocatePoint(rw.way, l.loc) AS closest_rail_way_frac,
        railway AS closest_rail_way_type
    FROM planet_osm_rail_ways AS rw
    WHERE
        rw.way && ST_Expand(l.loc, 50)
    ORDER BY ST_Distance(rw.way, l.loc) ASC
    LIMIT 1
) AS crw ON true
WHERE
    l.uuid = $1
    AND l.time >= $2
    AND l.time <= $3
ORDER BY
    l.time;
