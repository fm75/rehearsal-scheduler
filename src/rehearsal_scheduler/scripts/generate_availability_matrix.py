#!/usr/bin/env python3
"""
Availability Matrix Generator

Generates a CSV matrix showing dance group availability across all rehearsal slots.
Includes priority and participation scores for ranking/sorting.

Output columns:
- dance_group: Name of the dance group
- priority: Availability score (0-1, higher = more available)
- participation: Dancer participation score (0-1, higher = better coverage)
- slot_N: 100% availability window(s) for each rehearsal slot

Usage:
    # Default config
    python -m rehearsal_scheduler.scripts.generate_availability_matrix
    
    # Custom output
    python -m rehearsal_scheduler.scripts.generate_availability_matrix --output my_matrix.csv
    
    # Custom config
    python -m rehearsal_scheduler.scripts.generate_availability_matrix --config custom.yaml
"""

import sys
import click
import pandas as pd
from datetime import time
from typing import Dict

from rehearsal_scheduler.persistence.data_loader import SchedulingDataLoader
from rehearsal_scheduler.domain.scheduling_catalog import (
    parse_slot_from_row,
    find_conflicted_rds,
    find_ineligible_groups,
    calculate_full_availability_for_group,
    check_constraint_conflicts,
    constraint_to_intervals
)
from rehearsal_scheduler.grammar import constraint_parser
from rehearsal_scheduler.models.intervals import TimeInterval
from rehearsal_scheduler.models.interval_operations import subtract_intervals


def calculate_priority_score(
    dg_id: str,
    full_availability_by_slot: dict,
    total_slot_minutes: int
) -> float:
    """
    Calculate priority score (0-1) based on total 100% available time.
    
    Priority = sum(100% available minutes) / sum(slot minutes)
    
    Args:
        dg_id: Dance group ID
        full_availability_by_slot: Dict of slot_name -> list of TimeIntervals
        total_slot_minutes: Total minutes across all slots
        
    Returns:
        Priority score 0.0 (impossible) to 1.0 (unconstrained)
    """
    if total_slot_minutes == 0:
        return 0.0
    
    total_available_minutes = 0
    
    for intervals in full_availability_by_slot.values():
        if intervals and intervals != "None":
            for interval in intervals:
                duration = (interval.end.hour * 60 + interval.end.minute) - \
                          (interval.start.hour * 60 + interval.start.minute)
                total_available_minutes += duration
    
    return min(1.0, total_available_minutes / total_slot_minutes)


def calculate_participation_score(
    dg_id: str,
    group_cast_df: pd.DataFrame,
    dancer_constraints_df: pd.DataFrame,
    rehearsal_slots: list,
    total_slot_minutes: int
) -> float:
    """
    Calculate participation score (0-1) based on individual dancer availability.
    
    Participation = sum(dancer available minutes) / (num_dancers × slot minutes)
    
    Args:
        dg_id: Dance group ID
        group_cast_df: Casting matrix
        dancer_constraints_df: Dancer constraints
        rehearsal_slots: List of RehearsalSlot objects
        total_slot_minutes: Total minutes across all slots
        
    Returns:
        Participation score 0.0 to 1.0
    """
    parser = constraint_parser()
    
    # Get dancers in this group
    dancers_in_group = group_cast_df[group_cast_df[dg_id] == '1'].index.tolist()
    
    if not dancers_in_group or total_slot_minutes == 0:
        return 0.0
    
    total_dancer_available_minutes = 0
    
    # For each dancer, calculate their total availability across all slots
    for dancer_id in dancers_in_group:
        dancer_row = dancer_constraints_df[dancer_constraints_df['dancer_id'] == dancer_id]
        
        if dancer_row.empty:
            # No constraints = fully available
            total_dancer_available_minutes += total_slot_minutes
            continue
        
        constraint_text = dancer_row.iloc[0]['constraints'].strip()
        
        if not constraint_text:
            # No constraints = fully available
            total_dancer_available_minutes += total_slot_minutes
            continue
        
        # Calculate availability for this dancer across all slots
        for slot in rehearsal_slots:
            slot_interval = TimeInterval(
                time(slot.start_time // 100, slot.start_time % 100),
                time(slot.end_time // 100, slot.end_time % 100)
            )
            
            try:
                parsed_constraints = parser.parse(constraint_text)
                
                unavailable_intervals = []
                for constraint in parsed_constraints:
                    if check_constraint_conflicts(constraint, slot):
                        constraint_intervals = constraint_to_intervals(constraint, slot)
                        unavailable_intervals.extend(constraint_intervals)
                
                # Calculate available time for this slot
                available_windows = subtract_intervals(slot_interval, unavailable_intervals)
                
                for window in available_windows:
                    duration = (window.end.hour * 60 + window.end.minute) - \
                              (window.start.hour * 60 + window.start.minute)
                    total_dancer_available_minutes += duration
            
            except Exception:
                # Parse error - treat as unavailable
                pass
    
    max_possible_minutes = len(dancers_in_group) * total_slot_minutes
    
    return min(1.0, total_dancer_available_minutes / max_possible_minutes)


def format_intervals_for_csv(intervals) -> str:
    """
    Format list of TimeIntervals as comma-separated string.
    
    Args:
        intervals: List of TimeInterval objects or "None"
        
    Returns:
        Formatted string like "7:00 pm - 8:30 pm, 9:00 pm - 9:30 pm" or ""
    """
    from rehearsal_scheduler.reporting.constraint_formatter import format_time
    
    if not intervals or intervals == "None":
        return ""
    
    formatted = []
    for interval in intervals:
        start_str = format_time(interval.start.hour * 100 + interval.start.minute)
        end_str = format_time(interval.end.hour * 100 + interval.end.minute)
        formatted.append(f"{start_str} - {end_str}")
    
    return ", ".join(formatted)


def get_full_availability_intervals(
    dg_id: str,
    slot_interval,
    group_cast_df: pd.DataFrame,
    dancer_constraints_df: pd.DataFrame,
    slot
) -> list:
    """
    Get 100% availability as list of TimeInterval objects (not formatted strings).
    
    This duplicates logic from calculate_full_availability_for_group but returns
    actual TimeInterval objects for scoring.
    
    Returns:
        List of TimeInterval objects where 100% of dancers are available
    """
    from rehearsal_scheduler.models.interval_operations import intersect_intervals, union_intervals
    
    parser = constraint_parser()
    
    dancers_in_group = group_cast_df[group_cast_df[dg_id] == '1'].index.tolist()
    
    if not dancers_in_group:
        return []
    
    # Start with full slot
    common_availability = [slot_interval]
    
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
                return []
            
            # Intersect with common
            new_common = []
            for common_window in common_availability:
                for dancer_window in dancer_availability:
                    intersection = intersect_intervals(common_window, dancer_window)
                    new_common.extend(intersection)
            
            common_availability = new_common
            
            if not common_availability:
                return []
        
        except Exception:
            return []
    
    if not common_availability:
        return []
    
    # Merge and return
    merged = union_intervals(common_availability)
    return merged if merged else []


def generate_availability_matrix(data: Dict[str, pd.DataFrame], verbose: bool = False) -> pd.DataFrame:
    """
    Generate availability matrix CSV.
    
    Args:
        data: Dict of DataFrames from data loader
        verbose: Show detailed progress
        
    Returns:
        DataFrame with columns: dance_group, priority, participation, slot_1_rd, slot_1_dancers, slot_1_combined, ...
    """
    from rehearsal_scheduler.models.interval_operations import union_intervals
    
    # Parse all rehearsal slots
    rehearsal_slots = []
    slot_names = []
    total_slot_minutes = 0
    
    for _, row in data['rehearsals'].iterrows():
        slot = parse_slot_from_row(row)
        rehearsal_slots.append(slot)
        
        # Create slot name
        slot_name = f"{slot.day_of_week.title()} {slot.rehearsal_date.strftime('%m/%d/%y')}"
        slot_names.append(slot_name)
        
        # Track total minutes
        duration = slot.end_time - slot.start_time
        hours = duration // 100
        minutes = duration % 100
        total_slot_minutes += hours * 60 + minutes
    
    # Get RD conflicts for each slot
    rd_conflicts_by_slot = []
    ineligible_by_slot = []
    
    # for slot in rehearsal_slots:
    #     rd_conflicts = find_conflicted_rds(slot, data['rd_constraints'])
    #     ineligible_groups = find_ineligible_groups(rd_conflicts, data['dance_groups'])
    #     rd_conflicts_by_slot.append(rd_conflicts)
    #     ineligible_by_slot.append({g.dg_id for g in ineligible_groups})

    for i, slot in enumerate(rehearsal_slots):
        slot_interval = TimeInterval(
            time(slot.start_time // 100, slot.start_time % 100),
            time(slot.end_time // 100, slot.end_time % 100)
        )
    
        rd_conflicts = find_conflicted_rds(slot, data['rd_constraints'])
        ineligible_groups = find_ineligible_groups(
            rd_conflicts, 
            data['dance_groups'],
            slot_interval=slot_interval,
            slot=slot,
            rd_constraints_df=data['rd_constraints']
        )
        rd_conflicts_by_slot.append(rd_conflicts)
        ineligible_by_slot.append({g.dg_id for g in ineligible_groups})

    # Build matrix data
    matrix_rows = []
    
    for _, group_row in data['dance_groups'].iterrows():
        dg_id = group_row['dg_id']
        dg_name = group_row['dg_name']
        
        # Calculate 100% availability for each slot
        full_availability_by_slot = {}
        full_availability_intervals = {}  # Store actual intervals for priority calc
        
        for i, slot in enumerate(rehearsal_slots):
            slot_interval = TimeInterval(
                time(slot.start_time // 100, slot.start_time % 100),
                time(slot.end_time // 100, slot.end_time % 100)
            )
            
            # Skip if RD unavailable
            if dg_id in ineligible_by_slot[i]:
                full_availability_by_slot[slot_names[i]] = {
                    'rd': "",
                    'dancers': "",
                    'combined': ""
                }
                full_availability_intervals[slot_names[i]] = []
                continue
            
            # Get RD info for this group
            rd_id = group_row['current_rd']
            
            if verbose:
                click.echo(f"  Processing {dg_name}: RD={rd_id} for {slot_names[i]}")
                # DEBUG: Check if RD exists in constraints
                if rd_id and 'rd_constraints' in data:
                    rd_exists = rd_id in data['rd_constraints']['rd_id'].values
                    click.echo(f"    RD {rd_id} exists in rd_constraints: {rd_exists}")
                    if rd_exists:
                        rd_constraint = data['rd_constraints'][data['rd_constraints']['rd_id'] == rd_id]['constraints'].iloc[0]
                        click.echo(f"    RD constraint: {rd_constraint}")
            
            # Calculate three availability measures (returns tuple)
            try:
                rd_avail, dancer_avail, combined_avail = calculate_full_availability_for_group(
                    dg_id,
                    slot_interval,
                    data['group_cast'],
                    data['dancer_constraints'],
                    slot,
                    rd_id=rd_id,
                    rd_constraints_df=data['rd_constraints']
                )
                
                if verbose and (not rd_avail or rd_avail == "None"):
                    click.echo(f"    WARNING: {dg_name} has no RD availability in {slot_names[i]}")

            except Exception as e:
                click.echo(f"    ERROR calculating availability for {dg_name}: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()
                rd_avail = ""
                dancer_avail = ""
                combined_avail = ""
            
            # Store all three
            full_availability_by_slot[slot_names[i]] = {
                'rd': rd_avail if rd_avail != "None" else "",
                'dancers': dancer_avail if dancer_avail != "None" else "",
                'combined': combined_avail if combined_avail != "None" else ""
            }
            
            # Store intervals for priority calculation (use RD availability, not combined)
            # Priority should be based on when RD can make it, not when all dancers can
            from rehearsal_scheduler.models.interval_parsing import parse_availability_string
            try:
                rd_intervals = parse_availability_string(rd_avail) if rd_avail != "None" else []
            except:
                rd_intervals = []
            full_availability_intervals[slot_names[i]] = rd_intervals
        
        # Calculate scores using actual intervals
        priority = calculate_priority_score(
            dg_id,
            full_availability_intervals,
            total_slot_minutes
        )
        
        participation = calculate_participation_score(
            dg_id,
            data['group_cast'],
            data['dancer_constraints'],
            rehearsal_slots,
            total_slot_minutes
        )
        
        # Build row
        row_data = {
            'dance_group': dg_name,
            'priority': round(priority, 3),
            'participation': round(participation, 3)
        }
        
        # Add slot columns (3 per slot: rd, dancers, combined)
        for i, slot_name in enumerate(slot_names):
            avail = full_availability_by_slot.get(slot_name, {'rd': '', 'dancers': '', 'combined': ''})
            row_data[f'slot_{i+1}_rd'] = avail['rd']
            row_data[f'slot_{i+1}_dancers'] = avail['dancers']
            row_data[f'slot_{i+1}_combined'] = avail['combined']
        
        matrix_rows.append(row_data)
    
    # Create DataFrame
    df = pd.DataFrame(matrix_rows)
    
    return df


@click.command()
@click.option('--config', 
              default='config/workbook_config.yaml',
              type=click.Path(exists=True),
              help='YAML config for Google Sheets')
@click.option('--output', 
              default='availability_matrix.csv',
              help='Output CSV file')
@click.option('--verbose', is_flag=True,
              help='Show detailed progress')
def cli(config, output, verbose):
    """
    Generate availability matrix CSV.
    
    Shows dance group priority, participation, and 100% availability windows
    for each rehearsal slot.
    """
    click.echo(click.style("\n=== Availability Matrix Generator ===\n", fg='blue', bold=True))
    
    # Load data
    click.echo("📊 Loading scheduling data...")
    
    try:
        loader = SchedulingDataLoader(config)
        data = loader.load_all()
    except Exception as e:
        click.echo(click.style(f"Error loading data: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    if verbose:
        click.echo(f"  ✓ Loaded {len(data['dance_groups'])} dance groups")
        click.echo(f"  ✓ Loaded {len(data['rehearsals'])} rehearsal slots")
    else:
        click.echo(click.style("  ✓ Data loaded successfully", fg='green'))
    
    # Generate matrix
    click.echo(click.style("\n🔍 Calculating availability matrix...", fg='cyan'))
    
    try:
        matrix_df = generate_availability_matrix(data, verbose=verbose)
    except Exception as e:
        click.echo(click.style(f"Error generating matrix: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    click.echo(f"  Generated matrix for {len(matrix_df)} dance groups")
    
    # Save to CSV
    click.echo(f"\n📝 Saving to {output}...")
    
    try:
        matrix_df.to_csv(output, index=False)
    except Exception as e:
        click.echo(click.style(f"Error saving CSV: {e}", fg='red'))
        sys.exit(1)
    
    click.echo(click.style(f"\n✅ Matrix saved to {output}\n", fg='green', bold=True))
    
    # Show preview
    click.echo("Preview (first 5 rows):")
    click.echo(matrix_df.head().to_string(index=False))


if __name__ == '__main__':
    cli()