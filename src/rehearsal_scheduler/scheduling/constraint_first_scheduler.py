"""
Constraint-First Scheduling Implementation

Implements smart scheduling that prioritizes most-constrained RDs first,
then schedules their dance groups in optimal slots.

Also outputs "unable to fit" groups with availability windows to help
manual scheduling decisions.
"""

import pandas as pd
from typing import Dict, List, Tuple, Set
from rehearsal_scheduler.models.interval_parsing import (
    parse_availability_string,
    does_duration_fit_in_intervals
)


def calculate_rd_total_availability(
    availability_df: pd.DataFrame,
    slot_columns: List[str]
) -> Dict[str, float]:
    """
    Calculate total available minutes for each RD across all slots.
    
    Args:
        availability_df: Availability matrix with rd availability columns
        slot_columns: List of slot column names (e.g., ['slot_1_rd', 'slot_2_rd'])
        
    Returns:
        Dict mapping RD name -> total available minutes
    """
    # This requires knowing which RD directs which groups
    # For now, return empty - needs to be implemented with RD->group mapping
    # TODO: Implement after we separate RD/dancer availability
    return {}


def get_groups_for_rd(rd_id: str, dance_groups_df: pd.DataFrame) -> List[str]:
    """
    Get list of dance group IDs assigned to an RD.
    
    Args:
        rd_id: Rehearsal director ID
        dance_groups_df: DataFrame with dg_id and current_rd columns
        
    Returns:
        List of dance group IDs
    """
    if dance_groups_df is None or dance_groups_df.empty:
        return []
    
    rd_groups = dance_groups_df[dance_groups_df['current_rd'] == rd_id]
    return rd_groups['dg_id'].tolist()


def format_intervals_for_display(intervals) -> str:
    """Format list of TimeInterval objects as display string."""
    if not intervals:
        return ""
    
    from rehearsal_scheduler.reporting.constraint_formatter import format_time
    
    formatted = []
    for interval in intervals:
        start_str = format_time(interval.start.hour * 100 + interval.start.minute)
        end_str = format_time(interval.end.hour * 100 + interval.end.minute)
        formatted.append(f"{start_str} - {end_str}")
    
    return ", ".join(formatted)


def constraint_first_schedule_slot(
    slot_name: str,
    slot_duration: int,
    availability_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    scheduled_groups: Set[str],
    priority_ordered_groups: List[Dict],
    rd_constraints_df: pd.DataFrame = None,
    min_participation: float = 0.70
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Schedule dance groups for one slot using constraint-first approach.
    
    Groups are processed in priority order (most constrained first).
    Returns both scheduled and unable-to-fit groups.
    
    Args:
        slot_name: Slot identifier (e.g., 'slot_1')
        slot_duration: Total minutes in slot
        availability_df: Availability matrix
        allocations_df: Time allocations
        scheduled_groups: Set of already-scheduled group names
        priority_ordered_groups: List of group info dicts, pre-sorted by constraint
        min_participation: Minimum dancer participation to allow RD-only scheduling
        
    Returns:
        Tuple of (scheduled_df, unable_df)
    """
    scheduled = []
    unable = []
    remaining_minutes = slot_duration
    order = 10
    
    # Helper to safely parse availability
    def safe_parse(avail_str):
        if pd.isna(avail_str) or avail_str == '':
            return []
        try:
            return parse_availability_string(str(avail_str))
        except:
            return []
    
    for group_info in priority_ordered_groups:
        dance_group = group_info['dance_group']
        
        if dance_group in scheduled_groups:
            continue
        
        requested_minutes = group_info['minutes']
        participation = group_info.get('participation', 0)
        
        # Get availability from matrix
        group_row = availability_df[availability_df['dance_group'] == dance_group]
        if group_row.empty:
            continue
        
        group_row = group_row.iloc[0]
        
        # # Parse availability intervals
        # # NOTE: These column names will change when we implement RD/dancer separation
        # # For now, using current column structure
        # slot_avail_str = group_row.get(slot_name, '')
        # available_intervals = safe_parse(slot_avail_str)
        
        # Parse all three availability types
        slot_rd = f'{slot_name}_rd'
        slot_dancers = f'{slot_name}_dancers'
        slot_combined = f'{slot_name}_combined'
        
        rd_intervals = safe_parse(group_row.get(slot_rd, ''))
        dancer_intervals = safe_parse(group_row.get(slot_dancers, ''))
        combined_intervals = safe_parse(group_row.get(slot_combined, ''))
        
        
    #     # Try to schedule
    #     if available_intervals and does_duration_fit_in_intervals(requested_minutes, available_intervals):
    #         if requested_minutes <= remaining_minutes:
    #             # Success - fits in slot
    #             scheduled.append({
    #                 'status': 'scheduled',
    #                 'order': order,
    #                 'minutes': requested_minutes,
    #                 'dance_group': dance_group,
    #                 'notes': '',
    #                 'available_windows': format_intervals_for_display(available_intervals)
    #             })
    #             remaining_minutes -= requested_minutes
    #             scheduled_groups.add(dance_group)
    #             order += 10
    #         else:
    #             # Fits in availability window but not enough slot capacity
    #             unable.append({
    #                 'status': 'unable',
    #                 'unable_order': len(unable) + 1,
    #                 'minutes': requested_minutes,
    #                 'dance_group': dance_group,
    #                 'reason': f'Insufficient slot capacity ({remaining_minutes} min available, needs {requested_minutes})',
    #                 'available_windows': format_intervals_for_display(available_intervals),
    #                 'participation_pct': int(participation * 100)
    #             })
    #     else:
    #         # Cannot fit
    #         if not available_intervals:
    #             reason = 'No availability this slot'
    #         else:
    #             reason = f'Duration {requested_minutes}min does not fit available windows'
            
    #         unable.append({
    #             'status': 'unable',
    #             'unable_order': len(unable) + 1,
    #             'minutes': requested_minutes,
    #             'dance_group': dance_group,
    #             'reason': reason,
    #             'available_windows': format_intervals_for_display(available_intervals),
    #             'participation_pct': int(participation * 100)
    #         })
    # xxxxxxxxxxxx
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
    # yyyyyyyyyyyy=================================================
    # Add idle time
    if remaining_minutes > 0:
        scheduled.append({
            'status': 'idle',
            'order': order,
            'minutes': remaining_minutes,
            'dance_group': '(idle)',
            'notes': '',
            'available_windows': ''
        })
    
    return (pd.DataFrame(scheduled), pd.DataFrame(unable))


def constraint_first_schedule_all(
    availability_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    dance_groups_df: pd.DataFrame,
    rehearsals_df: pd.DataFrame,
    rd_constraints_df: pd.DataFrame = None
) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Generate schedules for all slots using constraint-first approach.
    
    Algorithm:
    1. Sort dance groups by priority (most constrained first)
    2. For each slot, process groups in priority order
    3. Track both scheduled and unable-to-fit groups
    
    Args:
        availability_df: Availability matrix
        allocations_df: Time allocations
        dance_groups_df: Dance group info
        rehearsals_df: Rehearsal slot info
        
    Returns:
        Dict mapping slot_name -> (scheduled_df, unable_df)
    """
    from rehearsal_scheduler.scripts.generate_schedule import (
        parse_slot_columns,
        parse_slot_duration
    )
    
    # Get slot columns
    slot_columns = parse_slot_columns(availability_df)
    
    # Merge availability with allocations to get all info in one place
    merged = pd.merge(
        availability_df,
        allocations_df[['dg_name', 'minutes']],
        left_on='dance_group',
        right_on='dg_name',
        how='left'
    )
    merged['minutes'] = merged['minutes'].fillna(30).astype(int)
    
    # Sort by priority (ascending - most constrained first)
    priority_ordered = merged.sort_values('priority', ascending=True)
    
    # Convert to list of dicts for easier processing
    priority_groups = priority_ordered.to_dict('records')
    
    # Schedule each slot
    schedules = {}
    scheduled_groups = set()
    
    for i, slot_name in enumerate(slot_columns):
        slot_duration = parse_slot_duration(slot_name, rehearsals_df)
        
        scheduled_df, unable_df = constraint_first_schedule_slot(
            slot_name,
            slot_duration,
            availability_df,
            allocations_df,
            scheduled_groups,
            priority_groups,
            rd_constraints_df=dance_groups_df
        )
        
        schedules[slot_name] = (scheduled_df, unable_df)
    
    return schedules


def save_schedules_with_unable(
    schedules: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]],
    output_dir: str
):
    """
    Save scheduled and unable-to-fit groups to CSV files.
    
    Creates two files per slot:
    - slot_X_schedule.csv - scheduled groups
    - slot_X_unable.csv - groups that couldn't fit
    
    Args:
        schedules: Dict of slot_name -> (scheduled_df, unable_df)
        output_dir: Output directory path
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for slot_name, (scheduled_df, unable_df) in schedules.items():
        # Save scheduled
        scheduled_file = os.path.join(output_dir, f"{slot_name}_schedule.csv")
        scheduled_df.to_csv(scheduled_file, index=False)
        
        # Save unable (if any)
        if not unable_df.empty:
            unable_file = os.path.join(output_dir, f"{slot_name}_unable.csv")
            unable_df.to_csv(unable_file, index=False)