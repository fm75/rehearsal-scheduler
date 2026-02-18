"""
Implementation Guide: Separate RD and Dancer Availability

PROBLEM:
Currently, calculate_full_availability_for_group() returns a single "100% availability" 
window that represents when BOTH the RD AND all dancers are available. This prevents 
scheduling in windows where the RD is available but some dancers aren't.

SOLUTION:
Return three separate availability measures for each dance group/slot combination:
1. RD availability - when the assigned RD can make it
2. Dancer 100% - when all dancers can make it  
3. Combined 100% - when RD AND all dancers can make it (current behavior)

================================================================================
STEP 1: Update calculate_full_availability_for_group()
================================================================================

File: src/rehearsal_scheduler/domain/scheduling_catalog.py

Change signature from:
    def calculate_full_availability_for_group(...) -> str:

To:
    def calculate_full_availability_for_group(
        dg_id: str,
        slot_interval,
        group_cast_df: pd.DataFrame,
        dancer_constraints_df: pd.DataFrame,
        slot: RehearsalSlot,
        rd_id: str = None,                    # NEW
        rd_constraints_df: pd.DataFrame = None # NEW
    ) -> tuple:  # Returns (rd_str, dancer_str, combined_str)

Logic:
1. Calculate dancer 100% availability (existing logic)
2. Calculate RD availability (new):
   - If rd_id and rd_constraints_df provided:
     - Find RD's constraints
     - Calculate their available windows
   - Else: assume fully available
3. Calculate combined (new):
   - Intersect RD windows with dancer windows
4. Return tuple: (rd_avail_str, dancer_avail_str, combined_avail_str)

================================================================================
STEP 2: Update generate_availability_matrix.py
================================================================================

File: src/rehearsal_scheduler/scripts/generate_availability_matrix.py

In generate_availability_matrix() function:

OLD:
    # Calculate 100% availability (returns string)
    availability_str = calculate_full_availability_for_group(...)
    row_data[f'slot_{i+1}'] = availability_str

NEW:
    # Get RD info for this group
    rd_id = group_row['current_rd']
    
    # Calculate three availability measures (returns tuple)
    rd_avail, dancer_avail, combined_avail = calculate_full_availability_for_group(
        dg_id,
        slot_interval,
        data['group_cast'],
        data['dancer_constraints'],
        slot,
        rd_id=rd_id,
        rd_constraints_df=data['rd_constraints']
    )
    
    # Store all three in separate columns
    row_data[f'slot_{i+1}_rd'] = rd_avail
    row_data[f'slot_{i+1}_dancers'] = dancer_avail
    row_data[f'slot_{i+1}_combined'] = combined_avail

Output CSV will now have:
    dance_group, priority, participation, 
    slot_1_rd, slot_1_dancers, slot_1_combined,
    slot_2_rd, slot_2_dancers, slot_2_combined, ...

================================================================================
STEP 3: Update generate_schedule.py
================================================================================

File: src/rehearsal_scheduler/scripts/generate_schedule.py

In greedy_schedule_slot() function:

Update the parsing section:

OLD:
    # Parse availability intervals for each candidate
    candidates['parsed_intervals'] = candidates[slot_name].apply(safe_parse_availability)

NEW:
    # Parse THREE availability columns
    slot_combined = f'{slot_name}_combined'
    slot_rd = f'{slot_name}_rd'
    
    candidates['combined_intervals'] = candidates[slot_combined].apply(safe_parse_availability)
    candidates['rd_intervals'] = candidates[slot_rd].apply(safe_parse_availability)

Update scheduling logic:

OLD:
    if available_intervals and does_duration_fit_in_intervals(requested_minutes, available_intervals):

NEW:
    combined_intervals = row['combined_intervals']
    rd_intervals = row['rd_intervals']
    
    # Try combined first (best case - RD + all dancers)
    if combined_intervals and does_duration_fit_in_intervals(requested_minutes, combined_intervals):
        schedule.append({
            'order': order,
            'minutes': requested_minutes,
            'dance_group': dance_group,
            'notes': ''
        })
        ...
    
    # Fall back to RD-only windows (partial dancer coverage)
    elif rd_intervals and does_duration_fit_in_intervals(requested_minutes, rd_intervals):
        schedule.append({
            'order': order,
            'minutes': requested_minutes,
            'dance_group': dance_group,
            'notes': 'RD available, partial dancer coverage'
        })
        ...

================================================================================
STEP 4: Update Tests
================================================================================

File: test/integration/test_rd_availability.py

Update test expectations for calculate_full_availability_for_group():

OLD:
    result = calculate_full_availability_for_group(...)
    assert '6:00 pm' in result

NEW:
    rd_avail, dancer_avail, combined_avail = calculate_full_availability_for_group(
        ...,
        rd_id='rd_01',
        rd_constraints_df=rd_constraints
    )
    assert '6:00 pm' in combined_avail

Add new tests:
- test_calculate_separate_rd_dancer_availability()
- test_rd_available_dancers_not()
- test_dancers_available_rd_not()

================================================================================
PRIORITY CALCULATION
================================================================================

The priority calculation in generate_availability_matrix.py should use:
- RD availability for ranking (can't rehearse without RD)
- Not combined (too restrictive)

Update calculate_priority_score() to use slot_X_rd columns instead of slot_X_combined.

================================================================================
SUMMARY
================================================================================

Changes needed:
1. scheduling_catalog.py: Update calculate_full_availability_for_group() signature and logic
2. generate_availability_matrix.py: Output 3 columns per slot, use rd for priority
3. generate_schedule.py: Try combined first, fall back to RD-only
4. test_rd_availability.py: Update test expectations

Result:
- Can schedule in RD's available windows even if not all dancers can make it
- Clear notes indicate when it's "full coverage" vs "RD available, partial dancers"
- Amy can make informed decisions about which partial-coverage rehearsals to accept
"""