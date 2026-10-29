
import random
from datetime import date, datetime, time, timedelta

import pandas as pd


def generate_dataset(
    seed=42,
    machine_count=5,
    days=3,
    target_events=None,
    target_counts=None,
    line_count=5,
    product_count=20,
):
    """Generate reproducible synthetic manufacturing OEE data."""

    if machine_count < 1 or days < 1:
        raise ValueError("machine_count and days must be positive")
    if line_count < 1 or product_count < 1:
        raise ValueError("line_count and product_count must be positive")
    if target_events is not None and target_events < 0:
        raise ValueError("target_events cannot be negative")
    if target_counts is not None and target_counts < 1:
        raise ValueError("target_counts must be at least 1")

    rng = random.Random(seed)
    first_day = date(2026, 1, 5)

    plants = pd.DataFrame([{
        "plant_id": "PLANT-001",
        "plant_name": "North Plant",
        "timezone": "Asia/Kolkata",
        "location": "Hyderabad",
    }])

    lines = pd.DataFrame([
        {
            "line_id": f"LINE-{i:03d}",
            "plant_id": "PLANT-001",
            "line_name": f"Production Line {i}",
        }
        for i in range(1, line_count + 1)
    ])

    shifts = pd.DataFrame([
        {
            "shift_id": f"SHIFT-{(first_day + timedelta(days=d)).isoformat()}-{code}",
            "shift_name": name,
            "start_time": start,
            "end_time": end,
        }
        for d in range(days)
        for code, name, start, end in [
            ("A", "Morning", "06:00", "14:00"),
            ("B", "Evening", "14:00", "22:00"),
            ("C", "Night", "22:00", "06:00"),
        ]
    ])

    products = pd.DataFrame([
        {
            "product_id": f"PROD-{i:03d}",
            "product_name": f"Product {i}",
            "sku": f"SKU-{i:04d}",
        }
        for i in range(1, product_count + 1)
    ])

    machine_rows = []
    for i in range(1, machine_count + 1):
        machine_rows.append({
            "machine_id": f"MCH-{i:03d}",
            "line_id": f"LINE-{((i - 1) % line_count) + 1:03d}",
            "machine_name": f"Machine {i}",
            "machine_type": ["Assembler", "Packer", "Cutter"][(i - 1) % 3],
            "ideal_cycle_time_sec": rng.choice([2.5, 3.0, 4.0, 5.0]),
            "active": True,
        })
    # Keep the baseline cycle times for production calculations. The machine
    # master data below contains one deliberate anomaly for validator testing.
    baseline_cycle_times = {
        row["machine_id"]: row["ideal_cycle_time_sec"]
        for row in machine_rows
    }

    # Inject a deliberate wrong ideal cycle time anomaly.
    wrong_cycle_machine = machine_rows[0]
    original_cycle_time = wrong_cycle_machine["ideal_cycle_time_sec"]

    wrong_cycle_machine["ideal_cycle_time_sec"] = (
        original_cycle_time * 10
    )

    wrong_cycle_machine_id = wrong_cycle_machine["machine_id"]

    machines = pd.DataFrame(machine_rows)
    product_rows = products.to_dict("records")

    # Create one production order per machine per day.
    orders = []
    order_lookup = []
    order_number = 0

    for day_index in range(days):
        day = first_day + timedelta(days=day_index)

        for machine in machine_rows:
            start = datetime.combine(day, time(6, 0))
            end = start + timedelta(hours=8)
            product = product_rows[rng.randrange(product_count)]

            order_number += 1
            order_id = f"PO-{day.year}-{order_number:06d}"
            shift_id = f"SHIFT-{day.isoformat()}-A"

            ideal_cycle_time = baseline_cycle_times[machine["machine_id"]]
            # Choose a feasible target below theoretical capacity so normal
            # production does not create impossible performance values.
            planned_production_seconds = 8 * 3600 - 30 * 60
            target_units = int(
                (planned_production_seconds / ideal_cycle_time)
                * rng.uniform(0.45, 0.60)
            )

            orders.append({
                "order_id": order_id,
                "machine_id": machine["machine_id"],
                "product_id": product["product_id"],
                "shift_id": shift_id,
                "planned_start": start.isoformat(timespec="seconds"),
                "planned_end": end.isoformat(timespec="seconds"),
                "planned_break_min": 30,
                "target_units": target_units,
                "status": "completed",
            })

            order_lookup.append({
                "order_id": order_id,
                "machine_id": machine["machine_id"],
                "product_id": product["product_id"],
                "start": start,
                "end": end,
                "ideal_cycle_time_sec": ideal_cycle_time,
                "target_units": target_units,
            })

    # Production counts are incremental records.
    # Reserve one record for the intentional anomaly.
    base_count_target = (
        target_counts if target_counts is not None
        else machine_count * days
    )
    normal_count_target = base_count_target - 2

    counts = []
    # Spread each order's target production across its assigned count records.
    # This keeps the synthetic totals consistent with the order target and
    # prevents hundreds of thousands of records from implying impossible output.
    records_per_order = {
        order["order_id"]: (
            normal_count_target // len(order_lookup)
            + (1 if order_index < normal_count_target % len(order_lookup) else 0)
        )
        for order_index, order in enumerate(order_lookup)
    }
    count_totals = {o["order_id"]: 0 for o in order_lookup}
    count_goods = {o["order_id"]: 0 for o in order_lookup}
    count_scrap = {o["order_id"]: 0 for o in order_lookup}
    count_sequence_by_order = {}
    counter_value_by_machine = {}
    count_decrease_anomaly_label = None

    for index in range(normal_count_target):
        order_index = index % len(order_lookup)
        order = order_lookup[order_index]
        sequence = count_sequence_by_order.get(order["order_id"], 0) + 1
        count_sequence_by_order[order["order_id"]] = sequence

        record_count = records_per_order[order["order_id"]]
        base_units, extra_units = divmod(
            int(order["target_units"]), max(1, record_count)
        )
        total = base_units + (1 if sequence <= extra_units else 0)
        scrap = rng.randint(0, total // 20)
        good = total - scrap
        rework = rng.randint(0, min(5, scrap))

        timestamp = order["start"] + timedelta(
            seconds=rng.randrange(0, 8 * 60 * 60)
        )

        sequence = count_sequence_by_order.get(order["order_id"], 0) + 1
        count_sequence_by_order[order["order_id"]] = sequence
        

        # Track a cumulative counter for each machine.
        previous_counter = counter_value_by_machine.get(
            order["machine_id"], 0
        )
        counter_value = previous_counter + total
        counter_value_by_machine[order["machine_id"]] = counter_value

        counts.append({
            "count_id": f"CNT-{order['order_id']}-{sequence:06d}",
            "order_id": order["order_id"],
            "machine_id": order["machine_id"],
            "timestamp": timestamp.isoformat(timespec="seconds"),
            "total_count": total,
            "counter_value": counter_value,
            "correction_event_id": None,
            "good_count": good,
            "scrap_count": scrap,
            "rework_count": rework,
        })

        count_totals[order["order_id"]] += total
        count_goods[order["order_id"]] += good
        count_scrap[order["order_id"]] += scrap

    # Rebuild cumulative counters in timestamp order for each machine.
    # This keeps normal counter readings monotonic before anomaly injection.
    counts_by_machine = {}
    for count in counts:
        counts_by_machine.setdefault(count["machine_id"], []).append(count)

    for machine_counts in counts_by_machine.values():
        running_counter = 0
        for count in sorted(machine_counts, key=lambda row: row["timestamp"]):
            running_counter += int(count["total_count"])
            count["counter_value"] = running_counter

    # Inject one labelled counter decrease without a correction event.
    count_decrease_anomaly_label = None
    for machine_id, machine_counts in counts_by_machine.items():
        ordered_counts = sorted(machine_counts, key=lambda row: row["timestamp"])
        if len(ordered_counts) >= 2:
            earlier = ordered_counts[0]
            later = ordered_counts[1]
            later["counter_value"] = max(0, int(earlier["counter_value"]) - 10)
            later["correction_event_id"] = None
            count_decrease_anomaly_label = {
                "record_type": "production_counts",
                "record_id": later["count_id"],
                "anomaly_type": "counter_decrease_without_correction",
                "expected_detection": True,
                "description": (
                    "Cumulative counter decreases without a correction event."
                ),
            }
            break

    # Generate machine events in 10-minute slots.
    desired_events = (
        target_events
        if target_events is not None
        else machine_count * days * 2
    )

    slots_per_machine_day = 48
    capacity = machine_count * days * slots_per_machine_day

    if desired_events > capacity:
        raise ValueError(
            f"Requested {desired_events:,} events, but the current "
            f"non-overlapping schedule supports at most {capacity:,}. "
            "Increase the schedule capacity or reduce target_events."
        )

    event_slots = []
    for day_index in range(days):
        day = first_day + timedelta(days=day_index)

        for machine in machine_rows:
            start_of_shift = datetime.combine(day, time(6, 0))

            for slot_index in range(slots_per_machine_day):
                event_start = start_of_shift + timedelta(
                    minutes=slot_index * 10
                )
                event_slots.append((machine, event_start))

    rng.shuffle(event_slots)
    event_slots.sort(
        key=lambda slot: (slot[1], slot[0]["machine_id"])
    )

    orders_by_machine_day = {
        (order["machine_id"], order["start"].date()): order
        for order in order_lookup
    }

    event_anomaly_labels = []
    events = []
    event_sequence_by_machine = {}

    for index, (machine, start) in enumerate(
        event_slots[:desired_events]
    ):
        duration = rng.randint(3, 8)

        linked_order = orders_by_machine_day[
            (machine["machine_id"], start.date())
        ]

        end = start + timedelta(minutes=duration)

        sequence = (
            event_sequence_by_machine.get(machine["machine_id"], 0) + 1
        )
        event_sequence_by_machine[machine["machine_id"]] = sequence

        events.append({
            "event_id": (
                f"EVT-{machine['machine_id']}-{sequence:06d}"
            ),
            "machine_id": machine["machine_id"],
            "order_id": linked_order["order_id"],
            "event_type": "downtime",
            "reason": [
                "Mechanical",
                "Material Shortage",
                "Changeover",
                "Planned Maintenance",
            ][index % 4],
            "start_time": start.isoformat(timespec="seconds"),
            "end_time": end.isoformat(timespec="seconds"),
            "duration_min": duration,
            "is_planned": index % 4 in (2, 3),
        })
            # Inject one labelled overlapping-event anomaly.
    # Keep the total event count unchanged.
    events_by_machine = {}

    for event in events:
        events_by_machine.setdefault(
            event["machine_id"], []
        ).append(event)

    for machine_id, machine_events in events_by_machine.items():
        if len(machine_events) >= 2:
            first = machine_events[0]
            second = machine_events[1]

            first_start = datetime.fromisoformat(first["start_time"])
            second_start = first_start + timedelta(minutes=2)

            second_end = second_start + timedelta(
                minutes=int(second["duration_min"])
            )

            second["start_time"] = second_start.isoformat(
                timespec="seconds"
            )
            second["end_time"] = second_end.isoformat(
                timespec="seconds"
            )

            event_anomaly_labels.append({
                "record_type": "machine_events",
                "record_id": second["event_id"],
                "anomaly_type": "overlapping_machine_states",
                "expected_detection": True,
                "description": (
                    "Machine event overlaps another event "
                    "for the same machine."
                ),
            })
            break

    
    # Aggregate unplanned downtime by production order.
    # Merge overlapping intervals to avoid double-counting.
    downtime_intervals = {o["order_id"]: [] for o in order_lookup}
    downtime_seconds = {o["order_id"]: 0 for o in order_lookup}

    for event in events:
        if event["is_planned"]:
            continue

        order_id = event["order_id"]
        if order_id not in downtime_intervals:
            continue

        event_start = datetime.fromisoformat(event["start_time"])
        event_end = datetime.fromisoformat(event["end_time"])

        order = next(
            o for o in order_lookup
            if o["order_id"] == order_id
        )

        # Restrict downtime to the production order's time window.
        interval_start = max(event_start, order["start"])
        interval_end = min(event_end, order["end"])

        if interval_end > interval_start:
            downtime_intervals[order_id].append(
                (interval_start, interval_end)
            )

    for order_id, intervals in downtime_intervals.items():
        intervals.sort(key=lambda interval: interval[0])

        if not intervals:
            continue

        merged_start, merged_end = intervals[0]
        total_seconds = 0

        for interval_start, interval_end in intervals[1:]:
            if interval_start <= merged_end:
                merged_end = max(merged_end, interval_end)
            else:
                total_seconds += int(
                    (merged_end - merged_start).total_seconds()
                )
                merged_start, merged_end = interval_start, interval_end

        total_seconds += int(
            (merged_end - merged_start).total_seconds()
        )

        downtime_seconds[order_id] = total_seconds

    planned_breaks = []


    # Inject one deliberate downtime-overlap anomaly for validation.
    if events:
        planned_break_event = events[0]

        event_start = datetime.fromisoformat(
            planned_break_event["start_time"]
        )

        break_start = event_start + timedelta(minutes=2)
        break_end = break_start + timedelta(minutes=15)

        planned_breaks.append({
            "break_id": "BREAK-ANOM-000001",
            "machine_id": planned_break_event["machine_id"],
            "start_time": break_start.isoformat(
                timespec="seconds"
            ),
            "end_time": break_end.isoformat(
                timespec="seconds"
            ),
        })

        event_end = break_end + timedelta(minutes=2)

        planned_break_event["end_time"] = event_end.isoformat(
            timespec="seconds"
        )
        planned_break_event["duration_min"] = int(
            (event_end - event_start).total_seconds() / 60
        )
        planned_break_event["is_planned"] = True

        event_anomaly_labels.append({
            "record_type": "machine_events",
            "record_id": planned_break_event["event_id"],
            "anomaly_type": "downtime_overlaps_planned_break",
            "expected_detection": True,
            "description": (
                "Downtime event overlaps a defined planned-break interval."
            ),
        })

    # Calculate OEE metrics.
    metrics = []

    for index, order in enumerate(order_lookup):
        planned_seconds = (
            8 * 3600
            - int(order.get("planned_break_min", 30)) * 60
        )

        operating_seconds = max(
            0,
            planned_seconds - downtime_seconds[order["order_id"]],
        )

        total = count_totals[order["order_id"]]
        good = count_goods[order["order_id"]]
        ideal = float(order["ideal_cycle_time_sec"])

        availability = (
            operating_seconds / planned_seconds
            if planned_seconds else 0
        )

        performance = (
            (ideal * total) / operating_seconds
            if operating_seconds > 0 else 0
        )
        quality = good / total if total else 0
        oee = availability * performance * quality

        
        metrics.append({
            "metric_id": f"OEE-{index + 1:07d}",
            "order_id": order["order_id"],
            "shift_id": next(
                o["shift_id"]
                for o in orders
                if o["order_id"] == order["order_id"]
            ),
            "machine_id": order["machine_id"],
            "planned_production_sec": planned_seconds,
            "operating_sec": operating_seconds,
            "ideal_cycle_time_sec": ideal,
            "total_count": total,
            "good_count": good,
            "availability": round(availability, 6),
            "performance": round(performance, 6),
            "quality": round(quality, 6),
            "oee": round(oee, 6),
            "oee_percent": round(oee * 100, 2),
        })
    
    # Aggregate OEE metrics by machine and shift.
    shift_groups = {}

    for metric in metrics:
        key = (metric["shift_id"], metric["machine_id"])

        if key not in shift_groups:
            shift_groups[key] = []

        shift_groups[key].append(metric)

    shift_oee_metrics = []

    for index, ((shift_id, machine_id), rows) in enumerate(
        sorted(shift_groups.items()),
        start=1,
    ):
        planned_seconds = sum(
            row["planned_production_sec"] for row in rows
        )
        operating_seconds = sum(
            row["operating_sec"] for row in rows
        )
        total = sum(row["total_count"] for row in rows)
        good = sum(row["good_count"] for row in rows)

        ideal_total_seconds = sum(
            row["ideal_cycle_time_sec"] * row["total_count"]
            for row in rows
        )

        availability = (
            operating_seconds / planned_seconds
            if planned_seconds > 0 else 0
        )
        performance = (
            ideal_total_seconds / operating_seconds
            if operating_seconds > 0 else 0
        )
        quality = good / total if total > 0 else 0
        oee = availability * performance * quality

        shift_oee_metrics.append({
            "shift_metric_id": f"SOEE-{index:07d}",
            "shift_id": shift_id,
            "machine_id": machine_id,
            "planned_production_sec": planned_seconds,
            "operating_sec": operating_seconds,
            "total_count": total,
            "good_count": good,
            "availability": round(availability, 6),
            "performance": round(performance, 6),
            "quality": round(quality, 6),
            "oee": round(oee, 6),
            "oee_percent": round(oee * 100, 2),
        })




    # Create three quality inspections per order.
    inspections = []
    inspection_number = 0

    for order in order_lookup:
        total = count_totals[order["order_id"]]

        for sample_no in range(3):
            inspection_number += 1
            failed = rng.random() < 0.03
            sample_size = rng.randint(1, max(1, min(100, total)))

            inspections.append({
                "inspection_id": (
                    f"QC-{order['start'].year}-{inspection_number:06d}"
                ),
                "order_id": order["order_id"],
                "product_id": order["product_id"],
                "inspection_time": (
                    order["start"] + timedelta(hours=1 + sample_no * 2)
                ).isoformat(timespec="seconds"),
                "sample_size": sample_size,
                "defect_count": int(failed),
                "inspection_result": "fail" if failed else "pass",
                "defect_code": (
                    rng.choice(["DIMENSION", "SURFACE", "ASSEMBLY"])
                    if failed else None
                ),
            })

    # Add deliberately labelled anomaly records for validator testing.
    labels = event_anomaly_labels.copy()
    # Label the wrong ideal cycle time anomaly.
    labels.append({
        "record_type": "machines",
        "record_id": wrong_cycle_machine_id,
        "anomaly_type": "wrong_ideal_cycle_time",
        "expected_detection": True,
        "description": (
            "Machine ideal cycle time is deliberately inflated "
            "to ten times its original value."
        ),
    })
    if count_decrease_anomaly_label is not None:
        labels.append(count_decrease_anomaly_label)

    if normal_count_target >= 0 and target_counts != 0:
        source = counts[0] if counts else {
            "order_id": order_lookup[0]["order_id"],
            "machine_id": order_lookup[0]["machine_id"],
            "timestamp": order_lookup[0]["start"].isoformat(
                timespec="seconds"
            ),
        }

        bad = {
            "count_id": f"CNT-ANOM-{base_count_target:07d}",
            "order_id": source["order_id"],
            "machine_id": source["machine_id"],
            "timestamp": source["timestamp"],
            "total_count": -5,
            "counter_value": None,
            "correction_event_id": None,
            "good_count": 10,
            "scrap_count": 0,
            "rework_count": 0,
        }

        counts.append(bad)

        labels.append({
            "record_type": "production_counts",
            "record_id": bad["count_id"],
            "anomaly_type": (
                "invalid_negative_total_and_good_exceeds_total"
            ),
            "expected_detection": True,
            "description": (
                "Deliberate invalid count row for validator testing"
            ),
        })
    # Add a separate anomaly where scrap exceeds total production.
    if counts:
        source = counts[0]

        bad_scrap = {
            "count_id": f"CNT-SCRAP-ANOM-{base_count_target:07d}",
            "order_id": source["order_id"],
            "machine_id": source["machine_id"],
            "timestamp": source["timestamp"],
            "total_count": 100,
            "counter_value": None,
            "correction_event_id": None,
            "good_count": 70,
            "scrap_count": 120,
            "rework_count": 0,
        }

        counts.append(bad_scrap)

        labels.append({
            "record_type": "production_counts",
            "record_id": bad_scrap["count_id"],
            "anomaly_type": "scrap_exceeds_total",
            "expected_detection": True,
            "description": (
                "Scrap count exceeds total production count."
            ),
        })

    return {
        "plants": plants,
        "lines": lines,
        "machines": machines,
        "shifts": shifts,
        "products": products,
        "production_orders": pd.DataFrame(orders),
        "machine_events": pd.DataFrame(events),
        "planned_breaks": pd.DataFrame(planned_breaks),
        "production_counts": pd.DataFrame(counts),
        "quality_inspections": pd.DataFrame(inspections),
        "oee_metrics": pd.DataFrame(metrics),
        "shift_oee_metrics": pd.DataFrame(shift_oee_metrics),
        "anomaly_labels": pd.DataFrame(
            labels,
            columns=[
                "record_type",
                "record_id",
                "anomaly_type",
                "expected_detection",
                "description",
            ],
        ),
    }
