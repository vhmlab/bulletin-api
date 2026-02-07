-- Extracted schema for bulletin.db
--
-- Usage instructions
-- 1) BACKUP your database before running this script to avoid data loss:
--      cp bulletin.db bulletin.db.bak
--
-- 2) Apply the schema safely (this file uses IF NOT EXISTS so existing
--    objects will not be dropped or overwritten):
--      sqlite3 bulletin.db < bulletin_schema.sql
--
-- 3) If you prefer to run commands inside the sqlite3 REPL:
--      sqlite3 bulletin.db
--      sqlite> .read bulletin_schema.sql
--
-- 4) If you run inside a virtual environment, ensure the environment's
--    sqlite3 binary/CLI is available, or run the Python snippet that
--    inspects `sqlite_master` (used earlier) instead.
--
-- Note: This script only creates missing tables/indexes (IF NOT EXISTS).
--       It will not modify or drop existing data structures.
--
-- Tables
CREATE TABLE IF NOT EXISTS sabbath_school (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wednesday_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worship_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS youth_service (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    data TEXT NOT NULL
);

-- Unique indexes on date (one per table)
CREATE UNIQUE INDEX IF NOT EXISTS idx_sabbath_school_date_unique ON sabbath_school(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_wednesday_service_date_unique ON wednesday_service(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_worship_service_date_unique ON worship_service(date);
CREATE UNIQUE INDEX IF NOT EXISTS idx_youth_service_date_unique ON youth_service(date);

-- Additional indexes
CREATE INDEX IF NOT EXISTS ix_sabbath_school_date ON sabbath_school (date);
CREATE INDEX IF NOT EXISTS ix_sabbath_school_id ON sabbath_school (id);

CREATE INDEX IF NOT EXISTS ix_wednesday_service_date ON wednesday_service (date);
CREATE INDEX IF NOT EXISTS ix_wednesday_service_id ON wednesday_service (id);

CREATE INDEX IF NOT EXISTS ix_worship_service_date ON worship_service (date);
CREATE INDEX IF NOT EXISTS ix_worship_service_id ON worship_service (id);

CREATE INDEX IF NOT EXISTS ix_youth_service_date ON youth_service (date);
CREATE INDEX IF NOT EXISTS ix_youth_service_id ON youth_service (id);

-- Templates table: stores reusable templates referenced by name
CREATE TABLE IF NOT EXISTS templates (
    name TEXT NOT NULL UNIQUE,
    icon TEXT,
    data TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_templates_name_unique ON templates(name);
