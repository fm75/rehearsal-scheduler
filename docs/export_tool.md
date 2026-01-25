# Google Sheets to CSV Export Tool

Export Google Sheets workbooks to organized CSV directory structure for testing and version control.

## Setup

1. **Update config with your spreadsheet IDs:**
   ```bash
   # Edit config/workbook_export.yaml
   # Replace placeholder IDs with actual spreadsheet IDs
   ```

2. **Set credentials:**
   ```bash
   export GOOGLE_BUILDER_CREDENTIALS=/path/to/credentials.json
   ```

## Usage

### Export all workbooks (recommended)

```bash
python export_workbooks.py all-workbooks \
  --config config/workbook_export.yaml \
  --output-dir data/csv
```

**Creates structure:**
```
data/csv/
├── lookup_tables/
│   ├── dances.csv
│   ├── dancers.csv
│   ├── rds.csv
│   └── dance_cast.csv
├── scheduling/
│   ├── venue_schedule.csv
│   ├── dancer_constraints.csv
│   └── rd_constraints.csv
└── production/
    ├── show_order.csv
    └── production_program.csv
```

### Export single workbook

```bash
python export_workbooks.py workbook \
  --spreadsheet-id YOUR_SPREADSHEET_ID \
  --output-dir data/csv/lookup_tables
```

## Output

```
============================================================
Exporting 3 workbooks to CSV
============================================================

📁 lookup_tables
  Workbook: Look Up Tables
  Sheets: 4
    ✓ dances.csv (41 rows)
    ✓ dancers.csv (51 rows)
    ✓ rds.csv (21 rows)
    ✓ dance_cast.csv (51 rows)

📁 scheduling
  Workbook: Scheduling
  Sheets: 3
    ✓ venue_schedule.csv (25 rows)
    ✓ dancer_constraints.csv (51 rows)
    ✓ rd_constraints.csv (21 rows)

📁 production
  Workbook: Production
  Sheets: 2
    ✓ show_order.csv (41 rows)
    ✓ production_program.csv (41 rows)

============================================================
✓ Exported 9 total sheets
  Location: data/csv
============================================================
```

## Workflow

### 1. Export from live Google Sheets
```bash
python export_workbooks.py all-workbooks \
  --config config/workbook_export.yaml \
  --output-dir data/csv
```

### 2. Use CSVs for integration testing
```python
# In your tests
import pandas as pd

dances = pd.read_csv('data/csv/lookup_tables/dances.csv')
dancers = pd.read_csv('data/csv/lookup_tables/dancers.csv')

# Run domain logic
analyzer = ConflictAnalyzer(...)
result = analyzer.analyze(...)
```

### 3. Generate test data (future)
```bash
# Create random realistic test data
python scripts/generate_test_data.py \
  --output-dir test/integration/fixtures/scenario_1/

# Export snapshots from production
python export_workbooks.py all-workbooks \
  --output-dir test/integration/fixtures/snapshot_2026_01_26/
```

### 4. Version control snapshots
```bash
git add data/csv/
git commit -m "Snapshot: Week 1 rehearsal data"
```

## Features

- ✅ **Batch export** - All workbooks in one command
- ✅ **Organized structure** - Subdirectories per workbook
- ✅ **CSV format** - Compatible with pandas, Excel, version control
- ✅ **Progress output** - See what's being exported
- ✅ **Error handling** - Continues on errors, reports issues

## Notes

- Empty sheets export as empty CSVs
- Formulas export as their calculated values
- Formatting is not preserved (CSV is data-only)
- Protected ranges are ignored (data is exported normally)

## Integration with Testing

**Directory structure:**
```
data/
├── csv/                          # Live exports from Google Sheets
│   ├── lookup_tables/
│   ├── scheduling/
│   └── production/
│
test/integration/fixtures/
├── scenario_1/                   # Test scenario 1
│   ├── lookup_tables/
│   ├── scheduling/
│   └── production/
│
├── scenario_2/                   # Test scenario 2
└── snapshot_2026_01_26/          # Production snapshot
```

**Usage in tests:**
```python
# test/integration/test_conflict_analyzer.py

def test_rd_conflicts_scenario_1():
    # Load from fixtures
    dancers = pd.read_csv('test/integration/fixtures/scenario_1/lookup_tables/dancers.csv')
    
    # Run domain logic
    analyzer = ConflictAnalyzer(...)
    result = analyzer.analyze(...)
    
    # Assert expectations
    assert result.has_conflicts == True
```
