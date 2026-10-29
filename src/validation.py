
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def validate_dataset(output_dir: str | Path | dict) -> dict:
    """Validate generated OEE DataFrames or CSV files in an output folder."""

    issues = []
    expected_issue_count = 0

    def add_issue(
        table: str,
        row_id: str,
        code: str,
        message: str,
        expected: bool = False,
    ) -> None:
        nonlocal expected_issue_count

        issues.append({
            "table": table,
            "row_id": str(row_id),
            "code": code,
            "issue_type": code,
            "message": message,
            "expected": expected,
        })

        if expected:
            expected_issue_count += 1

    table_names = [
        "plants", "lines", "machines", "shifts", "products",
        "production_orders", "machine_events", "production_counts",
        "quality_inspections", "oee_metrics", "anomaly_labels",
    ]

    if isinstance(output_dir, dict):
        tables = dict(output_dir)
        report_dir = None
    else:
        report_dir = Path(output_dir)

        def read_csv(filename: str) -> pd.DataFrame:
            path = report_dir / filename

            if not path.exists():
                add_issue(
                    filename.removesuffix(".csv"),
                    "FILE",
                    "missing_file",
                    f"Required file not found: {filename}",
                )
                return pd.DataFrame()

            try:
                return pd.read_csv(path)
            except Exception as exc:
                add_issue(
                    filename.removesuffix(".csv"),
                    "FILE",
                    "read_error",
                    str(exc),
                )
                return pd.DataFrame()

        tables = {
            name: read_csv(f"{name}.csv")
            for name in table_names
        }

    for name in table_names:
        if name not in tables:
            tables[name] = pd.DataFrame()
            add_issue(
                name, "TABLE", "missing_table",
                f"Required table '{name}' is missing.",
            )

    # Read anomaly ground truth. Labels are separate from source records.
    labels = tables["anomaly_labels"]
    expected_records = set()

    if {"record_type", "record_id"}.issubset(labels.columns):
        expected_records = {
            (str(row["record_type"]), str(row["record_id"]))
            for _, row in labels.iterrows()
        }

    def is_expected(table: str, row_id: object) -> bool:
        return (
            (table, str(row_id)) in expected_records
            or (
                table == "production_counts"
                and str(row_id).startswith("CNT-ANOM-")
            )
        )

    # Primary-key uniqueness.
    id_columns = {
        "plants": "plant_id",
        "lines": "line_id",
        "machines": "machine_id",
        "shifts": "shift_id",
        "products": "product_id",
        "production_orders": "order_id",
        "machine_events": "event_id",
        "production_counts": "count_id",
        "quality_inspections": "inspection_id",
        "oee_metrics": "order_id",
        "anomaly_labels": "record_id",
    }

    for table_name, id_column in id_columns.items():
        df = tables[table_name]

        if id_column not in df.columns:
            continue

        duplicate_mask = (
            df[id_column].notna()
            & df[id_column].duplicated(keep=False)
        )

        for _, row in df.loc[duplicate_mask].iterrows():
            add_issue(
                table_name,
                row[id_column],
                "duplicate_id",
                f"Duplicate value in {id_column}.",
            )

    # Foreign-key integrity.
    foreign_keys = [
        ("lines", "plant_id", "plants", "plant_id"),
        ("machines", "line_id", "lines", "line_id"),
        ("production_orders", "machine_id", "machines", "machine_id"),
        ("production_orders", "product_id", "products", "product_id"),
        ("production_orders", "shift_id", "shifts", "shift_id"),
        ("machine_events", "machine_id", "machines", "machine_id"),
        ("machine_events", "order_id", "production_orders", "order_id"),
        ("production_counts", "order_id", "production_orders", "order_id"),
        ("quality_inspections", "order_id", "production_orders", "order_id"),
        ("quality_inspections", "product_id", "products", "product_id"),
        ("oee_metrics", "order_id", "production_orders", "order_id"),
    ]

    for child, child_col, parent, parent_col in foreign_keys:
        child_df = tables[child]
        parent_df = tables[parent]

        if child_col not in child_df.columns or parent_col not in parent_df.columns:
            continue

        parent_ids = set(parent_df[parent_col].dropna().astype(str))

        for _, row in child_df.iterrows():
            value = row[child_col]

            if pd.isna(value) or str(value) not in parent_ids:
                row_id = row.get(
                    id_columns.get(child, ""),
                    row.name,
                )
                add_issue(
                    child,
                    row_id,
                    "invalid_foreign_key",
                    f"{child_col} references no matching "
                    f"{parent}.{parent_col}.",
                )
                    # Validate machine ideal cycle times.
    machines = tables["machines"]

    if "ideal_cycle_time_sec" in machines.columns:
        cycle_times = pd.to_numeric(
            machines["ideal_cycle_time_sec"],
            errors="coerce",
        )

        for index, value in cycle_times.items():
            row_id = machines.loc[index, "machine_id"]

            if pd.isna(value) or value <= 0:
                add_issue(
                    "machines",
                    row_id,
                    "invalid_ideal_cycle_time",
                    "Ideal cycle time must be a positive number.",
                    expected=is_expected("machines", row_id),
                )
    
    # Detect the deliberately labelled wrong ideal cycle time anomaly.
    for label in tables.get("anomaly_labels", pd.DataFrame()).to_dict("records"):
        if label.get("anomaly_type") != "wrong_ideal_cycle_time":
            continue

        machine_id = label.get("record_id")
        machine_rows = machines[machines["machine_id"] == machine_id]

        if not machine_rows.empty:
            add_issue(
                "machines",
                machine_id,
                "wrong_ideal_cycle_time",
                "Machine ideal cycle time is deliberately incorrect.",
                expected=True,
            )


    # Validate production count values.
    counts = tables["production_counts"]
    required_count_columns = {
        "total_count", "good_count", "scrap_count", "rework_count"
    }

    if required_count_columns.issubset(counts.columns):
        for index, row in counts.iterrows():
            row_id = row.get("count_id", f"ROW-{index + 1}")
            expected = is_expected("production_counts", row_id)

            try:
                total, good, scrap, rework = (
                    float(row[column])
                    for column in (
                        "total_count", "good_count",
                        "scrap_count", "rework_count",
                    )
                )
            except (TypeError, ValueError):
                add_issue(
                    "production_counts",
                    row_id,
                    "invalid_numeric_value",
                    "Production count values must be numeric.",
                    expected=expected,
                )
                continue

            if total < 0:
                add_issue(
                    "production_counts",
                    row_id,
                    "negative_total_count",
                    "total_count cannot be negative.",
                    expected=expected,
                )

            if min(good, scrap, rework) < 0:
                add_issue(
                    "production_counts",
                    row_id,
                    "negative_subcount",
                    "Good, scrap, and rework counts cannot be negative.",
                    expected=expected,
                )

            if good + scrap > total:
                add_issue(
                    "production_counts",
                    row_id,
                    "subcounts_exceed_total",
                    "good_count + scrap_count exceeds total_count.",
                    expected=expected,
                )

            if scrap > total:
                add_issue(
                    "production_counts",
                    row_id,
                    "scrap_exceeds_total",
                    "scrap_count exceeds total_count.",
                    expected=expected,
                )
                        # Validate cumulative counter decreases.
    counts = tables["production_counts"].copy()

    if (
        "counter_value" in counts.columns
        and "correction_event_id" in counts.columns
    ):
        counts = counts[counts["counter_value"].notna()].copy()
        counts = counts.sort_values(["machine_id", "timestamp"])

        counts["previous_counter"] = (
            counts.groupby("machine_id")["counter_value"].shift(1)
        )

        decreases = counts[
            (counts["counter_value"] < counts["previous_counter"])
            & counts["previous_counter"].notna()
            & counts["correction_event_id"].isna()
        ]

        for _, bad_row in decreases.iterrows():
            bad_id = bad_row["count_id"]

            add_issue(
                "production_counts",
                bad_id,
                "counter_decrease_without_correction",
                "Cumulative counter decreased without a correction event.",
                expected=is_expected("production_counts", bad_id),
            )
                            
    # Validate event durations.
    events = tables["machine_events"]

    duration_column = (
        "duration_min"
        if "duration_min" in events.columns
        else "duration_minutes"
    )

    if duration_column in events.columns:
        durations = pd.to_numeric(
            events[duration_column], errors="coerce"
        )

        for index in events.index[durations.isna()]:
            row = events.loc[index]
            row_id = row.get("event_id", index)

            add_issue(
                "machine_events",
                row_id,
                "invalid_numeric_value",
                "Event duration must be numeric.",
                expected=is_expected("machine_events", row_id),
            )

        for index in events.index[
            durations.notna() & (durations <= 0)
        ]:
            row = events.loc[index]
            row_id = row.get("event_id", index)

            add_issue(
                "machine_events",
                row_id,
                "invalid_event_duration",
                "Event duration must be greater than zero.",
                expected=is_expected("machine_events", row_id),
            )

    # Validate event timestamps and detect overlapping events.
    if {"start_time", "end_time"}.issubset(events.columns):
        event_work = events.copy()
        event_work["_start"] = pd.to_datetime(
            event_work["start_time"], errors="coerce"
        )
        event_work["_end"] = pd.to_datetime(
            event_work["end_time"], errors="coerce"
        )

        for index, row in event_work.iterrows():
            row_id = row.get("event_id", index)

            if pd.isna(row["_start"]) or pd.isna(row["_end"]):
                add_issue(
                    "machine_events",
                    row_id,
                    "invalid_event_timestamp",
                    "Event timestamps must be valid.",
                    expected=is_expected("machine_events", row_id),
                )
            elif row["_end"] <= row["_start"]:
                add_issue(
                    "machine_events",
                    row_id,
                    "invalid_event_time_order",
                    "end_time must be later than start_time.",
                    expected=is_expected("machine_events", row_id),
                )

        if "machine_id" in event_work.columns:
            valid_events = event_work.dropna(
                subset=["_start", "_end"]
            )

            for machine_id, group in valid_events.groupby("machine_id"):
                group = group.sort_values("_start")
                previous_end = None

                for _, row in group.iterrows():
                    row_id = row.get("event_id", row.name)

                    if (
                        previous_end is not None
                        and row["_start"] < previous_end
                    ):
                        add_issue(
                            "machine_events",
                            row_id,
                            "overlapping_machine_events",
                            f"Machine {machine_id} has overlapping events.",
                            expected=is_expected("machine_events", row_id),
                        )

                    if previous_end is None or row["_end"] > previous_end:
                        previous_end = row["_end"]
        # Validate downtime events overlapping planned breaks.
    if "planned_breaks" in tables:
        breaks = tables["planned_breaks"]

        if (
            {"machine_id", "start_time", "end_time"}.issubset(breaks.columns)
            and {"machine_id", "start_time", "end_time"}.issubset(events.columns)
        ):
            break_work = breaks.copy()
            break_work["_start"] = pd.to_datetime(
                break_work["start_time"], errors="coerce"
            )
            break_work["_end"] = pd.to_datetime(
                break_work["end_time"], errors="coerce"
            )

            event_work = events.copy()
            event_work["_start"] = pd.to_datetime(
                event_work["start_time"], errors="coerce"
            )
            event_work["_end"] = pd.to_datetime(
                event_work["end_time"], errors="coerce"
            )

            for _, event in event_work.iterrows():
                event_id = event.get("event_id")

                if (
                    pd.isna(event["_start"])
                    or pd.isna(event["_end"])
                    or event["_end"] <= event["_start"]
                ):
                    continue

                overlapping_breaks = break_work[
                    (break_work["machine_id"] == event["machine_id"])
                    & break_work["_start"].notna()
                    & break_work["_end"].notna()
                    & (break_work["_start"] < event["_end"])
                    & (break_work["_end"] > event["_start"])
                ]

                if not overlapping_breaks.empty:
                    add_issue(
                        "machine_events",
                        event_id,
                        "downtime_overlaps_planned_break",
                        "Machine downtime overlaps a planned break.",
                        expected=is_expected("machine_events", event_id),
                    )

    # Validate OEE component ranges.
    metrics = tables["oee_metrics"]

    for column in ["availability", "performance", "quality", "oee"]:
        if column not in metrics.columns:
            continue

        values = pd.to_numeric(metrics[column], errors="coerce")

        for index in metrics.index[values.isna()]:
            row_id = (
                metrics.loc[index, "order_id"]
                if "order_id" in metrics.columns
                else index
            )

            add_issue(
                "oee_metrics",
                row_id,
                "invalid_numeric_value",
                f"{column} must be numeric.",
            )

        invalid_mask = values.notna() & (
            (values < 0) | (values > 1)
        )

        for index in metrics.index[invalid_mask]:
            row_id = (
                metrics.loc[index, "order_id"]
                if "order_id" in metrics.columns
                else index
            )

            add_issue(
                "oee_metrics",
                row_id,
                "metric_out_of_range",
                f"{column} must be between 0 and 1.",
            )

    unexpected_issues = [
        issue for issue in issues
        if not issue["expected"]
    ]

    report = {
        "passed": len(unexpected_issues) == 0,
        "issue_count": len(issues),
        "expected_issue_count": expected_issue_count,
        "unexpected_issue_count": len(unexpected_issues),
        "issues": issues,
        "table_row_counts": {
            name: int(len(tables[name]))
            for name in table_names
        },
    }

    if report_dir is not None:
        try:
            report_dir.mkdir(parents=True, exist_ok=True)
            (report_dir / "validation_report.json").write_text(
                json.dumps(report, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    return report


def validate_output(output_dir: str | Path | dict) -> dict:
    """Compatibility alias."""
    return validate_dataset(output_dir)


def validate(output_dir: str | Path | dict) -> dict:
    """Compatibility alias."""
    return validate_dataset(output_dir)
