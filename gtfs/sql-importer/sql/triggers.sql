SET search_path to :schema, public;

CREATE TRIGGER shape_geom_trigger AFTER INSERT ON :schema.shapes
    FOR EACH STATEMENT EXECUTE PROCEDURE :schema.shape_update();

CREATE TRIGGER stop_times_dist_row_trigger BEFORE INSERT ON :schema.stop_times
  FOR EACH ROW
  WHEN (NEW.shape_dist_traveled IS NULL)
  EXECUTE PROCEDURE :schema.dist_insert();

CREATE TRIGGER stop_times_dist_stmt_trigger AFTER INSERT ON :schema.stop_times
  FOR EACH STATEMENT EXECUTE PROCEDURE :schema.dist_update();

CREATE TRIGGER stop_geom_trigger BEFORE INSERT OR UPDATE ON :schema.stops
    FOR EACH ROW EXECUTE PROCEDURE :schema.stop_geom_update();
