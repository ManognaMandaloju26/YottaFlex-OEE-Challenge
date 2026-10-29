# Decisions, assumptions, and trade-offs

## Scope
This project generates synthetic manufacturing records and derived Overall Equipment Effectiveness (OEE) metrics for a small, locally runnable demonstration.

## Assumptions
- Data is synthetic and does not represent a real factory.
- One production order is generated per machine per production day.
- Production time is an eight-hour shift with a 30-minute planned break.
- OEE is calculated at production-order level.
- All timestamps are naive local timestamps for the generated factory calendar; timezone is documented separately.
- A deliberately invalid production-count record is added so the validator can demonstrate detection of known bad data.
- The generator is deterministic for the same seed and configuration in the same supported environment.

## Key decisions
- Python and pandas were chosen for approachable data generation and tabular exports.
- SQLite keeps the project locally runnable without a hosted database.
- CSV and JSON provide portable outputs; SQLite and SQL schema support relational inspection.
- A seeded pseudo-random generator supports reproducibility.
- Anomaly labels are stored separately from operational tables to make the intended anomalies auditable.

## Trade-offs and limitations
- The initial generator models only a subset of real manufacturing complexity.
- Shift scheduling is simplified and does not fully model overnight shift boundaries.
- Event generation is synthetic and should be strengthened to guarantee all machine event intervals are non-overlapping across all orders.
- OEE policy varies by manufacturer; planned stops, changeovers, and ideal cycle-time conventions should be confirmed against the challenge's full specification.
- This starter implementation does not yet implement every potential anomaly class or every requested reconciliation check. Check the full portal statement and close gaps before final submission.
- OEE performance is retained as a raw ratio; OEE calculation currently caps performance at 1.0. Explain and verify this policy before submission.

## Verification
Record the exact commands run, environment, test output, and generated row counts in `docs/TEST_EVIDENCE.md` after running the project locally. Do not claim a test passed unless you ran it.
