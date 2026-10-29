
import sqlite3
from pathlib import Path

db_path = Path("output_schema_test/oee_seed.db")

if not db_path.exists():
    print(f"ERROR: Database not found: {db_path.resolve()}")
else:
    with sqlite3.connect(db_path) as con:
        # Check foreign-key violations
        violations = con.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        print("Foreign-key violations:", violations)

        # Count tables, excluding SQLite's internal tables
        table_count = con.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchone()[0]
        print("Table count:", table_count)

        # List table names
        tables = con.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        print("Table names:")
        for (table_name,) in tables:
            print("-", table_name)
