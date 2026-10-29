# Architecture and execution flow

1. `main.py` reads command-line options such as seed, machine count, number of days, and output folder.
2. `src/oee_generator.py` builds reference data and synthetic operational records.
3. `src/validation.py` checks key uniqueness, production counts, event durations, and overlapping events.
4. `src/exporter.py` writes CSV, JSON, SQLite, SQL schema, manifest, and validation report.
5. `tests/test_generator.py` checks repeatability, expected tables, and detection of a deliberately invalid count row.

## OEE formulas
- Availability = operating time / planned production time.
- Performance = ideal cycle time × total count / operating time.
- Quality = good count / total count.
- OEE = availability × performance × quality, subject to the implementation's documented performance cap.

Review these definitions against the exact challenge statement before submission.
