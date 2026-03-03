"""
STEP-BY-STEP INTEGRATION GUIDE
===============================

Follow these steps to integrate RD/dancer availability separation.

STEP 1: Update scheduling_catalog.py
=====================================

1.1) Replace calculate_full_availability_for_group() function
   - Location: Line 571-674
   - Replace with: Content from updated_calculate_full_availability.py
   
1.2) Update find_ineligible_groups() to check RD availability windows
   - Current logic: If RD has ANY conflict → group ineligible
   - New logic: If RD has NO available time → group ineligible
   
   Replace find_ineligible_groups() with:

```python
def find_ineligible_groups(
    rd_conflicts: List[ConflictInfo],
    dance_groups_df: pd.DataFrame,
    slot_interval,
    slot: RehearsalSlot,
    rd_constraints_df: pd.DataFrame
) -> List[DanceGroupInfo]:
    """
    Find dance groups that cannot be scheduled due to RD having zero availability.
    
    Args:
        rd_conflicts: List of RD conflicts (not used anymore - kept for compatibility)
        dance_groups_df: DataFrame with dance group info
        slot_interval: TimeInterval for the slot
        slot: RehearsalSlot
        rd_constraints_df: RD constraints DataFrame
        
    Returns:
        List of DanceGroupInfo for groups whose RD has NO availability this slot
    """
    ineligible = []
    
    for _, row in dance_groups_df.iterrows():
        rd_id = row['current_rd']
        
        # Calculate RD availability
        rd_availability, _, _ = calculate_full_availability_for_group(
            row['dg_id'],
            slot_interval,
            pd.DataFrame(),  # Empty - we only need RD availability
            pd.DataFrame(),  # Empty
            slot,
            rd_id=rd_id,
            rd_constraints_df=rd_constraints_df
        )
        
        # Only mark as ineligible if RD has ZERO availability
        if rd_availability == "None":
            ineligible.append(DanceGroupInfo(
                dg_id=row['dg_id'],
                dg_name=row['dg_name'],
                rd_id=rd_id,
                rd_name=row['current_rd_name']
            ))
    
    return ineligible
```

1.3) Update generate_scheduling_catalog() to pass new parameters

Find this section (around line 700):
```python
        # Find dance groups that can't be scheduled (RD unavailable)
        ineligible_groups = find_ineligible_groups(rd_conflicts, data['dance_groups'])
```

Replace with:
```python
        # Find dance groups that can't be scheduled (RD has zero availability)
        from rehearsal_scheduler.models.intervals import TimeInterval
        from datetime import time
        
        slot_interval = TimeInterval(
            time(slot.start_time // 100, slot.start_time % 100),
            time(slot.end_time // 100, slot.end_time % 100)
        )
        
        ineligible_groups = find_ineligible_groups(
            rd_conflicts, 
            data['dance_groups'],
            slot_interval,
            slot,
            data['rd_constraints']
        )
```


STEP 2: Update generate_availability_matrix.py
===============================================

2.1) Update where calculate_full_availability_for_group() is called

Find (around line 330):
```python
            availability_str = calculate_full_availability_for_group(
                dg_id,
                slot_interval,
                data['group_cast'],
                data['dancer_constraints'],
                slot
            )
            
            full_availability_by_slot[slot_names[i]] = availability_str if availability_str != "None" else ""
```

Replace with:
```python
            # Get RD info for this group
            rd_id = group_row['current_rd']
            
            # Calculate three availability measures
            rd_avail, dancer_avail, combined_avail = calculate_full_availability_for_group(
                dg_id,
                slot_interval,
                data['group_cast'],
                data['dancer_constraints'],
                slot,
                rd_id=rd_id,
                rd_constraints_df=data['rd_constraints']
            )
            
            # Store all three
            full_availability_by_slot[slot_names[i]] = {
                'rd': rd_avail if rd_avail != "None" else "",
                'dancers': dancer_avail if dancer_avail != "None" else "",
                'combined': combined_avail if combined_avail != "None" else ""
            }
```

2.2) Update the row_data creation

Find (around line 365):
```python
        # Add slot columns
        for i, slot_name in enumerate(slot_names):
            row_data[f'slot_{i+1}'] = full_availability_by_slot[slot_names[i]] if full_availability_by_slot[slot_names[i]] != "None" else ""
```

Replace with:
```python
        # Add slot columns (3 per slot: rd, dancers, combined)
        for i, slot_name in enumerate(slot_names):
            avail = full_availability_by_slot[slot_names[i]]
            row_data[f'slot_{i+1}_rd'] = avail['rd']
            row_data[f'slot_{i+1}_dancers'] = avail['dancers']
            row_data[f'slot_{i+1}_combined'] = avail['combined']
```

2.3) Update priority calculation to use RD availability

Find calculate_priority_score() calls and ensure they use rd availability columns, not combined.


STEP 3: Update constraint_first_scheduler.py
=============================================

3.1) Update constraint_first_schedule_slot() to use three columns

Find (around line 140):
```python
        # Parse availability intervals
        # NOTE: These column names will change when we implement RD/dancer separation
        # For now, using current column structure
        slot_avail_str = group_row.get(slot_name, '')
        available_intervals = safe_parse(slot_avail_str)
```

Replace with:
```python
        # Parse all three availability types
        slot_rd = f'{slot_name}_rd'
        slot_dancers = f'{slot_name}_dancers'
        slot_combined = f'{slot_name}_combined'
        
        rd_intervals = safe_parse(group_row.get(slot_rd, ''))
        dancer_intervals = safe_parse(group_row.get(slot_dancers, ''))
        combined_intervals = safe_parse(group_row.get(slot_combined, ''))
```

3.2) Update scheduling logic to try combined first, fall back to RD

Replace the scheduling if/else logic with:
```python
        # Try combined first (best case - RD + all dancers)
        if combined_intervals and does_duration_fit_in_intervals(requested_minutes, combined_intervals):
            if requested_minutes <= remaining_minutes:
                scheduled.append({
                    'status': 'scheduled',
                    'order': order,
                    'minutes': requested_minutes,
                    'dance_group': dance_group,
                    'notes': '',
                    'available_windows': format_intervals_for_display(combined_intervals)
                })
                remaining_minutes -= requested_minutes
                scheduled_groups.add(dance_group)
                order += 10
            else:
                unable.append({
                    'status': 'unable',
                    'unable_order': len(unable) + 1,
                    'minutes': requested_minutes,
                    'dance_group': dance_group,
                    'reason': f'Insufficient slot capacity ({remaining_minutes} min available, needs {requested_minutes})',
                    'available_windows': format_intervals_for_display(combined_intervals),
                    'participation_pct': int(participation * 100)
                })
        
        # Try RD-only (partial dancer coverage)
        elif rd_intervals and does_duration_fit_in_intervals(requested_minutes, rd_intervals):
            if requested_minutes <= remaining_minutes and participation >= min_participation:
                scheduled.append({
                    'status': 'scheduled',
                    'order': order,
                    'minutes': requested_minutes,
                    'dance_group': dance_group,
                    'notes': f'RD available, partial dancers ({int(participation*100)}%)',
                    'available_windows': format_intervals_for_display(rd_intervals)
                })
                remaining_minutes -= requested_minutes
                scheduled_groups.add(dance_group)
                order += 10
            else:
                reason = f'Insufficient slot capacity ({remaining_minutes} min available, needs {requested_minutes})' if requested_minutes > remaining_minutes else f'Low dancer coverage ({int(participation*100)}%)'
                unable.append({
                    'status': 'unable',
                    'unable_order': len(unable) + 1,
                    'minutes': requested_minutes,
                    'dance_group': dance_group,
                    'reason': reason,
                    'available_windows': format_intervals_for_display(rd_intervals),
                    'participation_pct': int(participation * 100)
                })
        
        # Cannot fit
        else:
            if not rd_intervals:
                reason = 'RD has no availability this slot'
            elif not dancer_intervals:
                reason = 'Dancers have no overlapping availability'
            else:
                reason = f'Duration {requested_minutes}min does not fit available windows'
            
            unable.append({
                'status': 'unable',
                'unable_order': len(unable) + 1,
                'minutes': requested_minutes,
                'dance_group': dance_group,
                'reason': reason,
                'available_windows': format_intervals_for_display(rd_intervals) if rd_intervals else '',
                'participation_pct': int(participation * 100)
            })
```


STEP 4: Update Tests
====================

4.1) Update test_rd_availability.py

All tests that call calculate_full_availability_for_group() need to:

OLD:
```python
result = calculate_full_availability_for_group(...)
assert '6:00 pm' in result
```

NEW:
```python
rd_avail, dancer_avail, combined_avail = calculate_full_availability_for_group(
    ...,
    rd_id='rd_01',
    rd_constraints_df=rd_constraints
)
assert '6:00 pm' in combined_avail
```

4.2) Add new test for RD/dancer separation

```python
def test_calculate_separate_rd_dancer_availability():
    """Test that RD and dancer availability are calculated separately."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 2, 17),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    slot_interval = TimeInterval(time(18, 0), time(21, 0))
    
    group_cast = pd.DataFrame({
        'd_01': ['1', '1'],
    }, index=['dancer_01', 'dancer_02'])
    
    dancer_constraints = pd.DataFrame({
        'dancer_id': ['dancer_01', 'dancer_02'],
        'full_name': ['Alice', 'Bob'],
        'constraints': [
            'Monday before 7:00 pm',  # Alice conflicts 6-7pm
            ''  # Bob fully available
        ]
    })
    
    rd_constraints = pd.DataFrame({
        'rd_id': ['rd_01'],
        'full_name': ['Director'],
        'constraints': ['Monday after 8:00 pm']  # RD conflicts 8-9pm
    })
    
    rd_avail, dancer_avail, combined_avail = calculate_full_availability_for_group(
        'd_01',
        slot_interval,
        group_cast,
        dancer_constraints,
        slot,
        rd_id='rd_01',
        rd_constraints_df=rd_constraints
    )
    
    # RD available 6-8pm
    assert '6:00 pm' in rd_avail
    assert '8:00 pm' in rd_avail
    
    # Dancers available 7-9pm (Alice blocks 6-7)
    assert '7:00 pm' in dancer_avail
    assert '9:00 pm' in dancer_avail
    
    # Combined is intersection: 7-8pm
    assert '7:00 pm' in combined_avail
    assert '8:00 pm' in combined_avail
    assert '9:00 pm' not in combined_avail  # RD not available
    assert '6:00 pm' not in combined_avail  # Alice not available
```


STEP 5: Verify
==============

After making all changes:

1. Run tests:
   ```bash
   pytest test/integration/test_rd_availability.py -v
   pytest test/integration/test_scheduling_catalog.py -v
   ```

2. Generate new availability matrix:
   ```bash
   python -m rehearsal_scheduler.scripts.generate_availability_matrix
   ```
   
   Check output CSV has columns:
   - slot_1_rd, slot_1_dancers, slot_1_combined
   - slot_2_rd, slot_2_dancers, slot_2_combined
   - etc.

3. Generate schedule:
   ```bash
   python -m rehearsal_scheduler.scripts.generate_schedule --verbose
   ```
   
   Verify:
   - Groups with RD availability but partial dancers get scheduled with notes
   - Unable CSV shows groups separated by reason (RD unavailable vs dancer issues)

4. Run analyze-scheduling:
   ```bash
   python -m rehearsal_scheduler.scripts.analyze_scheduling --show-availability
   ```
   
   Verify:
   - Dance groups with partial RD availability are NOT marked ineligible
   - They show availability during RD's available windows


TROUBLESHOOTING
================

If tests fail with "too many values to unpack":
- You missed updating a caller of calculate_full_availability_for_group()
- Search for all calls and ensure they expect tuple of 3 values

If availability matrix has wrong columns:
- Check step 2.2 - make sure you're creating 3 columns per slot

If scheduler doesn't use RD windows:
- Check step 3.2 - ensure fallback to rd_intervals is implemented

If groups still marked ineligible incorrectly:
- Check step 1.2 - find_ineligible_groups() should check for "None" not just any conflict
"""