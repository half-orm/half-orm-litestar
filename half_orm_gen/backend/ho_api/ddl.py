"""DDL for the "half_orm_meta.api" schema."""

HO_API_DDL = """\
CREATE SCHEMA IF NOT EXISTS "half_orm_meta.api";

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".role (
  name      text PRIMARY KEY,
  deletable boolean NOT NULL DEFAULT TRUE
);

CREATE OR REPLACE FUNCTION "half_orm_meta.api".check_role_deletable()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.name IN ('anonymous', 'connected', 'admin') THEN
    RAISE EXCEPTION 'Role "%" is a system role and cannot be deleted', OLD.name;
  END IF;
  IF NOT OLD.deletable THEN
    RAISE EXCEPTION 'Role "%" cannot be deleted (deletable = FALSE)', OLD.name;
  END IF;
  RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = 'trg_check_role_deletable'
      AND tgrelid = '"half_orm_meta.api".role'::regclass
  ) THEN
    CREATE TRIGGER trg_check_role_deletable
      BEFORE DELETE ON "half_orm_meta.api".role
      FOR EACH ROW EXECUTE FUNCTION "half_orm_meta.api".check_role_deletable();
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".route (
  schema_name  text NOT NULL,
  table_name   text NOT NULL,
  verb         text NOT NULL CHECK (verb IN ('GET', 'POST', 'PUT', 'DELETE')),
  deprecated   boolean NOT NULL DEFAULT FALSE,
  PRIMARY KEY (schema_name, table_name, verb)
);

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".field (
  schema_name  text NOT NULL,
  table_name   text NOT NULL,
  column_name  text NOT NULL,
  deprecated   boolean NOT NULL DEFAULT FALSE,
  PRIMARY KEY (schema_name, table_name, column_name)
);

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".access (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  role_name       text NOT NULL REFERENCES "half_orm_meta.api".role(name) ON DELETE CASCADE,
  schema_name     text NOT NULL,
  table_name      text NOT NULL,
  verb            text NOT NULL,
  all_fields_in   boolean NOT NULL DEFAULT FALSE,
  all_fields_out  boolean NOT NULL DEFAULT FALSE,
  FOREIGN KEY (schema_name, table_name, verb)
    REFERENCES "half_orm_meta.api".route(schema_name, table_name, verb) ON DELETE CASCADE,
  UNIQUE (role_name, schema_name, table_name, verb)
);

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".field_access_in (
  access_id  uuid NOT NULL REFERENCES "half_orm_meta.api".access(id) ON DELETE CASCADE,
  field_name text NOT NULL,
  PRIMARY KEY (access_id, field_name)
);

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".field_access_out (
  access_id  uuid NOT NULL REFERENCES "half_orm_meta.api".access(id) ON DELETE CASCADE,
  field_name text NOT NULL,
  PRIMARY KEY (access_id, field_name)
);

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".filter (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  schema_name text NOT NULL,
  table_name  text NOT NULL,
  name        text NOT NULL,
  UNIQUE (schema_name, table_name, name)
);

CREATE TABLE IF NOT EXISTS "half_orm_meta.api".access_filter (
  access_id uuid NOT NULL REFERENCES "half_orm_meta.api".access(id) ON DELETE CASCADE,
  filter_id uuid NOT NULL REFERENCES "half_orm_meta.api".filter(id) ON DELETE CASCADE,
  PRIMARY KEY (access_id, filter_id)
);

CREATE OR REPLACE FUNCTION "half_orm_meta.api".check_filter_relation()
RETURNS TRIGGER AS $$
DECLARE
  v_fs text; v_ft text; v_as text; v_at text;
BEGIN
  SELECT schema_name, table_name INTO v_fs, v_ft
    FROM "half_orm_meta.api".filter WHERE id = NEW.filter_id;
  SELECT schema_name, table_name INTO v_as, v_at
    FROM "half_orm_meta.api".access WHERE id = NEW.access_id;
  IF v_fs != v_as OR v_ft != v_at THEN
    RAISE EXCEPTION 'Filter (%.%) cannot be applied to access on %.%',
      v_fs, v_ft, v_as, v_at;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger
    WHERE tgname = 'trg_check_filter_relation'
      AND tgrelid = '"half_orm_meta.api".access_filter'::regclass
  ) THEN
    CREATE TRIGGER trg_check_filter_relation
      BEFORE INSERT OR UPDATE ON "half_orm_meta.api".access_filter
      FOR EACH ROW EXECUTE FUNCTION "half_orm_meta.api".check_filter_relation();
  END IF;
END $$;
"""
