# Whenever a row really changes and the caller did not write `updated_at` itself, the trigger
# does. `save()` always writes it, as Django does: a pro's own fields live in another table than
# her `updated_at`, so her row in that one would look unchanged. Postgres only computes a generated
# column such as `search_vector` after this trigger, so it would always look changed.
SET_UPDATED_AT = """
CREATE OR REPLACE FUNCTION techpourtoutes_set_updated_at() RETURNS trigger AS $$
BEGIN
    IF NEW.updated_at IS NOT DISTINCT FROM OLD.updated_at
        AND (to_jsonb(NEW) - 'updated_at' - 'search_vector')
            IS DISTINCT FROM (to_jsonb(OLD) - 'updated_at' - 'search_vector')
    THEN
        NEW.updated_at := clock_timestamp();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    table_name text;
BEGIN
    FOR table_name IN
        SELECT columns.table_name
        FROM information_schema.columns
        WHERE columns.table_schema = current_schema()
            AND columns.column_name = 'updated_at'
            AND columns.table_name LIKE 'techpourtoutes\\_%'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS set_updated_at ON %I', table_name);
        EXECUTE format(
            'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION techpourtoutes_set_updated_at()',
            table_name
        );
    END LOOP;
END;
$$;
"""


def install_updated_at_triggers(connection) -> None:
    """`auto_now` only moves `updated_at` in `save()`: `QuerySet.update()` and the imports'
    `bulk_create` leave it alone, hence a trigger on every table of the app holding one.

    Run after every `migrate`, so that a new model gets it without a migration of its own.
    """
    with connection.cursor() as cursor:
        cursor.execute(SET_UPDATED_AT)
