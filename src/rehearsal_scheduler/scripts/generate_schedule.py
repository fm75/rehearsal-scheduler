#!/usr/bin/env python3
"""
Greedy Schedule Generator

Generates rehearsal schedules using greedy assignment algorithm.
Reads availability matrix and RD time allocations, produces slot-by-slot schedules.

Output: One CSV per rehearsal slot with dance group assignments in order.

Usage:
    # Default greedy with priority sorting
    python -m rehearsal_scheduler.scripts.generate_schedule
    
    # Try different sort orders
    python -m rehearsal_scheduler.scripts.generate_schedule --sort-by duration
    
    # Future: Different heuristics
    python -m rehearsal_scheduler.scripts.generate_schedule --heuristic ilp
"""

import sys
import os
import click
import pandas as pd
from pathlib import Path

from rehearsal_scheduler.persistence.data_loader import SchedulingDataLoader


def load_availability_matrix(matrix_file: str) -> pd.DataFrame:
    """
    Load availability matrix CSV.
    
    Expected columns: dance_group, priority, participation, slot_1, slot_2, ...
    
    Args:
        matrix_file: Path to availability matrix CSV
        
    Returns:
        DataFrame with availability data
    """
    if not os.path.exists(matrix_file):
        raise FileNotFoundError(f"Availability matrix not found: {matrix_file}")
    
    return pd.read_csv(matrix_file)


def load_time_allocations(data: dict) -> pd.DataFrame:
    """
    Load RD time allocation requests.
    
    Args:
        data: Dict of DataFrames from SchedulingDataLoader
        
    Returns:
        DataFrame with columns: dg_id, dg_name, minutes
    """
    # Check if we have an 'allotted' sheet
    if 'allotted' in data and not data['allotted'].empty:
        # Use allotted sheet if available
        allotted_df = data['allotted']
        
        # Expected columns: rd_id, rd_name, minutes, dg_id, dg_name
        # Select just what we need
        if 'dg_id' in allotted_df.columns and 'minutes' in allotted_df.columns:
            result = allotted_df[['dg_id', 'dg_name', 'minutes']].copy()
            
            # Ensure minutes is numeric
            result['minutes'] = pd.to_numeric(result['minutes'], errors='coerce').fillna(30).astype(int)
            
            return result
        else:
            # Allotted sheet exists but doesn't have expected columns
            # Fall back to default
            result = data['dance_groups'][['dg_id', 'dg_name']].copy()
            result['minutes'] = 30
            return result
    else:
        # No allotted sheet - use default time
        result = data['dance_groups'][['dg_id', 'dg_name']].copy()
        result['minutes'] = 30  # Default allocation
        return result


def parse_slot_columns(availability_df: pd.DataFrame) -> list:
    """
    Extract slot column names from availability matrix.
    
    Args:
        availability_df: Availability matrix DataFrame
        
    Returns:
        List of slot column names like ['slot_1', 'slot_2', ...]
    """
    return [col for col in availability_df.columns if col.startswith('slot_')]


def parse_slot_duration(slot_name: str, rehearsals_df: pd.DataFrame) -> int:
    """
    Get duration in minutes for a rehearsal slot.
    
    Args:
        slot_name: Like "slot_1", "slot_2"
        rehearsals_df: Rehearsals DataFrame
        
    Returns:
        Duration in minutes
    """
    # Extract slot index (1-based)
    slot_idx = int(slot_name.split('_')[1]) - 1
    
    if slot_idx >= len(rehearsals_df):
        return 180  # Default 3 hours
    
    row = rehearsals_df.iloc[slot_idx]
    
    # Calculate duration from start_time and end_time
    start = row['start_time']
    end = row['end_time']
    
    # Parse times (could be int like 1800 or string like "6:00 PM")
    if isinstance(start, str):
        # Parse formatted time
        from rehearsal_scheduler.models.intervals import parse_time_to_military
        start = parse_time_to_military(start)
        end = parse_time_to_military(end)
    
    # Calculate duration
    start_hours = start // 100
    start_mins = start % 100
    end_hours = end // 100
    end_mins = end % 100
    
    duration = (end_hours * 60 + end_mins) - (start_hours * 60 + start_mins)
    
    return duration


def greedy_schedule_slot(
    slot_name: str,
    slot_duration: int,
    availability_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    scheduled_groups: set,
    sort_by: str = 'priority'
) -> pd.DataFrame:
    """
    Generate greedy schedule for one slot.
    
    Args:
        slot_name: Column name like "slot_1"
        slot_duration: Total minutes available in slot
        availability_df: Availability matrix
        allocations_df: Time allocations (dg_id, dg_name, minutes)
        scheduled_groups: Set of dg_names already scheduled
        sort_by: How to sort candidates ('priority', 'duration', 'participation', 'name')
        
    Returns:
        DataFrame with columns: order, minutes, dance_group, notes
    """
    from rehearsal_scheduler.models.interval_parsing import (
        parse_availability_string,
        does_duration_fit_in_intervals
    )
    from rehearsal_scheduler.models.interval_operations import subtract_intervals
    from rehearsal_scheduler.models.intervals import TimeInterval
    from datetime import time as dt_time
    
    # Filter to unscheduled groups with availability in this slot
    candidates = availability_df[
        (~availability_df['dance_group'].isin(scheduled_groups)) &
        (availability_df[slot_name].notna()) &
        (availability_df[slot_name] != '')
    ].copy()
    
    # Merge with allocations to get requested minutes
    candidates = pd.merge(
        candidates,
        allocations_df[['dg_name', 'minutes']],
        left_on='dance_group',
        right_on='dg_name',
        how='left'
    )
    
    # Fill missing minutes with default
    candidates['minutes'] = candidates['minutes'].fillna(30).astype(int)
    
    # Parse availability intervals for each candidate
    def safe_parse_availability(avail_str):
        """Parse availability string, handling special cases."""
        if not avail_str or avail_str.strip() == '':
            return []
        
        # Handle special cases
        avail_str_lower = str(avail_str).lower().strip()
        if avail_str_lower in ['none', 'no dancers', 'unavailable']:
            return []
        
        # Parse actual intervals
        try:
            return parse_availability_string(avail_str)
        except Exception:
            # Parsing failed - treat as no availability
            return []
    
    candidates['parsed_intervals'] = candidates[slot_name].apply(safe_parse_availability)
    
    # Sort candidates based on strategy
    if sort_by == 'priority':
        # Ascending - most constrained (low priority) first
        candidates = candidates.sort_values('priority', ascending=True)
    elif sort_by == 'duration':
        # Descending - longest first (bin packing heuristic)
        candidates = candidates.sort_values('minutes', ascending=False)
    elif sort_by == 'participation':
        # Descending - best participation first
        candidates = candidates.sort_values('participation', ascending=False)
    elif sort_by == 'name':
        # Alphabetical (for testing)
        candidates = candidates.sort_values('dance_group')
    else:
        raise ValueError(f"Unknown sort_by: {sort_by}")
    
    # Track remaining available time as list of intervals
    # Start with full slot (we'll subtract as we assign dances)
    # Note: We don't have slot start/end times here, so we track just the total minutes
    # In reality, we should track actual time windows, but for now use total capacity
    remaining_minutes = slot_duration
    
    # Greedy assignment
    schedule = []
    order = 10
    
    for _, row in candidates.iterrows():
        requested_minutes = row['minutes']
        
        # Skip zero-minute dances (no choreography yet)
        if requested_minutes == 0:
            continue
        
        dance_group = row['dance_group']
        available_intervals = row['parsed_intervals']
        
        # Check if duration fits in any available interval
        if available_intervals and does_duration_fit_in_intervals(requested_minutes, available_intervals):
            # Check if we have enough total time left in slot
            if requested_minutes <= remaining_minutes:
                schedule.append({
                    'order': order,
                    'minutes': requested_minutes,
                    'dance_group': dance_group,
                    'notes': ''
                })
                remaining_minutes -= requested_minutes
                scheduled_groups.add(dance_group)
                order += 10
    
    # Check for groups with partial availability (not scheduled above)
    # Look at ALL unscheduled groups, not just candidates with availability in this slot
    all_unscheduled = availability_df[
        (~availability_df['dance_group'].isin(scheduled_groups))
    ].copy()
    
    # Merge with allocations to get minutes
    all_unscheduled = pd.merge(
        all_unscheduled,
        allocations_df[['dg_name', 'minutes']],
        left_on='dance_group',
        right_on='dg_name',
        how='left'
    )
    all_unscheduled['minutes'] = all_unscheduled['minutes'].fillna(30).astype(int)
    
    for _, row in all_unscheduled.iterrows():
        dance_group = row['dance_group']
        
        # Skip if already scheduled
        if dance_group in scheduled_groups:
            continue
        
        requested_minutes = row['minutes']
        
        # Skip zero-minute dances
        if requested_minutes == 0:
            continue
        
        # Check if this group has participation but no 100% availability in THIS slot
        participation = row.get('participation', 0)
        slot_availability = row.get(slot_name, '')
        
        # Parse availability for this slot (handle NaN)
        if pd.isna(slot_availability) or slot_availability == '':
            available_intervals = []
        else:
            available_intervals = safe_parse_availability(str(slot_availability))
        
        if participation > 0 and not available_intervals:
            # Has dancers available but no 100% overlap - needs substitution
            if requested_minutes <= remaining_minutes:
                participation_pct = int(participation * 100)
                schedule.append({
                    'order': order,
                    'minutes': requested_minutes,
                    'dance_group': dance_group,
                    'notes': f'Needs RD substitution ({participation_pct}% dancers available)'
                })
                remaining_minutes -= requested_minutes
                scheduled_groups.add(dance_group)
                order += 10
    
    # Add idle time if any remains
    if remaining_minutes > 0:
        schedule.append({
            'order': order,
            'minutes': remaining_minutes,
            'dance_group': '(idle)',
            'notes': ''
        })
    
    return pd.DataFrame(schedule)


def greedy_schedule_all(
    availability_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    rehearsals_df: pd.DataFrame,
    sort_by: str = 'priority'
) -> dict:
    """
    Generate greedy schedules for all slots.
    
    Args:
        availability_df: Availability matrix
        allocations_df: Time allocations
        rehearsals_df: Rehearsal slot info
        sort_by: Sorting strategy for candidates
        
    Returns:
        Dict mapping slot_name -> schedule DataFrame
    """
    slot_columns = parse_slot_columns(availability_df)
    schedules = {}
    scheduled_groups = set()
    
    for slot_name in slot_columns:
        slot_duration = parse_slot_duration(slot_name, rehearsals_df)
        
        schedule_df = greedy_schedule_slot(
            slot_name,
            slot_duration,
            availability_df,
            allocations_df,
            scheduled_groups,
            sort_by
        )
        
        schedules[slot_name] = schedule_df
    
    return schedules


@click.command()
@click.option('--config',
              default='config/workbook_config.yaml',
              type=click.Path(exists=True),
              help='YAML config for Google Sheets')
@click.option('--matrix',
              default='availability_matrix.csv',
              type=click.Path(exists=True),
              help='Availability matrix CSV file')
@click.option('--output-dir',
              default='schedules',
              help='Directory for output schedule CSVs')
@click.option('--heuristic',
              type=click.Choice(['greedy']),
              default='greedy',
              help='Scheduling algorithm (currently only greedy supported)')
@click.option('--sort-by',
              type=click.Choice(['priority', 'duration', 'participation', 'name']),
              default='priority',
              help='How to sort candidates in greedy algorithm')
@click.option('--verbose', is_flag=True,
              help='Show detailed progress')
def cli(config, matrix, output_dir, heuristic, sort_by, verbose):
    """
    Generate rehearsal schedules using greedy assignment.
    
    Reads availability matrix and time allocations, produces one CSV per slot.
    """
    click.echo(click.style("\n=== Greedy Schedule Generator ===\n", fg='blue', bold=True))
    
    # Load data
    click.echo("📊 Loading data...")
    
    try:
        loader = SchedulingDataLoader(config)
        data = loader.load_all()
    except Exception as e:
        click.echo(click.style(f"Error loading config data: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    try:
        availability_df = load_availability_matrix(matrix)
    except Exception as e:
        click.echo(click.style(f"Error loading availability matrix: {e}", fg='red'))
        click.echo(f"Make sure to run generate_availability_matrix first")
        sys.exit(1)
    
    try:
        allocations_df = load_time_allocations(data)
    except Exception as e:
        click.echo(click.style(f"Error loading time allocations: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    if verbose:
        click.echo(f"  ✓ Loaded {len(availability_df)} dance groups")
        click.echo(f"  ✓ Loaded {len(data['rehearsals'])} rehearsal slots")
        click.echo(f"  ✓ Loaded {len(allocations_df)} time allocations")
        if len(allocations_df) > 0:
            click.echo(f"  ✓ Minutes range: {allocations_df['minutes'].min()}-{allocations_df['minutes'].max()}")
            click.echo("\nSample allocations:")
            click.echo(allocations_df.head().to_string(index=False))
        click.echo(f"  ✓ Using sort strategy: {sort_by}")
    else:
        click.echo(click.style("  ✓ Data loaded successfully", fg='green'))
    
    # Generate schedules
    click.echo(click.style(f"\n🔍 Generating schedules (heuristic={heuristic}, sort_by={sort_by})...", fg='cyan'))
    
    try:
        if heuristic == 'greedy':
            schedules = greedy_schedule_all(
                availability_df,
                allocations_df,
                data['rehearsals'],
                sort_by=sort_by
            )
        else:
            click.echo(click.style(f"Heuristic '{heuristic}' not yet implemented", fg='red'))
            sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"Error generating schedules: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Save schedules
    click.echo(f"\n📝 Saving schedules to {output_dir}/...")
    
    for slot_name, schedule_df in schedules.items():
        output_file = os.path.join(output_dir, f"{slot_name}_schedule.csv")
        schedule_df.to_csv(output_file, index=False)
        
        if verbose:
            click.echo(f"  ✓ {slot_name}: {len(schedule_df)} assignments")
    
    click.echo(click.style(f"\n✅ Generated {len(schedules)} schedule files\n", fg='green', bold=True))
    
    # Summary
    total_scheduled = sum(
        len(df[df['dance_group'] != '(idle)']) 
        for df in schedules.values()
    )
    total_groups = len(availability_df)
    
    click.echo(f"Summary:")
    click.echo(f"  Scheduled: {total_scheduled} / {total_groups} dance groups")
    click.echo(f"  Unscheduled: {total_groups - total_scheduled}")
    
    if verbose:
        click.echo(f"\nPreview of slot_1_schedule.csv:")
        if 'slot_1' in schedules:
            click.echo(schedules['slot_1'].to_string(index=False))


if __name__ == '__main__':
    cli()