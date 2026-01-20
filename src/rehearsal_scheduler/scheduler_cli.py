# src/rehearsal_scheduler/scheduler_cli.py

"""
Rehearsal Scheduler - Assign dances to venue time slots.

This is the core scheduling algorithm that assigns dances to available
venue times while respecting RD and dancer constraints.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime, time
import click

from rehearsal_scheduler.grammar import validate_token

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False


@click.group()
def cli():
    """Rehearsal scheduling tools."""
    pass


@cli.command()
@click.option('--time-requests', '-t', required=True, type=click.Path(exists=True),
              help='CSV file with time requests/allocations')
@click.option('--venue-schedule', '-v', required=True, type=click.Path(exists=True),
              help='CSV file with venue availability')
@click.option('--dance-matrix', '-m', required=True, type=click.Path(exists=True),
              help='CSV file with dance cast matrix')
@click.option('--dancer-conflicts', '-d', required=True, type=click.Path(exists=True),
              help='CSV file with dancer conflicts')
@click.option('--rhd-conflicts', '-r', required=True, type=click.Path(exists=True),
              help='CSV file with RD conflicts')
@click.option('--dance-map', '-p', required=True, type=click.Path(exists=True),
              help='CSV file mapping dances to RDs')
@click.option('--min-attendance', default=90.0, type=float,
              help='Minimum cast attendance percentage (default: 90%)')
@click.option('--output', '-o', type=click.Path(),
              help='Write schedule to CSV file')
def schedule(time_requests, venue_schedule, dance_matrix, dancer_conflicts, 
             rhd_conflicts, dance_map, min_attendance, output):
    """Generate rehearsal schedule.
    
    Assigns dances to venue time slots while respecting:
    - RD availability (hard constraint)
    - Dancer availability (soft constraint with threshold)
    - Allocated time per dance
    - Available venue time
    
    Example:
        rehearsal-schedule schedule \\
          -t time_requests.csv \\
          -v venue_schedule.csv \\
          -m dance_matrix.csv \\
          -d conflicts.csv \\
          -r rhd_conflicts.csv \\
          -p dance_director_map.csv \\
          --min-attendance 90 \\
          -o schedule_output.csv
    """
    click.echo("=" * 80)
    click.echo("REHEARSAL SCHEDULER")
    click.echo("=" * 80)
    
    # Load all data
    click.echo("\n📂 Loading data files...")
    data = load_scheduling_data(
        time_requests, venue_schedule, dance_matrix, 
        dancer_conflicts, rhd_conflicts, dance_map
    )
    
    if not data:
        click.echo("❌ Error loading data", err=True)
        sys.exit(1)
    
    click.echo("✓ All data loaded successfully")
    
    # Run scheduling algorithm
    click.echo(f"\n🔧 Running scheduler (min attendance: {min_attendance}%)...")
    result = run_scheduler(data, min_attendance)
    
    # Display results
    display_schedule(result)
    
    # Write output if requested
    if output:
        write_schedule_csv(result, output)
    
    # Exit with error if scheduling failed
    if result['unscheduled_dances']:
        sys.exit(1)


def load_scheduling_data(time_requests_path, venue_schedule_path, dance_matrix_path,
                        dancer_conflicts_path, rhd_conflicts_path, dance_map_path):
    """Load all CSV files needed for scheduling."""
    try:
        # Time requests/allocations
        with open(time_requests_path, 'r') as f:
            time_requests = list(csv.DictReader(f))
        
        # Venue schedule
        with open(venue_schedule_path, 'r') as f:
            venue_schedule = list(csv.DictReader(f))
        
        # Dance matrix (cast)
        with open(dance_matrix_path, 'r') as f:
            reader = csv.DictReader(f)
            dance_matrix = {row['dance']: row for row in reader}
        
        # Dancer conflicts
        with open(dancer_conflicts_path, 'r') as f:
            dancer_conflicts = list(csv.DictReader(f))
        
        # RD conflicts
        with open(rhd_conflicts_path, 'r') as f:
            rhd_conflicts = list(csv.DictReader(f))
        
        # Dance-to-RD mapping
        with open(dance_map_path, 'r') as f:
            dance_map = {row['dance_id']: row['rhd_id'] 
                        for row in csv.DictReader(f)}
        
        return {
            'time_requests': time_requests,
            'venue_schedule': venue_schedule,
            'dance_matrix': dance_matrix,
            'dancer_conflicts': dancer_conflicts,
            'rhd_conflicts': rhd_conflicts,
            'dance_map': dance_map
        }
    
    except Exception as e:
        click.echo(f"❌ Error loading data: {e}", err=True)
        return None


def run_scheduler(data, min_attendance):
    """Main scheduling algorithm."""
    
    click.echo("\n📊 Analyzing constraints...")
    
    # Parse all constraints
    dancer_constraint_map = parse_all_constraints(data['dancer_conflicts'], 'dancer_id')
    rhd_constraint_map = parse_all_constraints(data['rhd_conflicts'], 'rhd_id')
    
    # Build venue time slots
    venue_slots = build_venue_slots(data['venue_schedule'])
    
    click.echo(f"   Found {len(venue_slots)} venue time slots")
    
    # Get dances to schedule
    dances_to_schedule = get_dances_to_schedule(data['time_requests'])
    
    click.echo(f"   Found {len(dances_to_schedule)} dances to schedule")
    click.echo(f"   Total time needed: {sum(d['minutes'] for d in dances_to_schedule):.0f} minutes")
    
    # Schedule dances
    schedule = []
    unscheduled = []
    
    click.echo("\n🎯 Scheduling dances...")
    
    for dance in dances_to_schedule:
        dance_id = dance['dance_id']
        click.echo(f"\n   Scheduling {dance_id}...")
        
        # Find best slot
        best_slot = find_best_slot(
            dance, venue_slots, data, 
            dancer_constraint_map, rhd_constraint_map,
            min_attendance
        )
        
        if best_slot:
            schedule.append({
                'dance_id': dance_id,
                'slot': best_slot['slot'],
                'attendance': best_slot['attendance'],
                'missing_dancers': best_slot['missing_dancers']
            })
            click.echo(f"      ✓ Assigned to {best_slot['slot']['venue']} "
                      f"{best_slot['slot']['day']} {best_slot['slot']['start']}-{best_slot['slot']['end']}")
            click.echo(f"      Attendance: {best_slot['attendance']['available']}/{best_slot['attendance']['total']} "
                      f"({best_slot['attendance']['pct']:.1f}%)")
        else:
            unscheduled.append(dance_id)
            click.echo(f"      ❌ Could not schedule (no suitable slots)")
    
    return {
        'schedule': schedule,
        'unscheduled_dances': unscheduled,
        'venue_slots': venue_slots
    }


def parse_all_constraints(conflicts_data, id_column):
    """Parse all constraints into a lookup dictionary."""
    constraint_map = {}
    
    for row in conflicts_data:
        entity_id = row.get(id_column, '').strip()
        conflicts_text = row.get('conflicts', '').strip()
        
        if not conflicts_text:
            constraint_map[entity_id] = []
            continue
        
        # Parse tokens
        tokens = [t.strip() for t in conflicts_text.split(',')]
        parsed = []
        
        for token in tokens:
            if not token:
                continue
            result, error = validate_token(token)
            if not error:
                parsed.append(result)
        
        constraint_map[entity_id] = parsed
    
    return constraint_map


def build_venue_slots(venue_schedule):
    """Convert venue schedule into time slots."""
    slots = []
    
    for row in venue_schedule:
        venue = row.get('venue', '')
        day = row.get('day', '')
        date_str = row.get('date', '')
        start_str = row.get('start', '')
        end_str = row.get('end', '')
        
        # Parse times
        start_time = parse_time(start_str)
        end_time = parse_time(end_str)
        
        if start_time and end_time:
            start_mins = start_time.hour * 60 + start_time.minute
            end_mins = end_time.hour * 60 + end_time.minute
            available_mins = end_mins - start_mins
            
            slots.append({
                'venue': venue,
                'day': day,
                'date': date_str,
                'start': start_str,
                'end': end_str,
                'available_minutes': available_mins,
                'remaining_minutes': available_mins  # Will decrease as we schedule
            })
    
    return slots


def parse_time(time_str):
    """Parse time string to datetime.time object."""
    try:
        return datetime.strptime(time_str.strip(), '%I:%M %p').time()
    except ValueError:
        try:
            return datetime.strptime(time_str.strip(), '%H:%M').time()
        except ValueError:
            return None


def get_dances_to_schedule(time_requests):
    """Get list of dances with their allocated times."""
    dances = []
    
    for row in time_requests:
        dance_id = row.get('number_id', '').strip()
        allocated_str = str(row.get('min_allocated', '')).strip()
        
        if allocated_str and allocated_str != '':
            try:
                minutes = float(allocated_str)
                dances.append({
                    'dance_id': dance_id,
                    'minutes': minutes
                })
            except ValueError:
                pass
    
    # Sort by minutes descending (schedule longer dances first)
    dances.sort(key=lambda x: x['minutes'], reverse=True)
    
    return dances

# =============================================================================


def find_best_slot(dance, venue_slots, data, dancer_constraints, rhd_constraints, min_attendance):
    """Find the best venue slot for this dance."""
    
    # TODO: Implement actual scheduling logic
    # For now, just a stub
    return None


def display_schedule(result):
    """Display the generated schedule."""
    click.echo("\n" + "=" * 80)
    click.echo("SCHEDULE RESULTS")
    click.echo("=" * 80)
    
    if result['schedule']:
        click.echo(f"\n✓ Successfully scheduled {len(result['schedule'])} dances")
        # TODO: Display formatted schedule
    
    if result['unscheduled_dances']:
        click.echo(f"\n❌ Could not schedule {len(result['unscheduled_dances'])} dances:")
        for dance_id in result['unscheduled_dances']:
            click.echo(f"   - {dance_id}")


def write_schedule_csv(result, output_path):
    """Write schedule to CSV file."""
    # TODO: Implement CSV output
    pass
def check_slot_conflicts_simple(parsed_constraints, slot):
    """Simple check if any constraint conflicts with slot."""
    from rehearsal_scheduler.constraints import (
        DayOfWeekConstraint, TimeOnDayConstraint,
        DateConstraint, DateRangeConstraint
    )
    from datetime import datetime, time
    
    if not parsed_constraints:
        return False
    
    slot_day = slot['day'].lower()
    
    # Parse slot date
    try:
        slot_date = datetime.strptime(slot['date'], '%m/%d/%Y').date()
    except ValueError:
        try:
            slot_date = datetime.strptime(slot['date'], '%m/%d/%y').date()
        except ValueError:
            slot_date = None
    
    # Parse slot times
    slot_start = parse_time(slot['start'])
    slot_end = parse_time(slot['end'])
    
    for token_text, parsed_result in parsed_constraints:
        # Handle tuple of constraints
        if isinstance(parsed_result, tuple):
            constraint_list = parsed_result
        else:
            constraint_list = [parsed_result]
        
        for constraint in constraint_list:
            if isinstance(constraint, DayOfWeekConstraint):
                if constraint.day_of_week == slot_day:
                    return True
            
            elif isinstance(constraint, TimeOnDayConstraint):
                if constraint.day_of_week == slot_day and slot_start and slot_end:
                    constraint_start = time(constraint.start_time // 100, 
                                          constraint.start_time % 100)
                    constraint_end = time(constraint.end_time // 100, 
                                        constraint.end_time % 100)
                    if time_ranges_overlap(slot_start, slot_end, 
                                         constraint_start, constraint_end):
                        return True
            
            elif isinstance(constraint, DateConstraint):
                if slot_date and constraint.date == slot_date:
                    return True
            
            elif isinstance(constraint, DateRangeConstraint):
                if slot_date and constraint.start_date <= slot_date <= constraint.end_date:
                    return True
    
    return False


def time_ranges_overlap(start1, end1, start2, end2):
    """Check if two time ranges overlap."""
    return start1 < end2 and start2 < end1
# =============================================================================

@cli.command()
@click.option('--dance-matrix', '-m', required=True, type=click.Path(exists=True),
              help='CSV file with dance cast matrix')
@click.option('--dancer-conflicts', '-d', required=True, type=click.Path(exists=True),
              help='CSV file with dancer conflicts')
@click.option('--rhd-conflicts', '-r', required=True, type=click.Path(exists=True),
              help='CSV file with RD conflicts')
@click.option('--dance-map', '-p', required=True, type=click.Path(exists=True),
              help='CSV file mapping dances to RDs')
@click.option('--venue-schedule', '-v', required=True, type=click.Path(exists=True),
              help='CSV file with venue availability')
@click.option('--output', '-o', type=click.Path(),
              help='Write constraint catalog to CSV file')
def catalog_by_venue(dance_matrix, dancer_conflicts, rhd_conflicts, 
                     dance_map, venue_schedule, output):
    """Catalog dance availability by venue time slot.
    
    For each venue time slot, shows:
    - Which dances can be scheduled (conflict-free or near conflict-free)
    - Which dances have RD conflicts (cannot schedule)
    - Which dances have cast conflicts (can schedule with reduced attendance)
    
    This helps the director see which dances fit each venue slot.
    
    Example:
        rehearsal-schedule catalog-by-venue \\
          -m dance_matrix.csv \\
          -d conflicts.csv \\
          -r rhd_conflicts.csv \\
          -p dance_director_map.csv \\
          -v venue_schedule.csv \\
          -o venue_availability_catalog.csv
    """
    click.echo("=" * 80)
    click.echo("DANCE AVAILABILITY BY VENUE SLOT")
    click.echo("=" * 80)
    
    # Load data
    click.echo("\n📂 Loading data...")
    
    try:
        # Dance matrix (cast)
        with open(dance_matrix, 'r') as f:
            reader = csv.DictReader(f)
            dance_cast = {}
            for row in reader:
                dance_id = row['dance']
                cast = [dancer_id for dancer_id, val in row.items() 
                       if dancer_id != 'dance' and val and val.strip() in ['1.0', '1']]
                dance_cast[dance_id] = cast
        
        # Dancer conflicts
        with open(dancer_conflicts, 'r') as f:
            dancer_constraints = {row['dancer_id']: row['conflicts'] 
                                 for row in csv.DictReader(f)}
        
        # RD conflicts
        with open(rhd_conflicts, 'r') as f:
            rhd_constraints = {row['rhd_id']: row['conflicts'] 
                              for row in csv.DictReader(f)}
        
        # Dance to RD mapping
        with open(dance_map, 'r') as f:
            dance_to_rd = {row['dance_id']: row['rhd_id'] 
                          for row in csv.DictReader(f)}
        
        # Venue schedule
        with open(venue_schedule, 'r') as f:
            venue_slots = list(csv.DictReader(f))
        
    except Exception as e:
        click.echo(f"❌ Error loading data: {e}", err=True)
        sys.exit(1)
    
    click.echo("✓ Data loaded successfully")
    
    # Build catalog by venue
    click.echo("\n🔍 Analyzing dance availability for each venue slot...")
    
    catalog = []
    
    for slot in venue_slots:
        slot_info = {
            'venue': slot['venue'],
            'day': slot['day'],
            'date': slot['date'],
            'start': slot['start'],
            'end': slot['end'],
            'conflict_free_dances': [],
            'rd_blocked_dances': [],
            'cast_conflict_dances': []
        }
        
        # Check each dance against this slot
        for dance_id in sorted(dance_cast.keys()):
            cast = dance_cast[dance_id]
            rhd_id = dance_to_rd.get(dance_id, 'Unknown')
            
            # Parse RD constraints
            rd_conflict_text = rhd_constraints.get(rhd_id, '').strip()
            rd_parsed = parse_constraints(rd_conflict_text)
            
            # Parse cast constraints
            cast_parsed = {}
            for dancer_id in cast:
                dancer_conflict_text = dancer_constraints.get(dancer_id, '').strip()
                if dancer_conflict_text:
                    cast_parsed[dancer_id] = parse_constraints(dancer_conflict_text)
            
            # Check RD availability
            rd_has_conflict = check_slot_conflicts_simple(rd_parsed, slot)
            
            # Check cast availability
            conflicted_dancers = []
            for dancer_id, constraints in cast_parsed.items():
                if check_slot_conflicts_simple(constraints, slot):
                    conflicted_dancers.append(dancer_id)
            
            # Categorize this dance
            attendance_pct = ((len(cast) - len(conflicted_dancers)) / len(cast) * 100) if cast else 100
            
            if rd_has_conflict:
                slot_info['rd_blocked_dances'].append({
                    'dance_id': dance_id,
                    'rhd_id': rhd_id,
                    'cast_size': len(cast)
                })
            elif len(conflicted_dancers) == 0:
                slot_info['conflict_free_dances'].append({
                    'dance_id': dance_id,
                    'rhd_id': rhd_id,
                    'cast_size': len(cast),
                    'attendance_pct': 100.0
                })
            else:
                slot_info['cast_conflict_dances'].append({
                    'dance_id': dance_id,
                    'rhd_id': rhd_id,
                    'cast_size': len(cast),
                    'conflicted_count': len(conflicted_dancers),
                    'conflicted_dancers': conflicted_dancers,
                    'attendance_pct': attendance_pct
                })
        
        catalog.append(slot_info)
    
    # Display catalog
    display_venue_catalog(catalog)
    
    # Write to CSV if requested
    if output:
        write_venue_catalog_csv(catalog, output)


def parse_constraints(conflict_text):
    """Parse constraint text into list of parsed constraints."""
    from rehearsal_scheduler.grammar import validate_token
    
    if not conflict_text:
        return []
    
    tokens = [t.strip() for t in conflict_text.split(',')]
    parsed = []
    
    for token in tokens:
        if token:
            result, error = validate_token(token)
            if not error:
                parsed.append((token, result))
    
    return parsed


def display_venue_catalog(catalog):
    """Display formatted venue catalog."""
    
    click.echo("\n" + "=" * 80)
    click.echo("VENUE SLOT AVAILABILITY")
    click.echo("=" * 80)
    
    for slot_info in catalog:
        click.echo(f"\n{'═' * 80}")
        click.echo(f"VENUE: {slot_info['venue']}")
        click.echo(f"{slot_info['day']}, {slot_info['date']}")
        click.echo(f"Time: {slot_info['start']} - {slot_info['end']}")
        click.echo(f"{'═' * 80}")
        
        # Conflict-free dances (best options)
        conflict_free = slot_info['conflict_free_dances']
        if conflict_free:
            click.echo(f"\n✓ CONFLICT-FREE DANCES ({len(conflict_free)}):")
            click.echo("  (Can schedule with 100% attendance)")
            for dance in conflict_free:
                click.echo(f"  • {dance['dance_id']} (RD: {dance['rhd_id']}, Cast: {dance['cast_size']})")
        else:
            click.echo(f"\n✓ CONFLICT-FREE DANCES: None")
        
        # Cast conflict dances (can schedule with reduced attendance)
        cast_conflicts = sorted(slot_info['cast_conflict_dances'], 
                               key=lambda x: x['attendance_pct'], 
                               reverse=True)
        if cast_conflicts:
            click.echo(f"\n⚠ DANCES WITH CAST CONFLICTS ({len(cast_conflicts)}):")
            click.echo("  (Can schedule with reduced attendance)")
            for dance in cast_conflicts:
                click.echo(f"  • {dance['dance_id']} (RD: {dance['rhd_id']}, "
                          f"Attendance: {dance['attendance_pct']:.1f}% - "
                          f"{dance['conflicted_count']}/{dance['cast_size']} missing)")
                if len(dance['conflicted_dancers']) <= 5:
                    click.echo(f"    Missing: {', '.join(dance['conflicted_dancers'])}")
                else:
                    click.echo(f"    Missing: {', '.join(dance['conflicted_dancers'][:5])}... "
                              f"({len(dance['conflicted_dancers'])} total)")
        
        # RD blocked dances (cannot schedule)
        rd_blocked = slot_info['rd_blocked_dances']
        if rd_blocked:
            click.echo(f"\n❌ RD UNAVAILABLE - CANNOT SCHEDULE ({len(rd_blocked)}):")
            for dance in rd_blocked:
                click.echo(f"  • {dance['dance_id']} (RD: {dance['rhd_id']} unavailable)")
    
    # Summary
    click.echo("\n" + "=" * 80)
    click.echo("SUMMARY")
    click.echo("=" * 80)
    
    total_slots = len(catalog)
    for i, slot_info in enumerate(catalog, 1):
        click.echo(f"\nSlot {i} ({slot_info['venue']} {slot_info['day']}):")
        click.echo(f"  Conflict-free dances: {len(slot_info['conflict_free_dances'])}")
        click.echo(f"  Dances with cast conflicts: {len(slot_info['cast_conflict_dances'])}")
        click.echo(f"  RD-blocked dances: {len(slot_info['rd_blocked_dances'])}")


def write_venue_catalog_csv(catalog, output_path):
    """Write venue catalog to CSV."""
    import csv
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'venue', 'day', 'date', 'time_slot', 'dance_id', 'rhd_id',
                'status', 'attendance_pct', 'missing_dancers'
            ])
            writer.writeheader()
            
            for slot_info in catalog:
                time_slot = f"{slot_info['start']} - {slot_info['end']}"
                
                # Write conflict-free dances
                for dance in slot_info['conflict_free_dances']:
                    writer.writerow({
                        'venue': slot_info['venue'],
                        'day': slot_info['day'],
                        'date': slot_info['date'],
                        'time_slot': time_slot,
                        'dance_id': dance['dance_id'],
                        'rhd_id': dance['rhd_id'],
                        'status': 'CONFLICT_FREE',
                        'attendance_pct': 100.0,
                        'missing_dancers': ''
                    })
                
                # Write cast conflict dances
                for dance in slot_info['cast_conflict_dances']:
                    writer.writerow({
                        'venue': slot_info['venue'],
                        'day': slot_info['day'],
                        'date': slot_info['date'],
                        'time_slot': time_slot,
                        'dance_id': dance['dance_id'],
                        'rhd_id': dance['rhd_id'],
                        'status': 'CAST_CONFLICTS',
                        'attendance_pct': dance['attendance_pct'],
                        'missing_dancers': ', '.join(dance['conflicted_dancers'])
                    })
                
                # Write RD blocked dances
                for dance in slot_info['rd_blocked_dances']:
                    writer.writerow({
                        'venue': slot_info['venue'],
                        'day': slot_info['day'],
                        'date': slot_info['date'],
                        'time_slot': time_slot,
                        'dance_id': dance['dance_id'],
                        'rhd_id': dance['rhd_id'],
                        'status': 'RD_UNAVAILABLE',
                        'attendance_pct': 0,
                        'missing_dancers': 'RD'
                    })
        
        click.echo(f"\n✓ Venue catalog written to: {output_path}")
    
    except Exception as e:
        click.echo(f"❌ Error writing CSV: {e}", err=True)


if __name__ == '__main__':
    cli()