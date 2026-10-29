
"""Data dictionary for the YottaFlex synthetic OEE dataset.

Entity field definitions are aligned with the generator's columns.
Validation rules describe the intended contract for valid baseline records.
Deliberately injected anomaly records may violate these rules.
"""

DATA_DICTIONARY = {
    "plants": {
        "plant_id": ("string", "required", "unique", None, "Non-empty plant identifier"),
        "plant_name": ("string", "required", "not unique", None, "Non-empty name"),
        "timezone": ("string", "required", "not unique", "IANA timezone", "Must be a valid timezone"),
        "location": ("string", "required", "not unique", None, "Non-empty location"),
    },
    "lines": {
        "line_id": ("string", "required", "unique", None, "Must be unique"),
        "plant_id": ("string", "required", "foreign key", None, "Must reference plants.plant_id"),
        "line_name": ("string", "required", "not unique", None, "Non-empty line name"),
    },
    "machines": {
        "machine_id": ("string", "required", "unique", None, "Must be unique"),
        "line_id": ("string", "required", "foreign key", None, "Must reference lines.line_id"),
        "machine_name": ("string", "required", "not unique", None, "Non-empty machine name"),
        "machine_type": ("string", "required", "enum", None, "Must use a documented machine type"),
        "ideal_cycle_time_sec": ("float", "required", "positive", "seconds/unit", "Must be greater than zero for valid records"),
        "active": ("boolean", "required", "boolean", None, "Must be True or False"),
    },
    "shifts": {
        "shift_id": ("string", "required", "unique", None, "Must be unique; target format SHIFT-YYYY-MM-DD-A/B/C"),
        "shift_name": ("string", "required", "not unique", None, "Non-empty shift name"),
        "start_time": ("datetime", "required", "not unique", "timestamp", "Must be earlier than end_time"),
        "end_time": ("datetime", "required", "not unique", "timestamp", "Must be later than start_time"),
    },
    "products": {
        "product_id": ("string", "required", "unique", None, "Must be unique"),
        "product_name": ("string", "required", "not unique", None, "Non-empty product name"),
        "sku": ("string", "required", "unique", None, "Must be unique and non-empty"),
    },
    "production_orders": {
        "order_id": ("string", "required", "unique", None, "Target format PO-YYYY-000001"),
        "machine_id": ("string", "required", "foreign key", None, "Must reference machines.machine_id"),
        "product_id": ("string", "required", "foreign key", None, "Must reference products.product_id"),
        "shift_id": ("string", "required", "foreign key", None, "Must reference shifts.shift_id"),
        "planned_start": ("datetime", "required", "not unique", "timestamp", "Must be earlier than planned_end"),
        "planned_end": ("datetime", "required", "not unique", "timestamp", "Must be later than planned_start"),
        "planned_break_min": ("integer", "required", "non-negative", "minutes", "Must be >= 0 and not exceed planned duration"),
        "target_units": ("integer", "required", "non-negative", "units", "Must be >= 0"),
        "status": ("string", "required", "enum", None, "Document permitted order statuses"),
    },
    "machine_events": {
        "event_id": ("string", "required", "unique", None, "Target format EVT-<machine-id>-000001"),
        "machine_id": ("string", "required", "foreign key", None, "Must reference machines.machine_id"),
        "order_id": ("string", "required", "foreign key", None, "Must reference production_orders.order_id"),
        "event_type": ("string", "required", "enum", None, "Document permitted machine states and transitions"),
        "reason": ("string", "optional", "reason code", None, "Use a documented downtime reason when applicable"),
        "start_time": ("datetime", "required", "not unique", "timestamp", "Must be earlier than end_time"),
        "end_time": ("datetime", "required", "not unique", "timestamp", "Must be later than start_time"),
        "duration_min": ("float", "required", "non-negative", "minutes", "Must match end_time - start_time"),
        "is_planned": ("boolean", "required", "boolean", None, "Must be True or False"),
    },
    "production_counts": {
        "count_id": ("string", "required", "unique", None, "Target format CNT-<order-id>-000001"),
        "order_id": ("string", "required", "foreign key", None, "Must reference production_orders.order_id"),
        "machine_id": ("string", "required", "foreign key", None, "Must reference machines.machine_id"),
        "timestamp": ("datetime", "required", "not unique", "timestamp", "Must fall within the applicable order period for valid records"),
        "total_count": ("integer", "required", "non-negative", "units", "Must be >= 0 for valid records; decreases need correction events"),
        "good_count": ("integer", "required", "non-negative", "units", "Must be <= total_count for valid records"),
        "scrap_count": ("integer", "required", "non-negative", "units", "Must reconcile with production and quality records"),
        "rework_count": ("integer", "required", "non-negative", "units", "Must be >= 0 and reconcile with rework records"),
    },
    "quality_inspections": {
        "inspection_id": ("string", "required", "unique", None, "Target format QC-YYYY-000001"),
        "order_id": ("string", "required", "foreign key", None, "Must reference production_orders.order_id"),
        "product_id": ("string", "required", "foreign key", None, "Must reference products.product_id"),
        "inspection_time": ("datetime", "required", "not unique", "timestamp", "Must be valid and consistent with the order period"),
        "sample_size": ("integer", "required", "positive", "units", "Must be > 0 for valid inspections"),
        "defect_count": ("integer", "required", "non-negative", "defects", "Must be between 0 and sample_size for valid inspections"),
        "inspection_result": ("string", "required", "enum", None, "Document permitted values such as PASS, FAIL and REWORK"),
        "defect_code": ("string", "optional", "code", None, "Must be a documented code when present"),
    },
    "oee_metrics": {
        "metric_id": ("string", "required", "unique", None, "Must be unique"),
        "order_id": ("string", "required", "foreign key", None, "Must reference production_orders.order_id"),
        "machine_id": ("string", "required", "foreign key", None, "Must reference machines.machine_id"),
        "planned_production_sec": ("float", "required", "non-negative", "seconds", "Must be >= 0"),
        "operating_sec": ("float", "required", "non-negative", "seconds", "Must not exceed planned production time for valid records"),
        "ideal_cycle_time_sec": ("float", "required", "positive", "seconds/unit", "Must match the applicable machine/product configuration"),
        "total_count": ("integer", "required", "non-negative", "units", "Must reconcile with source production counts"),
        "good_count": ("integer", "required", "non-negative", "units", "Must reconcile with source production counts"),
        "availability": ("float", "required", "derived", "ratio", "Operating time / planned production time"),
        "performance": ("float", "required", "derived", "ratio", "Ideal cycle time x total count / operating time"),
        "quality": ("float", "required", "derived", "ratio", "Good count / total count"),
        "oee": ("float", "required", "derived", "ratio", "Availability x performance x quality"),
        "oee_percent": ("float", "required", "derived", "percent", "Must equal oee x 100"),
    },
    "shift_oee_metrics": {
        "shift_metric_id": ("string", "required", "unique", None, "Must be unique"),
        "shift_id": ("string", "required", "foreign key", None, "Must reference shifts.shift_id"),
        "machine_id": ("string", "required", "foreign key", None, "Must reference machines.machine_id"),
        "planned_production_sec": ("float", "required", "non-negative", "seconds", "Must be >= 0"),
        "operating_sec": ("float", "required", "non-negative", "seconds", "Must not exceed planned production time"),
        "total_count": ("integer", "required", "non-negative", "units", "Must reconcile with production counts"),
        "good_count": ("integer", "required", "non-negative", "units", "Must reconcile with production counts"),
        "availability": ("float", "required", "derived", "ratio", "Operating time / planned production time"),
        "performance": ("float", "required", "derived", "ratio", "Ideal cycle time x total count / operating time"),
        "quality": ("float", "required", "derived", "ratio", "Good count / total count"),
        "oee": ("float", "required", "derived", "ratio", "Availability x performance x quality"),
        "oee_percent": ("float", "required", "derived", "percent", "Must equal oee x 100"),
    },
    "anomaly_labels": {
        "record_type": ("string", "required", "enum", None, "Must identify the affected table or record type"),
        "record_id": ("string", "required", "reference", None, "Must identify the affected record"),
        "anomaly_type": ("string", "required", "enum", None, "Must identify the injected anomaly"),
        "expected_detection": ("boolean", "required", "boolean", None, "Must indicate whether validation should detect it"),
        "description": ("string", "required", "not unique", None, "Explain the anomaly and expected detection"),
    },
}

# Reasons are currently represented by machine_events.reason.
# This is a controlled vocabulary, not a separate generated table.
DOWNTIME_REASON_CODES = {
    "PLANNED_BREAK": "Scheduled break",
    "MICRO_STOP": "Short unplanned stop",
    "CHANGEOVER": "Product or setup change",
    "BREAKDOWN": "Equipment failure",
    "MAINTENANCE": "Maintenance activity",
    "OTHER": "Other downtime reason",
}


def print_data_dictionary():
    """Print every documented field and its metadata."""
    for entity, fields in DATA_DICTIONARY.items():
        print(f"\n[{entity}]")
        for field, details in fields.items():
            field_type, required, uniqueness, units, rule = details
            print(
                f"{field}: type={field_type}; required={required}; "
                f"uniqueness={uniqueness}; units={units}; rule={rule}"
            )


if __name__ == "__main__":
    print_data_dictionary()
