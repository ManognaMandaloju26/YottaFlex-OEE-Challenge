# Implementation notes

`main.py` parses options, `generate_dataset()` creates the tables, `validate_dataset()` checks record quality, and `export_dataset()` writes CSV, JSON, SQLite, SQL schema, manifest, and validation report.

The deliberate invalid count row is kept in the production-count export and labeled separately in `anomaly_labels`; the validation report should therefore contain expected issues. OEE is calculated per order. This is a practical starter implementation, not a claim that every portal requirement is complete. Review the full problem statement and extend/test as needed.
