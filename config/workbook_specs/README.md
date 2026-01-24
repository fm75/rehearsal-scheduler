# Google Sheets Workbook Builder

Builds Google Sheets workbooks from YAML specifications with automatic formatting, formulas, and protections.

## Setup

1. **Install dependencies:**
   ```bash
   pip install pyyaml google-api-python-client google-auth
   ```

2. **Set credentials:**
   ```bash
   export GOOGLE_BUILDER_CREDENTIALS=/path/to/service-account-credentials.json
   ```

3. **Create blank workbook in Google Drive**
   - Right-click in Drive → New → Google Sheets
   - Share with service account email as Editor
   - Copy the spreadsheet ID from the URL

## Usage

### Build entire workbook

```bash
export $(cat .env | xargs)
python build_workbook.py --workbook lookup_tables --spreadsheet-id YOUR_SHEET_ID
```

### Build single sheet

```bash
export $(cat .env | xargs)
python build_workbook.py \
  --spec config/workbook_specs/lookup_tables/dances.yaml \
  --spreadsheet-id YOUR_SHEET_ID \
  --is-first  # Only for first sheet in new workbook
```

### Interactive mode

```bash
python build_workbook.py
# Follow prompts
```

## Directory Structure

```
config/workbook_specs/
├── lookup_tables/
│   ├── dances.yaml
│   ├── dancers.yaml
│   ├── rds.yaml
│   └── dance_cast.yaml
├── scheduling/
│   ├── venue_schedule.yaml
│   ├── dancer_constraints.yaml
│   └── rd_constraints.yaml
└── production/
    └── show_order.yaml

test/integration/fixtures/
├── lookup_tables/
│   ├── dances.csv
│   ├── dancers.csv
│   └── ...
└── ...
```

## YAML Spec Format

```yaml
name: sheet_name

columns:
  - column1
  - column2
  - column3

protected_columns:  # Optional - columns that are read-only
  - column1

formulas:  # Optional - auto-calculated columns
  column2: '=A2*2'
  column3: '=SUM(A2:B2)'

auto_id_config:  # Optional - auto-generate IDs
  column: column1
  prefix: 'id_'
  count: 50
```

## Features

- ✅ **Auto-IDs**: Generates sequential IDs (d_01, d_02, ...)
- ✅ **Formulas**: ArrayFormulas that apply to all rows
- ✅ **Protection**: Lock headers and calculated columns
- ✅ **Formatting**: Bold headers, frozen rows
- ✅ **Idempotent**: Safe to re-run (updates existing sheets)

## Workflow

### For Testing (with CSV files)

1. Build workbooks from YAML specs
2. Export sheets to CSV
3. Commit CSV files to `test/integration/fixtures/`
4. Use CSV files for integration tests

### For Production

1. Create blank workbook in Drive
2. Share with service account
3. Run builder with workbook name
4. Directors edit the sheets
5. System reads from live Google Sheets

## Troubleshooting

**Permission denied (403)**
- Make sure workbook is shared with service account as Editor
- Check that GOOGLE_BUILDER_CREDENTIALS is set

**Sheet not found**
- Use `--is-first` flag when building the first sheet in a new workbook
- This renames the default "Sheet1"

**Formula not working**
- Formulas must reference row 2 (first data row)
- ArrayFormula wrapper is added automatically
