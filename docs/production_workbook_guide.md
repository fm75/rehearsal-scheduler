# Production Workbook Guide

**Workbook:** Production  
**Purpose:** Manage show order, program information, and cast lists for the final performance

---

## Overview

The Production workbook contains sheets for organizing the dance performance order, generating the printed program, and creating cast lists.

**Primary Users:**
- **Directors** - Finalize show order
- **Program Editor** - Create printed program
- **Stage Manager** - Reference performance order
- **Cast** - Know their dances and order

---

## Sheets

### 1. show_order

**Purpose:** Define the performance order of dances

**Columns:**
- `line_no` - BASIC-style line numbers (20, 40, 60, 80...)
- `dance_id` - Dance identifier (from Look Up Tables)
- `dance_name` - Dance title (VLOOKUP from Look Up Tables)
- `choreographer` - Choreographer name (VLOOKUP from Look Up Tables)

**How to Use:**

#### Initial Setup
1. Enter dance_ids in desired performance order
2. Use line numbers: 20, 40, 60, 80, 100, etc.
3. dance_name and choreographer auto-populate via VLOOKUP

#### Reordering Dances
**Don't insert/delete rows!** Instead, use line numbers:

```
Original Order:
20 - d_01 - Opening Number
40 - d_05 - Jazz Piece  
60 - d_12 - Contemporary

Want to move Jazz Piece to open?
Change line numbers:
25 - d_01 - Opening Number
15 - d_05 - Jazz Piece    (changed from 40 to 15)
60 - d_12 - Contemporary

Then: Select all → Data → Sort Range → Advanced range sorting options → check data has header row → Sort by line_no → A to Z
```

**Why BASIC-style numbering?**
- Easy reordering without row operations
- Space between numbers allows insertions
- No risk of breaking formulas
- Clear performance order

**Common Operations:**

| Task | Method |
|------|--------|
| Move dance up | Lower its line_no |
| Move dance down | Raise its line_no |
| Insert between | Use intermediate number (e.g., 35 between 30 and 40) |
| Swap two dances | Swap their line_no values, then sort |
| Remove from show | Delete the entire row |

#### Tips
- Keep 20-number gaps for flexibility
- Resort frequently to keep visual order clear
- line_no doesn't have to be sequential - only relative order matters
- Can renumber everything by 10s or 20s anytime

---

### 2. production_program

**Purpose:** Generate content for the printed program

**Columns:**
- `line_no` - Performance order (copied from show_order)
- `dance_id` - Dance identifier
- `dance_name` - Dance title (VLOOKUP)
- `choreographer` - Choreographer name (VLOOKUP)
- `dancers` - Comma-separated list of dancer names (generated)

**How to Use:**

#### Initial Setup
1. **Copy order from show_order:**
   - In show_order, select columns A-D (line_no through choreographer)
   - Copy
   - In production_program, paste into columns A-D
   - This establishes the show order

2. **Generate dancer lists:**
   ```bash
   python populate_production_dancers.py
   ```
   
   This script:
   - Reads dance_cast from Look Up Tables
   - Generates alphabetically sorted dancer lists
   - Populates the `dancers` column
   - Example: "Alice Smith, Bob Jones, Carol White"

#### Updating After Cast Changes
If dancers are added/removed from dances:

```bash
# Preview changes first
python populate_production_dancers.py --dry-run

# Apply updates
python populate_production_dancers.py
```

The script overwrites existing dancer lists with current cast from dance_cast.

#### Creating the Printed Program

**Option 1: Direct from Sheet**
1. Select columns B-E (dance_name through dancers)
2. Format as needed (fonts, spacing)
3. File → Print or File → Download → PDF

**Option 2: Copy to Document**
1. Copy data to Google Docs
2. Format with program template
3. Add show title, date, acknowledgments
4. Print or generate PDF

**Typical Program Format:**
```
DANCE TITLE
Choreographer: Name
Dancers: Alice Smith, Bob Jones, Carol White

NEXT DANCE TITLE
Choreographer: Name
Dancers: ...
```

---

### 3. cast_list

**Purpose:** Share cast assignments with dancers and program editor

**Columns:**
- `dance_name` - Dance title
- `choreographer` - Choreographer name
- `dancers` - Comma-separated list of dancer names

**How to Create:**

#### From production_program:
1. In production_program, select columns B-D (dance_name, choreographer, dancers)
2. Copy
3. In cast_list sheet, click cell A1
4. Edit → Paste Special → **Values only**
5. This removes formulas and dance_id, keeping just the display data

**Why values-only?**
- Removes VLOOKUP formulas (faster loading)
- Hides technical dance_id column
- Clean for sharing with cast
- Safe for program editor to copy from

#### Sharing with Cast

**Option 1: PDF**
1. In cast_list sheet, select all data
2. File → Download → PDF
3. Email or post to shared folder
4. Dancers see: which dances they're in, who else is in them

**Option 2: View-Only Link**
1. Share Production workbook with view-only access
2. Cast can reference anytime
3. Updates automatically when you regenerate

**What Dancers See:**
```
Opening Number          | Choreographer: Smith | Dancers: Alice, Bob, Carol, Dan
Jazz Piece             | Choreographer: Jones | Dancers: Alice, Eva, Frank
Contemporary Duet      | Choreographer: Smith | Dancers: Bob, Carol
```

---

## Workflows

### Complete Workflow: From Scheduling to Program

```mermaid
Look Up Tables (dances, dancers, dance_cast)
    ↓
show_order (directors set performance order)
    ↓
production_program (copy order, generate dancers)
    ↓
cast_list (values-only for sharing)
    ↓
Printed Program & PDF for Cast
```

### Weekly Production Meeting Workflow

**Week 8-6 Before Show:**
1. Directors work in show_order
2. Experiment with different orders
3. Consider pacing, transitions, themes

**Week 5-4 Before Show:**
1. Finalize show_order
2. Copy to production_program
3. Run `populate_production_dancers.py`
4. Review for accuracy

**Week 3-2 Before Show:**
1. Create cast_list (values-only)
2. Generate PDF
3. Share with all dancers
4. Program editor starts layout

**Week 1 Before Show:**
1. Make any final cast changes
2. Regenerate dancers column
3. Update cast_list
4. Final PDF to cast
5. Final program to printer

**Show Week:**
1. Cast list on stage manager's table
2. Program available for reference
3. No further changes!

---

## Common Tasks

### Task: Reorder Entire Show

```bash
1. In show_order, adjust line_no values
2. Select all data → Data → Sort by line_no
3. Copy updated order to production_program
4. Regenerate dancers: python populate_production_dancers.py
5. Update cast_list (copy values-only)
```

### Task: Add Dance to Show

```bash
1. In show_order, add new row with dance_id
2. Set line_no to position in show (e.g., 45 to go after 40)
3. Sort by line_no
4. Copy to production_program
5. Regenerate dancers
6. Update cast_list
```

### Task: Remove Dance from Show

```bash
1. In show_order, delete the dance's row
2. Copy remaining dances to production_program
3. Regenerate dancers (or manually delete that row)
4. Update cast_list
```

### Task: Update Cast for One Dance

```bash
1. In Look Up Tables → dance_cast, update the grid
2. Regenerate: python populate_production_dancers.py
   (This updates all dances, including the one you changed)
3. Copy updated row to cast_list
```

### Task: Share Cast List Changes

```bash
1. Make cast changes in Look Up Tables → dance_cast
2. Regenerate production_program dancers
3. Update cast_list (copy values-only)
4. Generate new PDF
5. Email: "Updated cast list attached - [Dance X] cast has changed"
```

---

## Technical Details

### VLOOKUPs in show_order and production_program

Both sheets use VLOOKUP formulas to pull data from Look Up Tables workbook:

```
=VLOOKUP(dance_id, IMPORTRANGE("SPREADSHEET_ID", "dances!A:C"), 2, FALSE)
```

**First time setup:**
- VLOOKUP shows #REF! error
- Click cell → "Allow access" button
- One-time permission per workbook pair
- All formulas then work automatically

**If formulas break:**
- Don't paste data over formula cells
- If broken, delete content and let VLOOKUP regenerate
- Or use build_workbook.py --force to rebuild sheet

### Generated Dancers Column

The `dancers` column in production_program is **generated by script**, not formulas:

**Why not use formulas?**
- dance_cast is a matrix (dancers × dances)
- No simple VLOOKUP pattern to extract dancer list
- Would require complex QUERY or FILTER arrays
- Python script is clearer and more maintainable

**How generation works:**
1. Read dance_cast matrix
2. For each dance_id, find all rows where grid cell = 1
3. Collect dancer full names
4. Sort alphabetically by first name
5. Join with ", " separator
6. Write to dancers column

**When to regenerate:**
- After any cast change in Look Up Tables
- After adding/removing dancers
- Before sharing cast_list
- Before finalizing printed program

---

## File Locations

```
rehearsal-scheduler/
├── config/
│   └── workbook_export.yaml          # Workbook IDs for scripts
│
├── src/rehearsal_scheduler/scripts/
│   └── populate_production_dancers.py # Generate dancers column
│
└── docs/
    └── production_workbook_guide.md   # This document
```

---

## Script Reference

### populate_production_dancers.py

**Purpose:** Generate alphabetically sorted dancer lists for production_program

**Usage:**
```bash
# Simple - uses config/workbook_export.yaml
python populate_production_dancers.py

# Dry run (preview only)
python populate_production_dancers.py --dry-run

# Override workbook IDs
python populate_production_dancers.py \
  --lookup-workbook-id SPREADSHEET_ID \
  --production-workbook-id SPREADSHEET_ID
```

**What it does:**
1. Reads dance_cast matrix from Look Up Tables
2. Reads production_program from Production workbook
3. For each dance, generates sorted dancer list
4. Updates dancers column in production_program

**Output Example:**
```
=== Populate Production Dancers ===

Loading workbook IDs from config/workbook_export.yaml...
  ✓ Loaded from config

Reading dance_cast matrix from Look Up Tables...
  Found 40 dances
  Loaded 250 total dancer assignments

Reading production_program from Production workbook...
  Found 25 dances in production program

Populating dancers column...
  ✓ d_01: 8 dancers
  ✓ d_05: 12 dancers
  ✓ d_12: 6 dancers
  ...

Writing updates to production_program...

✓ Updated 25 dances in production_program
```

---

## Troubleshooting

### IMPORTRANGE Errors

**Problem:** #REF! error in formulas  
**Solution:** Click cell → "Allow access" → Grant permission

**Problem:** "IMPORTRANGE cannot be found"  
**Solution:** Check spreadsheet ID in formula matches actual workbook

### Dancer List Issues

**Problem:** Dancers missing from list  
**Solution:** 
1. Check dance_cast matrix has "1" in correct cells
2. Verify dancer names are in column B of dance_cast
3. Regenerate: `python populate_production_dancers.py`

**Problem:** Dancers in wrong order  
**Solution:** Script sorts by first name. If you need different order, would need to modify script or manually edit.

**Problem:** Old dancers still listed  
**Solution:** Regenerate after updating dance_cast - script overwrites old data

### cast_list Not Updating

**Problem:** Changes in production_program don't show in cast_list  
**Solution:** cast_list is values-only copy, not linked. Must manually copy again:
1. Select production_program columns C-E
2. Copy
3. In cast_list, Paste Special → Values only

---

## Best Practices

### 1. Work in Order: show_order → production_program → cast_list

Always work upstream to downstream. Changes in show_order should be copied to production_program, then to cast_list.

### 2. Regenerate After Cast Changes

Anytime you update dance_cast in Look Up Tables, regenerate production_program:
```bash
python populate_production_dancers.py
```

### 3. Use Dry Run for Safety

Before regenerating, preview changes:
```bash
python populate_production_dancers.py --dry-run
```

### 4. Keep cast_list Updated

Update cast_list weekly, not daily. Too-frequent updates confuse dancers. Batch changes and send weekly "cast update" emails.

### 5. Version Control for Programs

When finalizing printed program, save dated copies:
- "Show Program 2026-03-01.pdf"
- "Show Program FINAL 2026-03-08.pdf"

### 6. Protect Finalized Data

Once show order is locked (usually 2 weeks before show):
- Consider protecting show_order and production_program sheets
- Prevents accidental changes
- Directors can still unprotect if needed

---

## FAQ

**Q: Can I reorder by dragging rows in show_order?**  
A: No - use line_no and sort. Dragging breaks formulas.

**Q: Why not just number 1, 2, 3 instead of 20, 40, 60?**  
A: Gaps allow easy insertion. To add between 40 and 60, just use 50.

**Q: Do I need to run populate_production_dancers.py after reordering?**  
A: No - only after cast changes. Reordering doesn't affect who's in each dance.

**Q: Can I edit the dancers list manually?**  
A: Yes, but it will be overwritten next time you run the script. Better to update dance_cast and regenerate.

**Q: What if a dancer needs to be listed by stage name?**  
A: Update their full_name in the dancers sheet of Look Up Tables, then regenerate.

**Q: Can I add intermission to show_order?**  
A: Yes! Use a placeholder dance_id like "INTERMISSION" or leave dance_id blank. Manually type "INTERMISSION" in other columns.

**Q: How do I handle guest performers?**  
A: Add them to dancers sheet, add to dance_cast, regenerate. Or manually add to cast_list if one-time only.

---

## Related Documentation

- **Look Up Tables Guide** - Managing dances, dancers, and casting
- **Workbook Builder Guide** - Creating/rebuilding sheets with YAML specs
- **CSV Export Tool** - Exporting data for testing/analysis

---

**Last Updated:** January 30, 2026  
**Maintained By:** Scheduling System Development Team