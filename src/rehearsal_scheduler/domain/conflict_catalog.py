"""
Conflict Catalog Generator - Core Domain Logic

Generates a catalog showing which RDs and dancers are unavailable for each rehearsal slot.
Helps directors manually schedule dances by identifying constraints upfront.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass

from rehearsal_scheduler.grammar import constraint_parser
from rehearsal_scheduler.constraints import RehearsalSlot
from rehearsal_scheduler.reporting.constraint_formatter import format_constraint


@dataclass
class ConflictInfo:
    """Information about a single conflict."""
    entity_id: str  # rd_id or dancer_id
    full_name: str
    constraint_text: str
    reason: str


@dataclass
class SlotCatalogEntry:
    """Catalog entry for one rehearsal slot."""
    slot: RehearsalSlot
    venue_name: str
    rd_conflicts: List[ConflictInfo]
    dance_conflicts: Dict[str, List[ConflictInfo]]  # dance_id -> list of dancer conflicts


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
    
    # Parse times - handle both formats:
    # - Military time as int: 1800
    # - Formatted string: "6:00 PM" or "18:00"
    
    def parse_time(time_value) -> int:
        """Convert time to military format integer."""
        if isinstance(time_value, int):
            return time_value
        
        time_str = str(time_value).strip()
        
        # Try to parse as "H:MM AM/PM" format
        try:
            # Handle "11:00 AM" or "6:00 PM"
            dt = datetime.strptime(time_str, '%I:%M %p')
            return dt.hour * 100 + dt.minute
        except ValueError:
            pass
        
        # Try to parse as "HH:MM" (24-hour)
        try:
            dt = datetime.strptime(time_str, '%H:%M')
            return dt.hour * 100 + dt.minute
        except ValueError:
            pass
        
        # Try as plain integer
        try:
            return int(time_str)
        except ValueError:
            raise ValueError(f"Could not parse time: {time_value}")
    
    start_time = parse_time(row['start_time'])
    end_time = parse_time(row['end_time'])
    
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
        # Conflicts if same day of week
        return constraint.day_of_week == slot.day_of_week
    
    elif isinstance(constraint, TimeOnDayConstraint):
        # Conflicts if same day AND times overlap
        if constraint.day_of_week != slot.day_of_week:
            return False
        
        # Check time interval overlap: max(starts) < min(ends)
        overlap_start = max(constraint.start_time, slot.start_time)
        overlap_end = min(constraint.end_time, slot.end_time)
        
        return overlap_start < overlap_end
    
    elif isinstance(constraint, DateConstraint):
        # Conflicts if same date
        return constraint.date == slot.rehearsal_date
    
    elif isinstance(constraint, DateRangeConstraint):
        # Conflicts if slot date is within range (inclusive)
        return constraint.start_date <= slot.rehearsal_date <= constraint.end_date
    
    elif isinstance(constraint, TimeOnDateConstraint):
        # Conflicts if same date AND times overlap
        if constraint.date != slot.rehearsal_date:
            return False
        
        # Check time interval overlap
        overlap_start = max(constraint.start_time, slot.start_time)
        overlap_end = min(constraint.end_time, slot.end_time)
        
        return overlap_start < overlap_end
    
    else:
        # Unknown constraint type
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
            # Parse constraints
            parsed_constraints = parser.parse(constraint_text)
            
            # Check each constraint against the slot
            for constraint in parsed_constraints:
                if check_constraint_conflicts(constraint, slot):
                    conflicts.append(ConflictInfo(
                        entity_id=rd_id,
                        full_name=full_name,
                        constraint_text=constraint_text,
                        reason=format_constraint(constraint)  # Format for readability
                    ))
                    break  # Only report once per RD
        
        except Exception as e:
            # Parsing error - note it but continue
            conflicts.append(ConflictInfo(
                entity_id=rd_id,
                full_name=full_name,
                constraint_text=constraint_text,
                reason=f"ERROR parsing constraint: {e}"
            ))
    
    return conflicts


def find_conflicts_by_dance(
    slot: RehearsalSlot,
    dances_df: pd.DataFrame,
    dance_cast_df: pd.DataFrame,
    dancer_constraints_df: pd.DataFrame
) -> Dict[str, List[ConflictInfo]]:
    """
    For each dance, find which dancers have conflicts with this slot.
    
    Args:
        slot: Rehearsal slot to check
        dances_df: DataFrame with dance information (currently unused but available for dance names)
        dance_cast_df: Matrix DataFrame with dancer_ids as index, dance_ids as columns
        dancer_constraints_df: DataFrame with columns: dancer_id, full_name, constraints
        
    Returns:
        Dict mapping dance_id -> list of ConflictInfo for conflicted dancers
        Only includes dances that have at least one conflict
    """
    parser = constraint_parser()
    dance_conflicts = {}
    
    # For each dance
    for dance_id in dance_cast_df.columns:
        # Get dancers in this dance (where value is '1')
        dancers_in_dance = dance_cast_df[dance_cast_df[dance_id] == '1'].index.tolist()
        
        conflicts = []
        
        # Check each dancer's constraints
        for dancer_id in dancers_in_dance:
            # Get dancer info
            dancer_row = dancer_constraints_df[dancer_constraints_df['dancer_id'] == dancer_id]
            
            if dancer_row.empty:
                continue
            
            full_name = dancer_row.iloc[0]['full_name']
            constraint_text = dancer_row.iloc[0]['constraints'].strip()
            
            if not constraint_text:
                continue
            
            try:
                # Parse constraints
                parsed_constraints = parser.parse(constraint_text)
                
                # Check each constraint
                for constraint in parsed_constraints:
                    if check_constraint_conflicts(constraint, slot):
                        conflicts.append(ConflictInfo(
                            entity_id=dancer_id,
                            full_name=full_name,
                            constraint_text=constraint_text,
                            reason=format_constraint(constraint)  # Format for readability
                        ))
                        break  # Only report once per dancer
            
            except Exception as e:
                conflicts.append(ConflictInfo(
                    entity_id=dancer_id,
                    full_name=full_name,
                    constraint_text=constraint_text,
                    reason=f"ERROR: {e}"
                ))
        
        # Only include dances that have conflicts
        if conflicts:
            dance_conflicts[dance_id] = conflicts
    
    return dance_conflicts


def generate_conflict_catalog(data: Dict[str, pd.DataFrame]) -> List[SlotCatalogEntry]:
    """
    Generate complete conflict catalog for all rehearsal slots.
    
    Args:
        data: Dict of DataFrames with keys:
            - rehearsals: rehearsal schedule
            - rd_constraints: RD availability constraints
            - dancer_constraints: dancer availability constraints
            - dances: dance information
            - dance_cast: casting matrix
            
    Returns:
        List of SlotCatalogEntry, one per rehearsal slot
    """
    catalog = []
    
    for _, row in data['rehearsals'].iterrows():
        slot = parse_slot_from_row(row)
        
        entry = SlotCatalogEntry(
            slot=slot,
            venue_name=row.get('venue_name', 'Unknown'),
            rd_conflicts=find_conflicted_rds(slot, data['rd_constraints']),
            dance_conflicts=find_conflicts_by_dance(
                slot,
                data['dances'],
                data['dance_cast'],
                data['dancer_constraints']
            )
        )
        
        catalog.append(entry)
    
    return catalog