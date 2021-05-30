\C 'Possible foreign key violations'

SELECT v.constraint, count as "possible violations" FROM (
  SELECT 'route_types_fkey' as constraint, count(distinct (feed_index, route_type))
    FROM :schema.routes a
      LEFT JOIN :schema.route_types b USING (route_type)
    WHERE b.description IS NULL
  UNION
  SELECT 'routes_fkey', count(distinct (feed_index, agency_id))
    FROM :schema.routes a
      LEFT JOIN :schema.agency b USING (feed_index, agency_id)
    WHERE b.agency_id IS NULL
  UNION
  SELECT 'calendar_fkey', count(distinct (feed_index, service_id))
    FROM :schema.calendar_dates
      LEFT JOIN :schema.calendar b USING (feed_index, service_id)
    WHERE coalesce(b.monday, b.friday) IS NULL
  UNION
  SELECT 'fare_attributes_fkey', count(distinct (feed_index, agency_id))
    FROM :schema.fare_attributes a
      LEFT JOIN :schema.agency b USING (feed_index, agency_id)
    WHERE b.agency_id IS NULL
  UNION
  SELECT 'fare_rules_service_fkey', count(distinct (feed_index, service_id))
    FROM :schema.fare_rules a
      LEFT JOIN :schema.calendar b USING (feed_index, service_id)
    WHERE coalesce(b.monday, b.friday) IS NULL
  UNION
  SELECT 'fare_rules_fare_id_fkey', count(distinct (feed_index, fare_id))
    FROM :schema.fare_rules a
      LEFT JOIN :schema.fare_attributes b USING (feed_index, fare_id)
    WHERE b.price IS NULL
  UNION
  SELECT 'fare_rules_route_id_fkey', count(distinct (feed_index, route_id))
    FROM :schema.fare_rules a
      LEFT JOIN :schema.routes b USING (feed_index, route_id)
    WHERE b.agency_id IS NULL
  UNION
  SELECT 'trips_route_id_fkey', count(distinct (feed_index, route_id))
    FROM :schema.trips a
      LEFT JOIN :schema.routes b USING (feed_index, route_id)
    WHERE b.agency_id IS NULL
  UNION
  SELECT 'trips_calendar_fkey', count(distinct (feed_index, service_id))
    FROM :schema.trips a
      LEFT JOIN :schema.calendar b USING (feed_index, service_id)
    WHERE coalesce(b.monday, b.friday) IS NULL
  UNION
  SELECT 'stop_times_trips_fkey', count(distinct (feed_index, trip_id))
    FROM :schema.stop_times a
      LEFT JOIN :schema.trips b USING (feed_index, trip_id)
    WHERE b.service_id IS NULL
  UNION
  SELECT 'stop_times_stops_fkey', count(distinct (feed_index, stop_id))
    FROM :schema.stop_times a
      LEFT JOIN :schema.stops b USING (feed_index, stop_id)
    WHERE coalesce(stop_lat, stop_lon) IS NULL
  UNION
  SELECT 'frequencies_trip_fkey', count(distinct (feed_index, trip_id))
    FROM :schema.frequencies a
      LEFT JOIN :schema.trips b USING (feed_index, trip_id)
    WHERE b.service_id IS NULL
  UNION
  SELECT 'transfers_from_stop_fkey', count(distinct (a.feed_index, from_stop_id))
    FROM :schema.transfers a
      LEFT JOIN :schema.stops b on a.feed_index = b.feed_index and a.from_stop_id::text = b.stop_id::text
    WHERE coalesce(stop_lat, stop_lon) IS NULL
  UNION
  SELECT 'transfers_to_stop_fkey', count(distinct (a.feed_index, to_stop_id))
    FROM :schema.transfers a
      LEFT JOIN :schema.stops b on a.feed_index = b.feed_index and a.to_stop_id::text = b.stop_id::text
    WHERE coalesce(stop_lat, stop_lon) IS NULL
  UNION
  SELECT 'transfers_from_route_fkey', count(distinct (a.feed_index, from_route_id))
    FROM :schema.transfers a
      LEFT JOIN :schema.routes b on a.feed_index = b.feed_index and a.from_route_id::text = b.route_id::text
    WHERE b.agency_id IS NULL
  UNION
  SELECT 'transfers_to_route_fkey', count(distinct (a.feed_index, to_route_id))
    FROM :schema.transfers a
      LEFT JOIN :schema.routes b on a.feed_index = b.feed_index and a.to_route_id::text = b.route_id::text
    WHERE b.agency_id IS NULL
  UNION
  SELECT 'transfers_service_fkey', count(distinct (feed_index, service_id))
    FROM :schema.transfers a
      LEFT JOIN :schema.calendar b USING (feed_index, service_id)
    WHERE coalesce(b.monday, b.friday) IS NULL
) AS v
WHERE count > 0;

\C 'Non-NULL constraint violations'
SELECT DISTINCT NULL::int feed_index, 'routes' as table, 'route_type' as key, a.route_type::text as value
  FROM :schema.routes a
    LEFT JOIN :schema.route_types b USING (route_type)
  where b.route_type is null
UNION
SELECT DISTINCT a.feed_index, 'routes' as table, 'agency_id'::text, a.agency_id
  FROM :schema.routes a
    LEFT JOIN :schema.agency b USING (feed_index, agency_id)
  where b.feed_index is null or b.agency_id is null
-- :schema.calendar_dates
UNION
SELECT DISTINCT a.feed_index, 'calendar', 'service_id', a.service_id
  FROM :schema.calendar_dates a
    LEFT JOIN :schema.calendar b USING (feed_index, service_id)
  WHERE b.feed_index is null or b.service_id is null
UNION
SELECT DISTINCT a.feed_index, 'agency', 'agency_id', a.agency_id
  FROM :schema.fare_attributes a
    LEFT JOIN :schema.agency b USING (feed_index, agency_id)
  WHERE b.feed_index is null or b.agency_id is null
-- :schema.fare_rules
UNION
SELECT DISTINCT a.feed_index, 'calendar', 'service_id', a.service_id
  FROM :schema.fare_rules a
    LEFT JOIN :schema.calendar b USING (feed_index, service_id)
  WHERE b.feed_index is null or b.service_id is null
UNION
SELECT DISTINCT a.feed_index, 'fare_attributes', 'fare_id', a.fare_id
  FROM :schema.fare_rules a
    LEFT JOIN :schema.fare_attributes b USING (feed_index, fare_id)
  WHERE b.feed_index is null or b.fare_id is null
UNION
SELECT DISTINCT a.feed_index, 'routes', 'route_id', a.route_id
  FROM :schema.fare_rules a
    LEFT JOIN :schema.routes b USING (feed_index, route_id)
  WHERE b.feed_index is null OR b.route_id is null
-- :schema.trips
UNION
SELECT DISTINCT a.feed_index, 'routes', 'route_id', a.route_id
  FROM :schema.trips a
    LEFT JOIN :schema.routes b USING (feed_index, route_id)
  WHERE b.feed_index is null OR b.route_id is null
UNION
SELECT DISTINCT a.feed_index, 'calendar', 'service_id', a.service_id
  FROM :schema.trips a
    LEFT JOIN :schema.calendar b USING (feed_index, service_id)
  WHERE b.feed_index is null OR b.service_id is null
-- :schema.stop_times
UNION
SELECT DISTINCT a.feed_index, 'trips', 'trip_id', a.trip_id
  FROM :schema.stop_times a
    LEFT JOIN :schema.trips b USING (feed_index, trip_id)
  WHERE b.feed_index is null OR b.trip_id is null
UNION
SELECT DISTINCT a.feed_index, 'stops', 'stop_id', a.stop_id
  FROM :schema.stop_times a
    LEFT JOIN :schema.stops b USING (feed_index, stop_id)
  WHERE b.feed_index is null OR b.stop_id is null
-- :schema.frequencies
UNION
SELECT DISTINCT a.feed_index, 'trips', 'trip_id', a.trip_id
  FROM :schema.frequencies a
    LEFT JOIN :schema.trips b USING (feed_index, trip_id)
  WHERE b.feed_index is null OR b.trip_id is null
-- :schema.transfers
UNION
SELECT DISTINCT a.feed_index, 'stops', 'from_stop_id', a.from_stop_id
  FROM :schema.transfers a
    LEFT JOIN :schema.stops b ON (a.feed_index, a.from_stop_id) = (b.feed_index, b.stop_id)
  WHERE b.feed_index is null OR stop_id is null
UNION
SELECT DISTINCT a.feed_index, 'stops', 'to_stop_id', coalesce(a.to_stop_id, 'NULL')
  FROM :schema.transfers a
    LEFT JOIN :schema.stops b ON (a.feed_index, a.to_stop_id) = (b.feed_index, b.stop_id)
  WHERE b.feed_index is null OR stop_id is null
UNION
SELECT DISTINCT a.feed_index, 'routes', 'from_route_id', coalesce(a.from_route_id, 'NULL')
  FROM :schema.transfers a
    LEFT JOIN :schema.routes b ON (a.feed_index, a.from_route_id) = (b.feed_index, b.route_id)
  WHERE (b.feed_index is null OR route_id is null)
UNION
SELECT DISTINCT a.feed_index, 'routes', 'to_route_id', coalesce(a.to_route_id, 'NULL')
  FROM :schema.transfers a
    LEFT JOIN :schema.routes b ON (a.feed_index, a.to_route_id) = (b.feed_index, b.route_id)
  WHERE (b.feed_index is null OR route_id is null)
UNION
SELECT DISTINCT a.feed_index, 'calendar', 'service_id', coalesce(a.service_id, 'NULL')
  FROM :schema.transfers a
    LEFT JOIN :schema.calendar b USING (feed_index, service_id)
  where (b.feed_index is null OR b.service_id is null);

-- Find out-of-order stops for the most recent feed added.
-- Change the first subquery to SELECT different feeds.
\C 'Out-of-order stop geometries'
WITH f AS (SELECT MAX(feed_index) AS feed_index FROM :schema.feed_info)
SELECT feed_index,
  trip_id,
  route_id,
  stop_id,
  stop_sequence,
  lag::numeric(9, 3),
  dist::numeric(9, 3), 
  coalesce(lead, length)::numeric(9, 3) as lead,
  length::numeric(9, 3)
FROM (
    SELECT
      feed_index,
      trip_id,
      stop_id,
      stop_sequence,
      coalesce(lag(shape_dist_traveled) over (trip), 0) AS lag,
      shape_dist_traveled AS dist,
      (lead(shape_dist_traveled) over (trip)) AS lead
    FROM :schema.stop_times
      INNER JOIN f USING (feed_index)
    WINDOW trip AS (PARTITION BY feed_index, trip_id ORDER BY stop_sequence)
  ) AS d
  LEFT JOIN :schema.trips trip USING (feed_index, trip_id)
  LEFT JOIN :schema.shape_geoms shape USING (feed_index, shape_id)
WHERE COALESCE(lead, length) > lag
  AND (dist > COALESCE(lead, length) OR dist < lag);
