"""
Scheduling Catalog Generator - Core Domain Logic

Generates a catalog showing RD and dancer availability for rehearsal scheduling.
Uses dance_groups (with RD assignments) and group_cast (dancer assignments).

This is the scheduling-focused version that uses data from the Scheduling workbook.
"""

import pandas as pd
from datetime import datetime
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


def find_ineligible_groups(
    rd_conflicts: List[ConflictInfo],
    dance_groups_df: pd.DataFrame
) -> List[DanceGroupInfo]:
    """
    Find dance groups that cannot be scheduled due to RD conflicts.
    
    Args:
        rd_conflicts: List of RDs with conflicts
        dance_groups_df: DataFrame with columns: dg_id, dg_name, current_rd, current_rd_name
        
    Returns:
        List of DanceGroupInfo for groups whose RD is unavailable
    """
    # Get set of conflicted RD IDs
    conflicted_rd_ids = {conflict.entity_id for conflict in rd_conflicts}
    
    ineligible = []
    
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


def generate_scheduling_catalog(data: Dict[str, pd.DataFrame]) -> List[SchedulingSlotEntry]:
    """
    Generate complete scheduling catalog for all rehearsal slots.
    
    Args:
        data: Dict of DataFrames with keys:
            - rehearsals: rehearsal schedule
            - rd_constraints: RD availability constraints
            - dancer_constraints: dancer availability constraints
            - dance_groups: dance group info with RD assignments
            - group_cast: casting matrix (dancer_id × dg_id)
            
    Returns:
        List of SchedulingSlotEntry, one per rehearsal slot
    """
    catalog = []
    
    for _, row in data['rehearsals'].iterrows():
        slot = parse_slot_from_row(row)
        
        # Find RD conflicts
        rd_conflicts = find_conflicted_rds(slot, data['rd_constraints'])
        
        # Find dance groups that can't be scheduled (RD unavailable)
        ineligible_groups = find_ineligible_groups(rd_conflicts, data['dance_groups'])
        ineligible_group_ids = {group.dg_id for group in ineligible_groups}
        
        # Find dancer conflicts for eligible groups
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