
from pathlib import Path
import json
import sqlite3
import pandas as pd


# Primary keys for tables with confirmed unique identifiers.
PRIMARY_KEYS = {
    "plants": ["plant_id"],
    "lines": ["line_id"],
    "machines": ["machine_id"],
    "shifts": ["shift_id"],
    "products": ["product_id"],
    "production_orders": ["order_id"],
    "machine_events": ["event_id"],
    "planned_breaks": ["break_id"],
    "production_counts": ["count_id"],
    "quality_inspections": ["inspection_id"],
    "oee_metrics": ["metric_id"],
    "shift_oee_metrics": ["shift_metric_id"],
}

# Foreign-key relationships based on the current data model.
FOREIGN_KEYS = {
    "lines": [
        ("plant_id", "plants", "plant_id"),
    ],
    "machines": [
        ("line_id", "lines", "line_id"),
    ],
    "production_orders": [
        ("machine_id", "machines", "machine_id"),
        ("product_id", "products", "product_id"),
        ("shift_id", "shifts", "shift_id"),
    ],
    "machine_events": [
        ("machine_id", "machines", "machine_id"),
        ("order_id", "production_orders", "order_id"),
    ],
    "planned_breaks": [
        ("machine_id", "machines", "machine_id"),
    ],
    "production_counts": [
        ("order_id", "production_orders", "order_id"),
        ("machine_id", "machines", "machine_id"),
    ],
    "quality_inspections": [
        ("order_id", "production_orders", "order_id"),
        ("product_id", "products", "product_id"),
    ],
    "oee_metrics": [
        ("order_id", "production_orders", "order_id"),
        ("shift_id", "shifts", "shift_id"),
        ("machine_id", "machines", "machine_id"),
    ],
    "shift_oee_metrics": [
        ("shift_id", "shifts", "shift_id"),
        ("machine_id", "machines", "machine_id"),
    ],
}


def _sqlite_type(series):
    """Infer a SQLite column type from a pandas Series."""
    if pd.api.types.is_bool_dtype(series.dtype):
        return "INTEGER"
    if pd.api.types.is_integer_dtype(series.dtype):
        return "INTEGER"
    if pd.api.types.is_numeric_dtype(series.dtype):
        return "REAL"
    return "TEXT"


def _create_sqlite_table(con, name, df):
    """Create a table with declared primary and foreign keys."""
    if name not in PRIMARY_KEYS:
        raise ValueError(
            f"No primary-key definition configured for table: {name}"
        )

    primary_keys = PRIMARY_KEYS[name]

    missing_pk = set(primary_keys) - set(df.columns)
    if missing_pk:
        raise ValueError(
            f"{name}: missing primary-key columns: {sorted(missing_pk)}"
        )

    definitions = []

    for column in df.columns:
        definition = f'"{column}" {_sqlite_type(df[column])}'

        if column in primary_keys:
            definition += " NOT NULL"

        definitions.append(definition)

    pk_sql = ", ".join(f'"{column}"' for column in primary_keys)
    definitions.append(f"PRIMARY KEY ({pk_sql})")

    for column, parent_table, parent_column in FOREIGN_KEYS.get(name, []):
        if column not in df.columns:
            raise ValueError(
                f"{name}: foreign-key column {column!r} does not exist"
            )

        definitions.append(
            f'FOREIGN KEY ("{column}") '
            f'REFERENCES "{parent_table}"("{parent_column}")'
        )

    columns_sql = ",\n    ".join(definitions)

    con.execute(
        f'CREATE TABLE "{name}" (\n    {columns_sql}\n)'
    )

    # to_sql appends records to the already-constrained table.
    df.to_sql(name, con, if_exists="append", index=False)


def export_dataset(data, out: Path, seed: int, config: dict, report: dict):
    """Export datasets to CSV, JSON, SQLite, and validation files."""
    out.mkdir(parents=True, exist_ok=True)

    # 1. Export every generated table as CSV and JSON.
    for name, df in data.items():
        df.to_csv(out / f"{name}.csv", index=False)

        json_path = out / f"{name}.json"

        with json_path.open("w", encoding="utf-8") as file:
            file.write("[\n")
            first_record = True

            for start in range(0, len(df), 10_000):
                chunk = df.iloc[start:start + 10_000]

                records = json.loads(
                    chunk.to_json(
                        orient="records",
                        date_format="iso",
                    )
                )

                for record in records:
                    if not first_record:
                        file.write(",\n")

                    file.write(json.dumps(record, ensure_ascii=False))
                    first_record = False

            file.write("\n]\n")

    # 2. Export ground truth separately for anomaly evaluation.
    ground_truth = data.get("anomaly_labels")

    if ground_truth is not None:
        ground_truth.to_csv(out / "ground_truth.csv", index=False)

        ground_truth.to_json(
            out / "ground_truth.json",
            orient="records",
            indent=2,
            date_format="iso",
        )

    # 3. Export SQLite tables with explicit constraints.
    db_path = out / "oee_seed.db"

    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")

        # Create parent tables before their dependent tables.
        table_order = [
            "plants",
            "lines",
            "machines",
            "shifts",
            "products",
            "production_orders",
            "machine_events",
            "planned_breaks",
            "production_counts",
            "quality_inspections",
            "oee_metrics",
            "shift_oee_metrics",
            "anomaly_labels",
        ]

        unknown_tables = set(data) - set(table_order)
        if unknown_tables:
            raise ValueError(
                "Add primary-key definitions and table ordering for: "
                + ", ".join(sorted(unknown_tables))
            )

        for name in table_order:
            if name not in data:
                continue

            df = data[name]

            # Drop old tables so reruns use the updated schema.
            con.execute(f'DROP TABLE IF EXISTS "{name}"')

            if name == "anomaly_labels":
                # The current anomaly-label schema has no confirmed
                # primary key. Preserve its records without inventing one.
                definitions = [
                    f'"{column}" {_sqlite_type(df[column])}'
                    for column in df.columns
                ]
                columns_sql = ",\n    ".join(definitions)

                con.execute(
                    f'CREATE TABLE "{name}" (\n    {columns_sql}\n)'
                )
                df.to_sql(name, con, if_exists="append", index=False)
            else:
                _create_sqlite_table(con, name, df)

        # Confirm that all declared foreign keys are satisfied.
        fk_issues = []
        for name in data:
            fk_issues.extend(
                con.execute(
                    f'PRAGMA foreign_key_check("{name}")'
                ).fetchall()
            )

        if fk_issues:
            raise ValueError(
                "SQLite foreign-key validation failed. "
                f"First issues: {fk_issues[:10]}"
            )

        statements = con.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND sql IS NOT NULL
            ORDER BY name
            """
        ).fetchall()

        sql = "\n\n".join(
            statement[0] + ";"
            for statement in statements
        )

    # 4. Export the actual SQLite schema.
    (out / "schema.sql").write_text(
        sql + "\n",
        encoding="utf-8",
    )

    # 5. Export source manifest.
    manifest = {
        "generator": "YottaFlex OEE Synthetic Data Generator",
        "seed": seed,
        "config": config,
        "tables": {
            name: int(len(df))
            for name, df in data.items()
        },
        "ground_truth": {
            "separate_csv": "ground_truth.csv",
            "separate_json": "ground_truth.json",
            "source_table": "anomaly_labels",
            "row_count": (
                int(len(ground_truth))
                if ground_truth is not None
                else 0
            ),
        },
        "validation": {
            "passed": report["passed"],
            "issue_count": report["issue_count"],
            "unexpected_issue_count": report.get(
                "unexpected_issue_count",
                report["issue_count"],
            ),
        },
    }

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str),
        encoding="utf-8",
    )

    # 6. Export validation report.
    (out / "validation_report.json").write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
