"""Tiny idempotent schema patches for SQLite.

create_all() adds new *tables* but never new *columns* on existing tables, so
a DB created before a column was added would be missing it. This adds any
missing columns on startup - safe to run every boot. (If this grows, switch
to Alembic.)
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# (table, column, column definition)
_COLUMNS: list[tuple[str, str, str]] = [
    ("solicitations", "naics_code", "VARCHAR"),
    ("outreach_drafts", "recipient_email", "VARCHAR"),
    ("outreach_drafts", "message_id", "VARCHAR"),
]


def run_lightweight_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, column, coltype in _COLUMNS:
            if table not in existing_tables:
                continue  # create_all will make the whole table fresh
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column not in cols:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {coltype}'))
