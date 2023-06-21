SET search_path to :schema, public;
DROP TRIGGER IF EXISTS shape_geom_trigger ON :schema.shapes;

DROP TRIGGER IF EXISTS stop_times_dist_row_trigger ON :schema.stop_times;

DROP TRIGGER IF EXISTS stop_times_dist_stmt_trigger ON :schema.stop_times;

DROP TRIGGER IF EXISTS stop_geom_trigger ON :schema.stops;
