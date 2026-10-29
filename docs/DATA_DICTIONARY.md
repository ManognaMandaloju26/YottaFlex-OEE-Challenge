# YottaFlex OEE Challenge — Data Dictionary

## 1. Purpose

This document defines the manufacturing entities, fields, data types, identifiers, relationships, constraints, and business rules used by the synthetic OEE data generator.

## 2. Entity Overview

| Entity | Description | Primary Key |
|---|---|---|
| plants | Manufacturing plant information | plant_id |
| lines | Production lines linked to plants | line_id |
| machines | Equipment and ideal cycle time | machine_id |
| shifts | Production shift schedules | shift_id |
| products | Product catalogue | product_id |
| production_orders | Planned manufacturing activities | order_id |
| machine_events | Machine operating and downtime intervals | event_id |
| production_counts | Total, good, scrap, and rework quantities | count_id |
| quality_inspections | Quality inspection records | inspection_id |
| oee_metrics | Order-level OEE measurements | metric_id |
| shift_oee_metrics | Machine-and-shift OEE measurements | shift_metric_id |
| anomaly_labels | Labels for intentionally introduced anomalies | Verify schema |

## 3. Field Definitions

### 3.1 Plants

| Field | Type | Constraints | Description |
|---|---|---|---|
| plant_id | String | Required, unique | Plant identifier |
| plant_name | String | Required | Plant name |
| timezone | String | Required | Plant timezone |
| location | String | Required | Plant location |

### 3.2 Lines

| Field | Type | Constraints | Description |
|---|---|---|---|
| line_id | String | Required, unique | Production line identifier |
| plant_id | String | Required, foreign key | References plants.plant_id |
| line_name | String | Required | Production line name |

### 3.3 Machines

| Field | Type | Constraints | Description |
|---|---|---|---|
| machine_id | String | Required, unique | Machine identifier |
| line_id | String | Required, foreign key | References lines.line_id |
| machine_name | String | Required | Machine name |
| machine_type | String | Defined enumeration | Machine category |
| ideal_cycle_time_sec | Float | Positive | Ideal seconds per unit |
| active | Boolean | Required | Whether the machine is active |

### 3.4 Shifts

| Field | Type | Constraints | Description |
|---|---|---|---|
| shift_id | String | Required, unique | Shift identifier |
| shift_name | String | Required | Shift name |
| start_time | Datetime | Before end_time | Shift start |
| end_time | Datetime | After start_time | Shift end |

Example identifier: `SHIFT-2026-01-01-A`.

### 3.5 Products

| Field | Type | Constraints | Description |
|---|---|---|---|
| product_id | String | Required, unique | Product identifier |
| product_name | String | Required | Product name |
| sku | String | Required, unique | Stock keeping unit |

### 3.6 Production Orders

| Field | Type | Constraints | Description |
|---|---|---|---|
| order_id | String | Required, unique | Production order identifier |
| machine_id | String | Required, foreign key | References machines.machine_id |
| product_id | String | Required, foreign key | References products.product_id |
| shift_id | String | Required, foreign key | References shifts.shift_id |
| planned_start | Datetime | Before planned_end | Planned production start |
| planned_end | Datetime | After planned_start | Planned production end |
| planned_break_min | Integer | Non-negative | Planned break duration |
| target_units | Integer | Non-negative | Target production quantity |
| status | String | Defined enumeration | Order lifecycle status |

Example identifier: `PO-2026-000001`.

### 3.7 Machine Events

| Field | Type | Constraints | Description |
|---|---|---|---|
| event_id | String | Required, unique | Machine event identifier |
| machine_id | String | Required, foreign key | References machines.machine_id |
| order_id | String | Required, foreign key | References production_orders.order_id |
| event_type | String | Defined enumeration | Machine state or event type |
| reason | String | Optional | Downtime reason code |
| start_time | Datetime | Before end_time | Event start timestamp |
| end_time | Datetime | After start_time | Event end timestamp |
| duration_min | Float | Non-negative | Event duration in minutes |
| is_planned | Boolean | Required | Whether the event is planned |

Example identifier: `EVT-<machine-id>-000001`.

### 3.8 Production Counts

| Field | Type | Constraints | Description |
|---|---|---|---|
| count_id | String | Required, unique | Count record identifier |
| order_id | String | Required, foreign key | References production_orders.order_id |
| machine_id | String | Required, foreign key | References machines.machine_id |
| timestamp | Datetime | Required | Count recording time |
| total_count | Integer | Non-negative for valid records | Total produced |
| good_count | Integer | No greater than total_count for valid records | Good units |
| scrap_count | Integer | Non-negative | Scrapped units |
| rework_count | Integer | Non-negative | Units requiring rework |

Example identifier: `CNT-<order-id>-000001`.

### 3.9 Quality Inspections

| Field | Type | Constraints | Description |
|---|---|---|---|
| inspection_id | String | Required, unique | Inspection identifier |
| order_id | String | Required, foreign key | References production_orders.order_id |
| product_id | String | Required, foreign key | References products.product_id |
| inspection_time | Datetime | Required | Inspection timestamp |
| sample_size | Integer | Positive for valid records | Number of inspected units |
| defect_count | Integer | Between zero and sample_size | Number of defects |
| inspection_result | String | Defined enumeration | Inspection outcome |
| defect_code | String | Optional | Defect classification |

Example identifier: `QC-2026-000001`.

### 3.10 Order-Level OEE Metrics

| Field | Type | Constraints | Description |
|---|---|---|---|
| metric_id | String | Required, unique | OEE metric identifier |
| order_id | String | Required, foreign key | References production_orders.order_id |
| machine_id | String | Required, foreign key | References machines.machine_id |
| planned_production_sec | Float | Non-negative | Planned production time |
| operating_sec | Float | Non-negative | Operating time |
| ideal_cycle_time_sec | Float | Positive | Ideal cycle time |
| total_count | Integer | Non-negative | Total production |
| good_count | Integer | Non-negative | Good production |
| availability | Float | Derived | Availability ratio |
| performance | Float | Derived | Performance ratio |
| quality | Float | Derived | Quality ratio |
| oee | Float | Derived | Overall equipment effectiveness |
| oee_percent | Float | Derived | OEE expressed as a percentage |

### 3.11 Shift-Level OEE Metrics

| Field | Type | Constraints | Description |
|---|---|---|---|
| shift_metric_id | String | Required, unique | Shift metric identifier |
| shift_id | String | Required, foreign key | References shifts.shift_id |
| machine_id | String | Required, foreign key | References machines.machine_id |
| planned_production_sec | Float | Non-negative | Planned production time |
| operating_sec | Float | Non-negative | Operating time |
| total_count | Integer | Non-negative | Total production |
| good_count | Integer | Non-negative | Good production |
| availability | Float | Derived | Availability ratio |
| performance | Float | Derived | Performance ratio |
| quality | Float | Derived | Quality ratio |
| oee | Float | Derived | Overall equipment effectiveness |
| oee_percent | Float | Derived | OEE percentage |

### 3.12 Anomaly Labels

| Field | Type | Constraints | Description |
|---|---|---|---|
| record_type | String | Required | Affected record type |
| record_id | String | Required | Affected record identifier |
| anomaly_type | String | Required | Anomaly classification |
| expected_detection | Boolean | Required | Whether validation should detect the anomaly |
| description | String | Required | Explanation of the anomaly |

Verify the actual primary key and uniqueness constraints against the database schema.

## 4. Relationships and Cardinality

| Parent | Child | Cardinality |
|---|---|---|
| Plant | Line | One-to-many (1:N) |
| Line | Machine | One-to-many (1:N) |
| Machine | Production Order | One-to-many (1:N) |
| Product | Production Order | One-to-many (1:N) |
| Shift | Production Order | One-to-many (1:N) |
| Machine | Machine Event | One-to-many (1:N) |
| Production Order | Machine Event | One-to-many (1:N) |
| Production Order | Production Count | One-to-many (1:N) |
| Machine | Production Count | One-to-many (1:N) |
| Production Order | Quality Inspection | One-to-many (1:N) |
| Product | Quality Inspection | One-to-many (1:N) |
| Shift | Shift OEE Metric | One-to-many (1:N) |
| Machine | Shift OEE Metric | One-to-many (1:N) |

These relationships reflect the current field definitions. Confirm them against the implemented schema and foreign-key constraints. Document one-to-one and many-to-many relationships only where the implementation supports them.

## 5. Downtime Reasons

The current implementation stores downtime reasons in the optional `machine_events.reason` field. A separate `DowntimeReason` table has not been confirmed.

The Python data dictionary defines these reason codes:

- `PLANNED_BREAK` — Scheduled break
- `MICRO_STOP` — Short unplanned stop
- `CHANGEOVER` — Product or setup change
- `BREAKDOWN` — Equipment failure
- `MAINTENANCE` — Maintenance activity
- `OTHER` — Other downtime reason

## 6. Lifecycle and Effective Dates

Production orders contain planned start and end times and a status field. Machine records contain an active flag, while machine events retain start and end timestamps.

The exact permitted status values and transitions must be documented from the implementation. Historical configuration changes and effective dates should be described only if the schema supports them.

## 7. OEE Business Rules

- Availability = Operating Time / Planned Production Time
- Performance = Ideal Cycle Time × Total Count / Operating Time
- Quality = Good Count / Total Count
- OEE = Availability × Performance × Quality
- OEE Percentage = OEE × 100

Document the implementation's handling of zero denominators, planned breaks, downtime overlap, scrap, rework, count corrections, and invalid cycle times.

## 8. Data Validation

Validation should check:

- Duplicate identifiers.
- Invalid foreign-key references.
- Invalid timestamps and durations.
- Negative or inconsistent production quantities.
- Invalid machine states and order statuses.
- Overlapping machine events.
- Downtime overlapping planned breaks.
- Invalid ideal cycle times.
- OEE metrics that do not reconcile with their source records.

Intentionally generated anomalies should be distinguished from unexpected validation failures.

## 9. Reproducibility and Limitations

The generator uses a configurable random seed to support repeatable dataset generation. Reproducibility claims should identify the files compared, the seed, configuration, and environment.

This project uses synthetic manufacturing data. Passing tests does not independently prove that every OEE formula or business rule has been fully verified.