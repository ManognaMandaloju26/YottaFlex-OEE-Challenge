# YottaFlex OEE — Manufacturing Synthetic Data Generator

## 1. Project Overview

The **YottaFlex OEE Synthetic Data Generator** is a Python-based project that creates interconnected synthetic manufacturing data for analyzing Overall Equipment Effectiveness (OEE).

It generates master data, production orders, machine events, planned breaks, production counts, quality inspections, OEE metrics, and labelled data-quality anomalies. The project supports validation, traceability, repeatable generation, and export to CSV, JSON, and SQLite.

All generated records are synthetic. They do not represent actual factory operations.

## 2. Objectives

- Simulate plants, production lines, machines, shifts, products, and production orders.
- Generate machine-state events, production counts, and quality inspection records.
- Calculate availability, performance, quality, and OEE metrics.
- Preserve relationships using consistent identifiers and database foreign keys.
- Introduce labelled anomaly scenarios for validation testing.
- Export datasets and supporting artifacts in CSV, JSON, and SQLite formats.
- Support repeatable generation through a configurable random seed.
- Report validation findings and distinguish expected issues from unexpected issues.

## 3. Key Features

### Synthetic data generation
Creates related manufacturing master, transaction, event, and metric datasets.

### OEE metrics
Calculates availability, performance, quality, and overall equipment effectiveness from generated production-related data.

### Validation and anomaly labels
Checks generated records and exports anomaly labels and separate ground-truth files for evaluation.

### Multiple export formats
Writes CSV and JSON datasets, a SQLite database, a SQL schema, a source/configuration manifest, and a validation report.

### Reproducibility and tests
Supports a configurable seed and includes automated tests for implemented generator and validation behavior.

## 4. Technology Stack

- Python 3.10+
- pandas
- PyYAML
- SQLite
- pytest

## 5. Project Structure

```text
YottaFlex_OEE_Challenge/
├── config.yaml
├── main.py
├── requirements.txt
├── README.md
├── src/
│   ├── oee_generator.py
│   ├── validation.py
│   ├── exporter.py
│   └── data_dictionary.py
├── tests/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   ├── DECISIONS_AND_ASSUMPTIONS.md
│   ├── IMPLEMENTATION_NOTES.md
│   └── TEST_EVIDENCE.md
└── output/                 # Generated output; created by a run
```

The exact contents of the output directory depend on the output path supplied to the generator.

## 6. Prerequisites

- Python 3.10 or a compatible newer version
- pip
- Windows PowerShell, VS Code terminal, or another terminal

## 7. Installation

Run these commands from the project root.

### Create a virtual environment

```powershell
python -m venv .venv
```

### Activate it (Windows PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
```

Skip this step if the virtual environment is already active.

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 8. Configuration and baseline scale

The generator reads its settings from `config.yaml`. The baseline configuration used in the recorded run was:

| Setting | Value |
|---|---:|
| Random seed | `20261022` |
| Plants | 1 |
| Production lines | 5 |
| Machines | 30 |
| Products | 20 |
| Simulation period | 90 days |
| Target machine events | 100,000 |
| Target production-count records | 500,000 |

Actual output counts are determined by the implementation and configuration. Adjust settings only where supported by the generator.

## 9. Generate the dataset

Run the configured baseline:

```powershell
python main.py
```

Or specify an output directory and seed:

```powershell
python main.py --output output_test --seed 20261022
```

The selected output directory contains the generated datasets and supporting files.

## 10. Generated datasets and artifacts

The generated tables include:

| Dataset/table | Purpose |
|---|---|
| `plants` | Manufacturing plant information |
| `lines` | Production lines linked to plants |
| `machines` | Machine details and ideal cycle-time configuration |
| `shifts` | Shift schedules |
| `products` | Product catalogue |
| `production_orders` | Orders assigned to machines, products, and shifts |
| `machine_events` | Machine-state and downtime event history |
| `planned_breaks` | Planned-break intervals |
| `production_counts` | Production quantities, counter values, and correction references |
| `quality_inspections` | Inspection results and defect counts |
| `oee_metrics` | Order-level OEE measurements |
| `shift_oee_metrics` | Machine-and-shift OEE measurements |
| `anomaly_labels` | Labels for deliberately introduced anomalies |

The exporter also produces CSV and JSON files, `ground_truth.csv`, `ground_truth.json`, `oee_seed.db`, `schema.sql`, `manifest.json`, and `validation_report.json`.

**Ground truth is exported separately** so it can be used as an evaluation reference rather than treated as an ordinary input feature.

## 11. OEE calculation

The project documents these standard formulas:

- **Availability** = Operating Time / Planned Production Time
- **Performance** = (Ideal Cycle Time × Total Count) / Operating Time
- **Quality** = Good Count / Total Count
- **OEE** = Availability × Performance × Quality
- **OEE percentage** = OEE × 100

Time values must use consistent units. The treatment of planned breaks, downtime overlaps, count corrections, invalid cycle times, and zero denominators should be interpreted according to the implemented generator and validation logic. The formulas and generated aggregates should be independently checked against source records before treating them as fully verified.

## 12. Validation and anomaly scenarios

The challenge scenarios represented in the project include:

- Overlapping machine-state events
- Production-count decreases without a correction record
- Scrap quantities exceeding total production
- Incorrect ideal cycle time
- Downtime overlapping a planned break

The generator labels intentional anomalies and reports validation findings. The precise findings depend on the generated dataset, configuration, and implemented validation rules. Expected anomalies should not be confused with unexpected validation failures.

## 13. Automated tests

Run the test suite from the project root:

```powershell
python -m pytest -q
```

The latest recorded test run completed with:

```text
5 passed
```

This is evidence that the tests present in the repository passed for that run; it does not independently prove that every business rule or edge case has been tested.

## 14. Recorded generation and validation results

The recorded run used seed `20261022` and produced:

| Dataset | Records |
|---|---:|
| Plants | 1 |
| Production lines | 5 |
| Machines | 30 |
| Shifts | 270 |
| Products | 20 |
| Production orders | 2,700 |
| Machine events | 100,000 |
| Planned breaks | 1 |
| Production counts | 500,000 |
| Quality inspections | 8,100 |
| OEE metrics | 2,700 |
| Shift OEE metrics | 2,700 |
| Anomaly labels | 6 |

The recorded validation report showed:

- Validation passed: `True`
- Total reported issues: `10`
- Unexpected issues: `0`

These are results from the tested configuration and run, not guarantees for every configuration. Review `manifest.json` and `validation_report.json` in the output directory for run-specific evidence.

## 15. SQLite schema and integrity

The exporter creates a SQLite database (`oee_seed.db`) and writes the corresponding SQL table definitions to `schema.sql`. The generated schema includes primary-key definitions for the tables with configured primary keys and foreign-key declarations for the relationships defined in the exporter.

The `anomaly_labels` table currently has no declared primary key. Foreign-key enforcement in SQLite is connection-specific; applications opening the database should enable it on their connection when enforcement is required:

```sql
PRAGMA foreign_keys = ON;
```

A recorded database check returned no rows from `PRAGMA foreign_key_check` and reported 13 tables. This confirms that the checked database had no reported foreign-key violations at that time.

## 16. Reproducibility

The baseline seed is `20261022`.

Two generation runs were performed with the same seed and configuration. The CSV and JSON files that were compared matched byte-for-byte across the two output directories. This demonstrates reproducibility for the compared files under the tested configuration and environment; it does not establish that every output file or every possible configuration has been verified.

To repeat a run, use the same code, configuration, seed, and compatible software environment:

```powershell
python main.py --output output_repeat --seed 20261022
```

## 17. Documentation

The `docs/` directory should contain the project documentation files, where present:

- `ARCHITECTURE.md` — system structure and data flow
- `DATA_DICTIONARY.md` — field definitions, types, constraints, and rules
- `DECISIONS_AND_ASSUMPTIONS.md` — assumptions and business decisions
- `IMPLEMENTATION_NOTES.md` — implementation details
- `TEST_EVIDENCE.md` — recorded tests and validation evidence

The Python data dictionary and generated SQL schema should be treated as the implementation references when documenting actual fields, keys, and relationships. In particular, `planned_breaks` is a separate table, downtime reason codes are currently represented by the `machine_events.reason` field rather than a separate `DowntimeReason` table, and `oee_metrics` plus `shift_oee_metrics` provide the two OEE aggregation levels.

## 18. Limitations and future improvements

This project generates synthetic manufacturing data, not real factory measurements. Further improvements could include:

- More independent tests for OEE formulas and source-to-aggregate reconciliation.
- Stronger checks for each injected anomaly.
- More explicit handling and documentation of planned and unplanned downtime.
- Additional configuration and scale tests.
- A declared, stable key for anomaly labels if a suitable uniqueness rule is established.
- More detailed database constraints and lifecycle validation.

## 19. Summary

The project provides a foundation for generating related synthetic manufacturing datasets, calculating OEE metrics, validating data quality, and exporting repeatable results. The recorded tests, validation report, SQLite integrity check, and reproducibility comparison provide evidence for the tested run. Independent verification of all business rules and OEE calculations remains important.

---

**Project:** YottaFlex OEE — Manufacturing Synthetic Data Generator  
**Language:** Python  
**Purpose:** Synthetic manufacturing data generation, OEE analysis, and data-quality validation  
**Data type:** Synthetic data for development and testing
