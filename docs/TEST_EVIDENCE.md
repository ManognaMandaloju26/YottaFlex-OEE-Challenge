# Test and verification evidence

Fill this file with results from your own final run before submission.

## Environment
- OS:
- Python version:
- Dependency installation command:
- Date/time tested:

## Commands
```bash
python main.py --output output --seed 42 --machines 5 --days 3
pytest -q
```

## Results to record
- Did the generator finish successfully?
- Which files were created?
- How many rows were generated in each table?
- Did the validation report identify the deliberately injected anomaly?
- Did repeated runs with the same seed produce identical data?
- Did the SQLite database open and contain the expected tables?

## Known limitations
Document any failures or incomplete requirements honestly.
