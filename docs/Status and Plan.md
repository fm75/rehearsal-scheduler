# Rehearsal Scheduler - Status & Planning Document

**Date:** January 22, 2026  
**Project Phase:** Pre-Production (2-3 weeks until live data)

---

## 🎯 Core Objectives

The system enables dance directors to:
1. **Validate constraints** - Check dancer/RD availability syntax
2. **Detect RD conflicts** - Find RD scheduling conflicts against venues
3. **Analyze dance availability** - See which dances can rehearse in which slots
4. **Generate schedules** - Auto-create or validate rehearsal schedules
5. **Report attendance** - Show expected attendance for any schedule

---

## ✅ Current System Status

### Fully Implemented & Tested (100% Coverage)

#### 1. Constraint Validation
- **Module:** `domain/constraint_validator.py`
- **CLI Tool:** `check-constraints`
- **What it does:** Parses and validates constraint syntax from dancers/RDs
- **Input formats:**
  - Day of week: `monday`, `M`, `tue`
  - Time blocks: `monday 14:00-16:00`, `W after 2 PM`
  - Dates: `Jan 20`, `01/15/2025`
  - Date ranges: `Jan 20-25`, `12/10/25 - 12/15/25`
- **Output:** List of valid/invalid tokens with error messages

#### 2. RD Conflict Detection
- **Module:** `domain/conflict_analyzer.py`
- **What it does:** Identifies when RDs are unavailable for scheduled slots
- **Inputs:**
  - RD constraints (availability text)
  - Venue schedule (slots with dates/times)
  - Dance-to-RD mapping
- **Output:** `ConflictReport` with:
  - List of conflicts (RD, venue, time, affected dances)
  - RDs with conflicts
  - Total conflict count

#### 3. Dance Availability Catalog
- **Module:** `domain/catalog_generator.py`
- **What it does:** Categorizes every dance for every venue slot
- **Inputs:**
  - Dance cast lists
  - Dancer constraints
  - RD constraints
  - Dance-to-RD mapping
  - Venue schedule
- **Output:** `VenueCatalog` with each slot showing:
  - **Conflict-free dances** (100% attendance, RD available)
  - **Cast-conflict dances** (partial attendance, sorted by %)
  - **RD-blocked dances** (RD unavailable)

#### 4. Supporting Infrastructure
- **Grammar parser** (`grammar.py`) - 99% coverage
- **Interval models** (`models/intervals.py`) - Time/date handling
- **Conflict detection** (`scheduling/conflicts.py`) - Slot conflict logic
- **Persistence base** (`persistence/base.py`) - CSV/Sheets data loading

### Working CLI Tools

```bash
# Validate constraints from CSV
check-constraints --csv dancer_constraints.csv --id-column dancer_id --column conflicts

# Validate constraints from Google Sheets
check-constraints --sheet-id SHEET_ID --worksheet "Dancer Constraints"

# Full scheduling workflow (needs verification after refactor)
rehearsal-schedule --help
```

---

## 📊 Google Sheets Data Model

### Required Sheets Structure

The system expects Google Sheets with these worksheets:

#### Sheet 1: "Dancer Constraints"
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `dancer_id` | Text | Unique ID | `D001`, `D002` |
| `conflicts` | Text | Comma-separated constraints | `monday, 14:00-16:00, Jan 20-25` |

**Notes:**
- Empty `conflicts` = fully available
- Invalid syntax flagged by validator
- Names stored separately (see "Dancer Names" sheet)

---

#### Sheet 2: "RD Constraints"
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `rhd_id` | Text | Unique RD ID | `RD001`, `RD002` |
| `conflicts` | Text | Comma-separated constraints | `tuesday, W after 5 PM` |

**Notes:**
- Same constraint format as dancers
- RDs block entire dances when unavailable

---

#### Sheet 3: "Dance Cast"
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `dance_id` | Text | Unique dance ID | `Dance01`, `Dance02` |
| `dancer_id` | Text | Dancer in this dance | `D001` |

**Alternative format (pivot table style):**
| `dance_id` | `D001` | `D002` | `D003` | ... |
|------------|--------|--------|--------|-----|
| `Dance01`  | 1      | 1      |        |     |
| `Dance02`  |        | 1      | 1      |     |

**Notes:**
- One row per dance-dancer pair (first format)
- OR one row per dance with 1/0 columns (second format)
- System needs to map dance → list of dancers

---

#### Sheet 4: "Dance Metadata"
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `dance_id` | Text | Unique dance ID | `Dance01` |
| `rhd_id` | Text | Rehearsal director | `RD001` |
| `duration` | Text/Number | Dance length (optional) | `4:30` or `270` (seconds) |
| `order` | Number | Performance order (optional) | `1`, `2`, `3` |

**Notes:**
- `rhd_id` maps dance to rehearsal director
- `duration` helps identify tight costume changes
- `order` determines production program sequence

---

#### Sheet 5: "Venue Schedule"
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `venue` | Text | Studio/location name | `Studio A`, `Main Hall` |
| `day` | Text | Day of week | `Monday`, `mon` |
| `date` | Text | Date of slot | `01/20/2025` |
| `start` | Text | Start time | `14:00`, `2:00 PM` |
| `end` | Text | End time | `16:00`, `4:00 PM` |

**Notes:**
- Date format: `MM/DD/YYYY` or `MM/DD/YY`
- Time format: 24-hour (`14:00`) or 12-hour (`2:00 PM`)
- System checks conflicts against these slots

---

#### Sheet 6: "Dancer Names" (for reporting)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `dancer_id` | Text | Unique ID | `D001` |
| `dancer_name` | Text | Display name | `Alice Smith` |

---

#### Sheet 7: "RD Names" (for reporting)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `rhd_id` | Text | Unique ID | `RD001` |
| `rhd_name` | Text | Display name | `Bob Jones` |

---

#### Sheet 8: "Dance Names" (for reporting)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `dance_id` | Text | Unique ID | `Dance01` |
| `dance_name` | Text | Display name | `Opening Number` |
| `choreographer` | Text | Choreographer name | `Jane Doe` |

---

#### Sheet 9: "Rehearsal Schedule" (optional - for validation)
| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `dance_id` | Text | Dance being rehearsed | `Dance01` |
| `venue` | Text | Location | `Studio A` |
| `date` | Text | Rehearsal date | `01/20/2025` |
| `start` | Text | Start time | `14:00` |
| `end` | Text | End time | `16:00` |

**Notes:**
- This sheet can be INPUT (director's proposed schedule)
- OR OUTPUT (system-generated schedule)
- System can validate and report expected attendance

---

## 🎯 Priority Implementation Plan

### Phase 1: Core Validation & Reporting (Next 2-3 Weeks)

**Goal:** Be ready when live data arrives

#### 1.1 Validate Constraints ✅ DONE
- Tool: `check-constraints`
- Status: Working, tested at 100%
- Action: Verify with sample Google Sheet

#### 1.2 RD Conflict Report 🔨 BUILD
**What:** Generate report showing RD conflicts
**Input:** Google Sheets (RD Constraints, Venue Schedule, Dance Metadata)
**Output:** Markdown/CSV report with:
- Which RDs conflict with which slots
- Which dances are blocked by RD conflicts
- Summary statistics

**Implementation:**
```python
from rehearsal_scheduler.domain.conflict_analyzer import ConflictAnalyzer
from rehearsal_scheduler.reporting.analysis_formatter import format_rd_conflicts

# Load data from sheets
analyzer = ConflictAnalyzer(validate_token, check_slot_conflicts, ...)
report = analyzer.analyze(rhd_conflicts, venue_schedule, dance_map)

# Format for director
markdown = format_rd_conflicts(report, rd_names, dance_names)
```

#### 1.3 Dance Availability Catalog 🔨 BUILD
**What:** Show which dances can rehearse in each slot
**Input:** All Google Sheets
**Output:** Markdown/CSV report per venue slot:
```markdown
## Studio A - Monday 01/20/2025 14:00-16:00

### ✅ Conflict-Free (100% attendance)
- Dance01: Opening Number (8 dancers, RD: Bob Jones)
- Dance03: Finale (12 dancers, RD: Alice Smith)

### ⚠️ Partial Attendance
- Dance02: Middle Solo (75% - 3/4 dancers, missing: Jane Doe)
  - RD: Bob Jones

### ❌ RD Blocked
- Dance04: Group Dance (RD: Carol Brown unavailable)
```

**Implementation:**
```python
from rehearsal_scheduler.domain.catalog_generator import CatalogGenerator

generator = CatalogGenerator(validate_token, check_slot_conflicts)
catalog = generator.generate(dance_cast, dancer_constraints, rhd_constraints, 
                             dance_to_rd, venue_slots)

markdown = format_venue_catalog(catalog, dance_names, dancer_names, rd_names)
```

#### 1.4 Schedule Attendance Report 🔨 BUILD (Priority 4a)
**What:** Validate director's proposed schedule
**Input:** 
- Director's schedule (Sheet 9)
- All constraint/cast data
**Output:** Report showing expected attendance for each rehearsal:
```markdown
## Proposed Schedule Attendance Report

### Monday 01/20/2025

#### 14:00-16:00 - Studio A - Dance01: Opening Number
- **Expected Attendance:** 7/8 dancers (87.5%)
- **Missing:** D005 (Jane Doe) - "monday 14:00-16:00"
- **RD Status:** ✅ Available (Bob Jones)

#### 16:00-18:00 - Studio A - Dance02: Middle Solo  
- **Expected Attendance:** 4/4 dancers (100%)
- **RD Status:** ✅ Available (Bob Jones)
```

---

### Phase 2: Automatic Scheduling (4-6 Weeks)

**Goal:** Generate optimal schedules automatically

#### 2.1 Schedule Generator
- Use catalog data to assign dances to slots
- Optimize for:
  - Maximum conflict-free rehearsals
  - Minimize RD conflicts
  - Balance workload across venues/days
  - Consider dance dependencies (if any)

#### 2.2 Schedule Optimizer
- Improve initial schedule
- Constraint satisfaction problem (CSP)
- Or greedy algorithm with backtracking

---

## 📋 Integration Testing Strategy

### CSV-Based Integration Tests

**Advantages:**
- Fast execution
- Version controlled
- No external dependencies
- Easy to debug

**Test Structure:**
```
test/integration/fixtures/
├── sample_scenario_1/
│   ├── dancer_constraints.csv
│   ├── rd_constraints.csv
│   ├── dance_cast.csv
│   ├── dance_metadata.csv
│   ├── venue_schedule.csv
│   ├── dancer_names.csv
│   ├── rd_names.csv
│   └── dance_names.csv
└── sample_scenario_2/
    └── ...
```

**Test Cases:**
1. **Perfect scenario** - No conflicts, all dances schedulable
2. **RD conflicts** - Some RDs unavailable
3. **Dancer conflicts** - Partial cast availability
4. **Complex scenario** - Mix of all conflict types
5. **Edge cases** - Empty casts, all-day conflicts, date ranges

---

## 🔄 Google Sheets → Repo Workflow

### Challenge
Google Sheets are collaborative but not version-controlled

### Proposed Solution: "Sheet Snapshots"

**Option 1: Export to CSV (Recommended)**
```bash
# Script to download sheets as CSV
scripts/download_sheet_snapshot.sh SHEET_ID output_dir/

# Creates:
output_dir/
├── dancer_constraints.csv
├── rd_constraints.csv
├── dance_cast.csv
└── ...

# Commit to repo as "snapshots"
git add test/integration/fixtures/snapshot_2026_01_22/
git commit -m "Snapshot: Week 3 data model"
```

**Option 2: Google Sheets → GitHub Sync**
- Use GitHub Actions
- Scheduled export (nightly)
- Auto-commit changes
- Allows diff/review of data changes

**Option 3: Hybrid Approach**
- **Live sheets** for directors (Google Sheets)
- **Model/template sheet** in repo (CSV)
- **Weekly snapshots** for testing

---

## 📝 Immediate Action Items

### This Week
1. ✅ **Refactoring complete** (Just finished!)
2. 🔨 **Create model Google Sheet** with all required worksheets
3. 🔨 **Test `check-constraints` tool** with model sheet
4. 🔨 **Document sheet structure** for directors (user guide)

### Next Week  
5. 🔨 **Build RD conflict report generator**
6. 🔨 **Build dance availability catalog formatter**
7. 🔨 **Create CSV integration test suite**

### Week 3 (Before Live Data)
8. 🔨 **Build schedule attendance validator** (Priority 4a)
9. 🔨 **Create production program report** template
10. 🔨 **Director training/walkthrough**

---

## 🎨 Production Program Report (Future)

**Input:** Final schedule + all metadata
**Output:** Production program listing

```markdown
# [Show Name] - Production Program

## Act I

### 1. Opening Number
- **Choreographer:** Jane Doe
- **Music:** "Overture" (4:30)
- **Dancers:** Alice Smith, Bob Jones, Carol Brown, ...

### 2. Solo Performance
- **Choreographer:** Bob Jones  
- **Music:** "Reflection" (3:15)
- **Dancers:** Alice Smith

[Costume Change: 5 minutes] ⚠️

### 3. Group Dance
- **Choreographer:** Jane Doe
- **Music:** "Unity" (5:00)
- **Dancers:** Alice Smith, Bob Jones, Carol Brown, ...

---

## Act II
...

---

## Production Statistics
- **Total Dances:** 15
- **Total Dancers:** 24
- **Total Duration:** 78 minutes
- **Costume Changes Required:** 8
- **Critical Changes (<2 min):** 2 ⚠️
```

---

## 🔧 Technical Notes

### Data Flow Architecture

```
Google Sheets (Live Data)
    ↓
Persistence Layer (load data)
    ↓
Domain Logic (validate, analyze, generate)
    ↓
Reporting Layer (format output)
    ↓
Output (Markdown, CSV, console)
```

### Key Design Decisions

1. **IDs everywhere** - All business logic uses IDs
2. **Names for display only** - Name lookup happens in reporting layer
3. **Constraint text parsing** - Grammar handles all syntax variations
4. **Separation of concerns** - Domain logic 100% tested, formatters simple templates

---

## 📚 Documentation Needed

1. **User Guide for Directors**
   - How to fill in Google Sheets
   - Constraint syntax reference
   - How to read reports

2. **Developer Guide**
   - How to add new constraint types
   - How to add new report formats
   - Testing strategy

3. **Google Sheets Template**
   - Pre-formatted with all required sheets
   - Example data showing format
   - Data validation rules where possible

---

## 🎯 Success Metrics

### Short-term (3 weeks)
- ✅ Directors can validate all constraints
- ✅ System generates RD conflict reports
- ✅ System generates dance availability catalogs
- ✅ System validates proposed schedules

### Medium-term (6 weeks)
- ✅ System generates initial schedules
- ✅ Directors can refine generated schedules
- ✅ Production program auto-generated

### Long-term
- ⏱️ Time savings: Manual work reduced by 80%
- ✅ Error reduction: No missed conflicts
- ✅ Director satisfaction: Easy to use

---

**Next Steps:** Create model Google Sheet matching this specification.