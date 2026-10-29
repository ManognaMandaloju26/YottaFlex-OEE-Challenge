
from src.oee_generator import generate_dataset
from src.validation import validate_dataset


def test_reproducible():
    a = generate_dataset(123, 2, 1)
    b = generate_dataset(123, 2, 1)

    assert a["machines"].equals(b["machines"])
    assert a["oee_metrics"].equals(b["oee_metrics"])

    for table in a:
        assert a[table].equals(b[table]), (
            f"{table} is not reproducible"
        )


def test_tables_present():
    data = generate_dataset(1, 2, 1)

    expected_tables = {
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
    }

    assert set(data) == expected_tables


def test_anomaly_detected():
    report = validate_dataset(generate_dataset(42, 2, 1))

    codes = {issue["code"] for issue in report["issues"]}

    assert "negative_total_count" in codes
    assert "subcounts_exceed_total" in codes


def test_required_anomaly_labels_have_schema():
    data = generate_dataset(42, 2, 1)
    labels = data["anomaly_labels"]

    required_columns = {
        "record_type",
        "record_id",
        "anomaly_type",
        "expected_detection",
        "description",
    }

    assert required_columns.issubset(labels.columns)


def test_oee_values_are_in_valid_range():
    data = generate_dataset(42, 2, 1)

    for table_name in ["oee_metrics", "shift_oee_metrics"]:
        metrics = data[table_name]

        for column in [
            "availability",
            "performance",
            "quality",
            "oee",
        ]:
            assert metrics[column].between(0, 1).all(), (
                f"{table_name}.{column} contains values outside 0-1"
            )
