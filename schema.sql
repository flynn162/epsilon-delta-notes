BEGIN TRANSACTION;
-- Schema
CREATE TABLE IF NOT EXISTS "toc" (
       "id" INTEGER NOT NULL UNIQUE,
       "parent_id" INTEGER,
       "next_id" INTEGER,
       "first_child_id" INTEGER,
       "slur" TEXT NOT NULL UNIQUE,
       "title" TEXT NOT NULL,
       "mtime" INTEGER,
       "content_lock" TEXT,
       "first_content_id" INTEGER,
       PRIMARY KEY("id")
);
CREATE TABLE IF NOT EXISTS "content" (
       "id" INTEGER NOT NULL UNIQUE,
       "parent_id" INTEGER NOT NULL,
       "next_id" INTEGER,
       "content" TEXT NOT NULL,
       PRIMARY KEY("id"),
       FOREIGN KEY("parent_id") REFERENCES toc(id)
);
CREATE TABLE IF NOT EXISTS "metadata" (
       "key" string NOT NULL,
       "value_int" integer,
       "value_str" text,
       "value_blob" blob,
       PRIMARY KEY("key")
);
COMMIT;
