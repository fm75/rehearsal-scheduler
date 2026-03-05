"""
Scheduling Catalog Generator - Core Domain Logic

Generates a catalog showing RD and dancer availability for rehearsal scheduling.
Uses dance_groups (with RD assignments) and group_cast (dancer assignments).

This is the scheduling-focused version that uses data from the Scheduling workbook.
"""

import pandas as pd
from datetime import datetime, time
from typing import Dict, List, Set
from dataclasses import dataclass

from rehearsal_scheduler.grammar import constraint_parser
from rehearsal_scheduler.constraints import RehearsalSlot
from rehearsal_scheduler.models.intervals import parse_time_to_military
from rehearsal_scheduler.reporting.constraint_formatter import format_constraint


@dataclass
class ConflictInfo:
    """Information about a single conflict."""
    entity_id: str  # rd_id or dancer_id
    full_name: str
    constraint_text: str
    reason: str


@dataclass
class DanceGroupInfo:
    """Information about a dance group."""
    dg_id: str
    dg_name: str
    rd_id: str
    rd_name: str


@dataclass
class SchedulingSlotEntry:
    """Catalog entry for one rehearsal slot."""
    slot: RehearsalSlot
    venue_name: str
    rd_conflicts: List[ConflictInfo]
    ineligible_groups: List[DanceGroupInfo]  # Groups whose RD is unavailable
    group_conflicts: Dict[str, List[ConflictInfo]]  # dg_id -> list of dancer conflicts


def parse_slot_from_row(row: pd.Series) -> RehearsalSlot:
    """
    Convert DataFrame row to RehearsalSlot.
    
    Expected columns: date, weekday, start_time, end_time
    
    Args:
        row: DataFrame row with rehearsal info
        
    Returns:
        RehearsalSlot object
    """
    # Parse date (format: m-d-yy like "1-15-26")
    date_str = row['date']
    rehearsal_date = datetime.strptime(date_str, '%m-%d-%y').date()
    
    weekday = row['weekday'].lower()
    
    # Parse times using shared utility function
    start_time = parse_time_to_military(row['start_time'])
    end_time = parse_time_to_military(row['end_time'])
    
    return RehearsalSlot(
        rehearsal_date=rehearsal_date,
        day_of_week=weekday,
        start_time=start_time,
        end_time=end_time
    )


def check_constraint_conflicts(constraint, slot: RehearsalSlot) -> bool:
    """
    Check if a constraint conflicts with a rehearsal slot.
    
    Args:
        constraint: Any constraint type
        slot: RehearsalSlot to check against
        
    Returns:
        True if there's a conflict, False otherwise
    """
    from rehearsal_scheduler.constraints import (
        DayOfWeekConstraint,
        TimeOnDayConstraint,
        DateConstraint,
        DateRangeConstraint,
        TimeOnDateConstraint
    )
    
    if isinstance(constraint, DayOfWeekConstraint):
        return constraint.day_of_week == slot.day_of_week
    
    elif isinstance(constraint, TimeOnDayConstraint):
        if constraint.day_of_week != slot.day_of_week:
            return False
        
        overlap_start = max(constraint.start_time, slot.start_time)
        overlap_end = min(constraint.end_time, slot.end_time)
        
        return overlap_start < overlap_end
    
    elif isinstance(constraint, DateConstraint):
        return constraint.date == slot.rehearsal_date
    
    elif isinstance(constraint, DateRangeConstraint):
        return constraint.start_date <= slot.rehearsal_date <= constraint.end_date
    
    elif isinstance(constraint, TimeOnDateConstraint):
        if constraint.date != slot.rehearsal_date:
            return False
        
        overlap_start = max(constraint.start_time, slot.start_time)
        overlap_end = min(constraint.end_time, slot.end_time)
        
        return overlap_start < overlap_end
    
    else:
        return False


def find_conflicted_rds(slot: RehearsalSlot, rd_constraints_df: pd.DataFrame) -> List[ConflictInfo]:
    """
    Find which RDs have constraints that conflict with this slot.
    
    Args:
        slot: Rehearsal slot to check
        rd_constraints_df: DataFrame with columns: rd_id, full_name, constraints
        
    Returns:
        List of ConflictInfo for each conflicted RD
    """
    parser = constraint_parser()
    conflicts = []
    
    for _, row in rd_constraints_df.iterrows():
        rd_id = row['rd_id']
        full_name = row['full_name']
        constraint_text = row['constraints'].strip()
        
        if not constraint_text:
            continue
        
        try:
            parsed_constraints = parser.parse(constraint_text)
            
            for constraint in parsed_constraints:
                if check_constraint_conflicts(constraint, slot):
                    conflicts.append(ConflictInfo(
                        entity_id=rd_id,
                        full_name=full_name,
                        constraint_text=constraint_text,
                        reason=format_constraint(constraint)
                    ))
                    break
        
        except Exception as e:
            conflicts.append(ConflictInfo(
                entity_id=rd_id,
                full_name=full_name,
                constraint_text=constraint_text,
                reason=f"ERROR parsing constraint: {e}"
            ))
    
    return conflicts


def find_rd_availability(slot: RehearsalSlot, rd_constraints_df: pd.DataFrame) -> List[ConflictInfo]:
    """
    Find RD availability windows within this slot.
    
    Only shows RDs with constraints (partial or zero availability).
    RDs with full availability are omitted.
    
    Args:
        slot: Rehearsal slot to check
        rd_constraints_df: DataFrame with columns: rd_id, full_name, constraints
        
    Returns:
        List of ConflictInfo with availability windows for RDs with constraints
    """
    from rehearsal_scheduler.models.intervals import TimeInterval
    from rehearsal_scheduler.models.interval_operations import subtract_intervals
    from datetime import time
    
    parser = constraint_parser()
    availability_list = []
    
    # Convert slot to TimeInterval
    slot_interval = TimeInterval(
        time(slot.start_time // 100, slot.start_time % 100),
        time(slot.end_time // 100, slot.end_time % 100)
    )
    
    for _, row in rd_constraints_df.iterrows():
        rd_id = row['rd_id']
        full_name = row['full_name']
        constraint_text = row['constraints'].strip()
        
        if not constraint_text:
            # No constraints = full availability = don't show
            continue
        
        try:
            # Parse constraints and convert to unavailable intervals
            parsed_constraints = parser.parse(constraint_text)
            
            unavailable_intervals = []
            for constraint in parsed_constraints:
                if check_constraint_conflicts(constraint, slot):
                    # This constraint affects this slot
                    constraint_intervals = constraint_to_intervals(constraint, slot)
                    unavailable_intervals.extend(constraint_intervals)
            
            if not unavailable_intervals:
                # No conflicts = full availability = don't show
                continue
            
            # Calculate available windows
            available_windows = subtract_intervals(slot_interval, unavailable_intervals)
            
            if not available_windows:
                # Zero availability - MUST show this
                availability_list.append(ConflictInfo(
                    entity_id=rd_id,
                    full_name=full_name,
                    constraint_text=constraint_text,
                    reason="❌ Unavailable (conflicts entire slot)"
                ))
            else:
                # Partial availability - show windows
                windows_str = ", ".join([
                    f"{format_time_interval(w)}"
                    for w in available_windows
                ])
                availability_list.append(ConflictInfo(
                    entity_id=rd_id,
                    full_name=full_name,
                    constraint_text=constraint_text,
                    reason=f"Available {windows_str}"
                ))
        
        except Exception as e:
            # Parse error
            availability_list.append(ConflictInfo(
                entity_id=rd_id,
                full_name=full_name,
                constraint_text=constraint_text,
                reason=f"ERROR: {e}"
            ))
    
    return availability_list


def find_ineligible_groups(
    rd_conflicts: List[ConflictInfo],
    dance_groups_df: pd.DataFrame,
    slot_interval=None,
    slot: RehearsalSlot = None,
    rd_constraints_df: pd.DataFrame = None
) -> List[DanceGroupInfo]:
    """
    Find dance groups that cannot be scheduled due to RD having ZERO availability.
    
    Note: If RD has partial availability, group is NOT ineligible - can schedule
    in the available window.
    
    Args:
        rd_conflicts: List of RDs with conflicts (kept for backward compatibility)
        dance_groups_df: DataFrame with columns: dg_id, dg_name, current_rd, current_rd_name
        slot_interval: TimeInterval for the slot (optional, for new behavior)
        slot: RehearsalSlot (optional, for new behavior)
        rd_constraints_df: RD constraints (optional, for new behavior)
        
    Returns:
        List of DanceGroupInfo for groups whose RD has NO availability this slot
    """
    from rehearsal_scheduler.models.interval_operations import subtract_intervals
    
    ineligible = []
    
    # New behavior: Check actual RD availability
    if slot_interval is not None and slot is not None and rd_constraints_df is not None:
        parser = constraint_parser()
        
        for _, row in dance_groups_df.iterrows():
            rd_id = row['current_rd']
            
            if not rd_id:
                continue
            
            # Check RD constraints directly
            rd_row = rd_constraints_df[rd_constraints_df['rd_id'] == rd_id]
            
            if rd_row.empty or not rd_row.iloc[0]['constraints'].strip():
                # RD has no constraints = fully available
                continue
            
            # RD has constraints - check if any availability exists
            try:
                parsed_constraints = parser.parse(rd_row.iloc[0]['constraints'].strip())
                
                unavailable_intervals = []
                for constraint in parsed_constraints:
                    if check_constraint_conflicts(constraint, slot):
                        constraint_intervals = constraint_to_intervals(constraint, slot)
                        unavailable_intervals.extend(constraint_intervals)
                
                if unavailable_intervals:
                    rd_available = subtract_intervals(slot_interval, unavailable_intervals)
                    
                    if not rd_available:
                        # RD has ZERO availability this slot
                        ineligible.append(DanceGroupInfo(
                            dg_id=row['dg_id'],
                            dg_name=row['dg_name'],
                            rd_id=rd_id,
                            rd_name=row['current_rd_name']
                        ))
            except:
                # Parse error - treat as unavailable
                ineligible.append(DanceGroupInfo(
                    dg_id=row['dg_id'],
                    dg_name=row['dg_name'],
                    rd_id=rd_id,
                    rd_name=row['current_rd_name']
                ))
    
    else:
        # Old behavior: Any conflict makes group ineligible
        conflicted_rd_ids = {conflict.entity_id for conflict in rd_conflicts}
        
        for _, row in dance_groups_df.iterrows():
            rd_id = row['current_rd']
            
            if rd_id in conflicted_rd_ids:
                ineligible.append(DanceGroupInfo(
                    dg_id=row['dg_id'],
                    dg_name=row['dg_name'],
                    rd_id=rd_id,
                    rd_name=row['current_rd_name']
                ))
    
    return ineligible


def find_conflicts_by_group(
    slot: RehearsalSlot,
    dance_groups_df: pd.DataFrame,
    group_cast_df: pd.DataFrame,
    dancer_constraints_df: pd.DataFrame,
    ineligible_group_ids: Set[str]
) -> Dict[str, List[ConflictInfo]]:
    """
    For each dance group, find which dancers have conflicts with this slot.
    
    Args:
        slot: Rehearsal slot to check
        dance_groups_df: DataFrame with dance group info
        group_cast_df: Matrix DataFrame with dancer_ids as index, dg_ids as columns
        dancer_constraints_df: DataFrame with columns: dancer_id, full_name, constraints
        ineligible_group_ids: Set of dg_ids to skip (RD unavailable)
        
    Returns:
        Dict mapping dg_id -> list of ConflictInfo for conflicted dancers
        Only includes groups that are eligible (RD available) and have conflicts
    """
    parser = constraint_parser()
    group_conflicts = {}
    
    # For each dance group
    for dg_id in group_cast_df.columns:
        # Skip if RD is unavailable
        if dg_id in ineligible_group_ids:
            continue
        
        # Get dancers in this group (where value is '1')
        dancers_in_group = group_cast_df[group_cast_df[dg_id] == '1'].index.tolist()
        
        conflicts = []
        
        # Check each dancer's constraints
        for dancer_id in dancers_in_group:
            dancer_row = dancer_constraints_df[dancer_constraints_df['dancer_id'] == dancer_id]
            
            if dancer_row.empty:
                continue
            
            full_name = dancer_row.iloc[0]['full_name']
            constraint_text = dancer_row.iloc[0]['constraints'].strip()
            
            if not constraint_text:
                continue
            
            try:
                parsed_constraints = parser.parse(constraint_text)
                
                for constraint in parsed_constraints:
                    if check_constraint_conflicts(constraint, slot):
                        conflicts.append(ConflictInfo(
                            entity_id=dancer_id,
                            full_name=full_name,
                            constraint_text=constraint_text,
                            reason=format_constraint(constraint)
                        ))
                        break
            
            except Exception as e:
                conflicts.append(ConflictInfo(
                    entity_id=dancer_id,
                    full_name=full_name,
                    constraint_text=constraint_text,
                    reason=f"ERROR: {e}"
                ))
        
        # Only include groups that have conflicts
        if conflicts:
            group_conflicts[dg_id] = conflicts
    
    return group_conflicts


def find_availability_by_group(
    slot: RehearsalSlot,
    dance_groups_df: pd.DataFrame,
    group_cast_df: pd.DataFrame,
    dancer_constraints_df: pd.DataFrame,
    ineligible_group_ids: Set[str],
    calculate_full_availability: bool = False,
    rd_constraints_df: pd.DataFrame = None
) -> Dict[str, tuple]:
    """
    For each dance group, calculate dancer availability windows within the slot.
    
    Only shows dancers with constraints (partial or zero availability).
    Dancers with full availability are omitted.
    
    Args:
        slot: Rehearsal slot to check
        dance_groups_df: DataFrame with dance group info
        group_cast_df: Matrix DataFrame with dancer_ids as index, dg_ids as columns
        dancer_constraints_df: DataFrame with columns: dancer_id, full_name, constraints
        ineligible_group_ids: Set of dg_ids to skip (RD unavailable)
        calculate_full_availability: If True, calculate 100% availability window
        
    Returns:
        Dict mapping dg_id -> (list of ConflictInfo, full_availability_str)
        Only includes dancers with partial or zero availability
    """
    from rehearsal_scheduler.models.intervals import TimeInterval
    from rehearsal_scheduler.models.interval_operations import subtract_intervals
    
    parser = constraint_parser()
    group_availability = {}
    
    # Convert slot to TimeInterval
    slot_interval = TimeInterval(
        time(slot.start_time // 100, slot.start_time % 100),
        time(slot.end_time // 100, slot.end_time % 100)
    )
    
    # For each dance group
    for dg_id in group_cast_df.columns:
        # Skip if RD is unavailable
        if dg_id in ineligible_group_ids:
            continue
        
        # Get dancers in this group
        dancers_in_group = group_cast_df[group_cast_df[dg_id] == '1'].index.tolist()
        
        availability_info = []
        
        # Calculate availability for each dancer
        for dancer_id in dancers_in_group:
            dancer_row = dancer_constraints_df[dancer_constraints_df['dancer_id'] == dancer_id]
            
            if dancer_row.empty:
                # No constraints = full availability = don't show
                continue
            
            full_name = dancer_row.iloc[0]['full_name']
            constraint_text = dancer_row.iloc[0]['constraints'].strip()
            
            if not constraint_text:
                # No constraints = full availability = don't show
                continue
            
            try:
                # Parse constraints and convert to unavailable intervals
                parsed_constraints = parser.parse(constraint_text)
                
                unavailable_intervals = []
                for constraint in parsed_constraints:
                    if check_constraint_conflicts(constraint, slot):
                        # This constraint affects this slot
                        # Convert constraint to TimeInterval(s)
                        constraint_intervals = constraint_to_intervals(constraint, slot)
                        unavailable_intervals.extend(constraint_intervals)
                
                if not unavailable_intervals:
                    # No conflicts = full availability = don't show
                    continue
                
                # Calculate available windows
                available_windows = subtract_intervals(slot_interval, unavailable_intervals)
                
                if not available_windows:
                    # Zero availability - MUST show this
                    availability_info.append(ConflictInfo(
                        entity_id=dancer_id,
                        full_name=full_name,
                        constraint_text=constraint_text,
                        reason="❌ Unavailable (conflicts entire slot)"
                    ))
                else:
                    # Partial availability - show windows
                    windows_str = ", ".join([
                        f"{format_time_interval(w)}"
                        for w in available_windows
                    ])
                    availability_info.append(ConflictInfo(
                        entity_id=dancer_id,
                        full_name=full_name,
                        constraint_text=constraint_text,
                        reason=f"Available {windows_str}"
                    ))
            
            except Exception as e:
                # Parse error
                availability_info.append(ConflictInfo(
                    entity_id=dancer_id,
                    full_name=full_name,
                    constraint_text=constraint_text,
                    reason=f"ERROR: {e}"
                ))
        
        # Calculate 100% availability if requested
        full_availability_str = None
        if calculate_full_availability:
            rd_id=dance_groups_df[dance_groups_df['dg_id'] == dg_id].iloc[0]['current_rd'] if not dance_groups_df.empty else None
            rd_avail, dancer_avail, combined_avail = calculate_full_availability_for_group(
                dg_id,
                slot_interval,
                group_cast_df,
                dancer_constraints_df,
                slot,
                rd_id=rd_id,
                rd_constraints_df=rd_constraints_df  # Or pass actual rd_constraints if available
            )
            
            # For the tuple return, use combined_avail (RD + all dancers)
            full_availability_str = combined_avail

        # Only include groups with dancers that have constraints OR if calculating full availability
        if availability_info or calculate_full_availability:
            if calculate_full_availability:
                group_availability[dg_id] = (availability_info, full_availability_str)
            else:
                group_availability[dg_id] = availability_info
    
    return group_availability


def constraint_to_intervals(constraint, slot: RehearsalSlot) -> List:
    """
    Convert a constraint that conflicts with a slot into TimeInterval(s).
    
    Returns list of unavailable time intervals within the slot.
    """
    from rehearsal_scheduler.constraints import (
        DayOfWeekConstraint,
        TimeOnDayConstraint,
        DateConstraint,
        DateRangeConstraint,
        TimeOnDateConstraint
    )
    from rehearsal_scheduler.models.intervals import TimeInterval
    
    if isinstance(constraint, DayOfWeekConstraint):
        # Entire day unavailable = entire slot unavailable
        return [TimeInterval(
            time(slot.start_time // 100, slot.start_time % 100),
            time(slot.end_time // 100, slot.end_time % 100)
        )]
    
    elif isinstance(constraint, TimeOnDayConstraint):
        # Time range on this day - intersect with slot
        constraint_start = max(constraint.start_time, slot.start_time)
        constraint_end = min(constraint.end_time, slot.end_time)
        
        if constraint_start < constraint_end:
            return [TimeInterval(
                time(constraint_start // 100, constraint_start % 100),
                time(constraint_end // 100, constraint_end % 100)
            )]
        return []
    
    elif isinstance(constraint, (DateConstraint, DateRangeConstraint)):
        # Entire date unavailable = entire slot unavailable
        return [TimeInterval(
            time(slot.start_time // 100, slot.start_time % 100),
            time(slot.end_time // 100, slot.end_time % 100)
        )]
    
    elif isinstance(constraint, TimeOnDateConstraint):
        # Time range on this date - intersect with slot
        constraint_start = max(constraint.start_time, slot.start_time)
        constraint_end = min(constraint.end_time, slot.end_time)
        
        if constraint_start < constraint_end:
            return [TimeInterval(
                time(constraint_start // 100, constraint_start % 100),
                time(constraint_end // 100, constraint_end % 100)
            )]
        return []
    
    return []


def format_time_interval(interval) -> str:
    """Format TimeInterval as human-readable string."""
    from rehearsal_scheduler.reporting.constraint_formatter import format_time
    
    start_str = format_time(interval.start.hour * 100 + interval.start.minute)
    end_str = format_time(interval.end.hour * 100 + interval.end.minute)
    
    return f"{start_str} - {end_str}"


def calculate_full_availability_for_group(
    dg_id: str,
    slot_interval,
    group_cast_df: pd.DataFrame,
    dancer_constraints_df: pd.DataFrame,
    slot: RehearsalSlot,
    rd_id: str = None,
    rd_constraints_df: pd.DataFrame = None
) -> tuple:
    """
    Calculate availability windows for a dance group.
    
    Returns three availability measures:
    1. RD availability - when the assigned RD is available
    2. Dancer 100% availability - when all dancers are available
    3. Combined 100% availability - when RD AND all dancers are available
    
    Args:
        dg_id: Dance group ID
        slot_interval: TimeInterval for the rehearsal slot
        group_cast_df: Casting matrix
        dancer_constraints_df: Dancer constraints
        slot: RehearsalSlot for constraint checking
        rd_id: Assigned RD ID (optional)
        rd_constraints_df: RD constraints (optional)
        
    Returns:
        Tuple of (rd_availability_str, dancer_availability_str, combined_availability_str)
    """
    from rehearsal_scheduler.models.interval_operations import intersect_intervals, union_intervals, subtract_intervals
    from rehearsal_scheduler.models.intervals import TimeInterval
    
    parser = constraint_parser()
    
    # Get dancers in this group
    dancers_in_group = group_cast_df[group_cast_df[dg_id] == '1'].index.tolist()
    
    if not dancers_in_group:
        return ("No dancers", "No dancers", "No dancers")
    
    # ========================================================================
    # STEP 1: Calculate Dancer 100% Availability
    # ========================================================================
    dancer_common_availability = [slot_interval]
    
    for dancer_id in dancers_in_group:
        dancer_row = dancer_constraints_df[dancer_constraints_df['dancer_id'] == dancer_id]
        
        if dancer_row.empty:
            continue
        
        constraint_text = dancer_row.iloc[0]['constraints'].strip()
        
        if not constraint_text:
            continue
        
        try:
            parsed_constraints = parser.parse(constraint_text)
            
            unavailable_intervals = []
            for constraint in parsed_constraints:
                if check_constraint_conflicts(constraint, slot):
                    constraint_intervals = constraint_to_intervals(constraint, slot)
                    unavailable_intervals.extend(constraint_intervals)
            
            if not unavailable_intervals:
                continue
            
            dancer_availability = subtract_intervals(slot_interval, unavailable_intervals)
            
            if not dancer_availability:
                dancer_common_availability = []
                break
            
            # Intersect with common
            new_common = []
            for common_window in dancer_common_availability:
                for dancer_window in dancer_availability:
                    intersection = intersect_intervals(common_window, dancer_window)
                    new_common.extend(intersection)
            
            dancer_common_availability = new_common
            
            if not dancer_common_availability:
                break
        
        except Exception:
            dancer_common_availability = []
            break
    
    # Format dancer availability
    if not dancer_common_availability:
        dancer_avail_str = "None"
        dancer_merged = []
    else:
        dancer_merged = union_intervals(dancer_common_availability)
        if not dancer_merged:
            dancer_avail_str = "None"
        else:
            dancer_avail_str = ", ".join([format_time_interval(w) for w in dancer_merged])
    
    # ========================================================================
    # STEP 2: Calculate RD Availability
    # ========================================================================
    if rd_id and rd_constraints_df is not None:
        rd_row = rd_constraints_df[rd_constraints_df['rd_id'] == rd_id]
        
        if rd_row.empty or not rd_row.iloc[0]['constraints'].strip():
            # No constraints = fully available
            rd_avail_str = format_time_interval(slot_interval)
            rd_available_intervals = [slot_interval]
        else:
            constraint_text = rd_row.iloc[0]['constraints'].strip()
            
            try:
                parsed_constraints = parser.parse(constraint_text)
                
                unavailable_intervals = []
                for constraint in parsed_constraints:
                    if check_constraint_conflicts(constraint, slot):
                        constraint_intervals = constraint_to_intervals(constraint, slot)
                        unavailable_intervals.extend(constraint_intervals)
                
                if not unavailable_intervals:
                    # No conflicts = fully available
                    rd_avail_str = format_time_interval(slot_interval)
                    rd_available_intervals = [slot_interval]
                else:
                    rd_available_intervals = subtract_intervals(slot_interval, unavailable_intervals)
                    
                    if not rd_available_intervals:
                        rd_avail_str = "None"
                    else:
                        rd_merged = union_intervals(rd_available_intervals)
                        rd_avail_str = ", ".join([format_time_interval(w) for w in rd_merged])
                        rd_available_intervals = rd_merged
            
            except Exception:
                rd_avail_str = "None"
                rd_available_intervals = []
    else:
        # No RD info provided = assume fully available
        rd_avail_str = format_time_interval(slot_interval)
        rd_available_intervals = [slot_interval]
    
    # ========================================================================
    # STEP 3: Calculate Combined Availability (RD AND all dancers)
    # ========================================================================
    if rd_avail_str == "None" or dancer_avail_str == "None":
        combined_avail_str = "None"
    else:
        # Intersect RD availability with dancer availability
        combined_intervals = []
        
        # Intersect each RD window with each dancer window
        for rd_window in rd_available_intervals:
            for dancer_window in dancer_merged:
                intersection = intersect_intervals(rd_window, dancer_window)
                combined_intervals.extend(intersection)
        
        if not combined_intervals:
            combined_avail_str = "None"
        else:
            combined_merged = union_intervals(combined_intervals)
            if not combined_merged:
                combined_avail_str = "None"
            else:
                combined_avail_str = ", ".join([format_time_interval(w) for w in combined_merged])
    
    return (rd_avail_str, dancer_avail_str, combined_avail_str)


def generate_scheduling_catalog(
    data: Dict[str, pd.DataFrame],
    show_availability: bool = False
) -> List[SchedulingSlotEntry]:
    """
    Generate complete scheduling catalog for all rehearsal slots.
    
    Args:
        data: Dict of DataFrames with keys:
            - rehearsals: rehearsal schedule
            - rd_constraints: RD availability constraints
            - dancer_constraints: dancer availability constraints
            - dance_groups: dance group info with RD assignments
            - group_cast: casting matrix (dancer_id × dg_id)
        show_availability: If True, calculate and show availability windows instead of conflicts
            
    Returns:
        List of SchedulingSlotEntry, one per rehearsal slot
    """
    catalog = []
    
    for _, row in data['rehearsals'].iterrows():
        slot = parse_slot_from_row(row)
        
        # Create slot interval for availability calculations
        from rehearsal_scheduler.models.intervals import TimeInterval
        slot_interval = TimeInterval(
            time(slot.start_time // 100, slot.start_time % 100),
            time(slot.end_time // 100, slot.end_time % 100)
        )
        
        # Find RD conflicts or availability
        if show_availability:
            rd_conflicts = find_rd_availability(slot, data['rd_constraints'])
        else:
            rd_conflicts = find_conflicted_rds(slot, data['rd_constraints'])
        
        # Find dance groups that can't be scheduled (RD has ZERO availability)
        ineligible_groups = find_ineligible_groups(
            rd_conflicts, 
            data['dance_groups'],
            slot_interval=slot_interval,
            slot=slot,
            rd_constraints_df=data['rd_constraints']
        )
        ineligible_group_ids = {group.dg_id for group in ineligible_groups}
        
        # Find dancer conflicts or availability for eligible groups
        if show_availability:
            group_conflicts = find_availability_by_group(
                slot,
                data['dance_groups'],
                data['group_cast'],
                data['dancer_constraints'],
                ineligible_group_ids,
                calculate_full_availability=True,
                rd_constraints_df=data['rd_constraints']
            )
        else:
            group_conflicts = find_conflicts_by_group(
                slot,
                data['dance_groups'],
                data['group_cast'],
                data['dancer_constraints'],
                ineligible_group_ids
            )
        
        entry = SchedulingSlotEntry(
            slot=slot,
            venue_name=row.get('venue_name', 'Unknown'),
            rd_conflicts=rd_conflicts,
            ineligible_groups=ineligible_groups,
            group_conflicts=group_conflicts
        )
        
        catalog.append(entry)
    
    return catalog