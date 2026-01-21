"""
Formatters for venue catalog reports.

Handles display and CSV output of venue availability catalogs.
"""

import csv
import sys
from pathlib import Path


class VenueCatalogFormatter:
    """Formats venue catalog results for display."""
    
    def __init__(self, output_stream=None, error_stream=None):
        """
        Initialize formatter.
        
        Args:
            output_stream: Stream for normal output (default: stdout)
            error_stream: Stream for error output (default: stderr)
        """
        self.output = output_stream or sys.stdout
        self.errors = error_stream or sys.stderr
    
    def display_catalog(self, catalog):
        """
        Display formatted venue catalog.
        
        Args:
            catalog: VenueCatalog object
        """
        self.output.write("\n" + "=" * 80 + "\n")
        self.output.write("VENUE SLOT AVAILABILITY\n")
        self.output.write("=" * 80 + "\n")
        
        for slot_info in catalog.slots:
            self._display_slot(slot_info)
        
        # Summary
        self._display_summary(catalog)
        
        self.output.flush()
    
    def _display_slot(self, slot_info):
        """Display a single slot."""
        self.output.write(f"\n{'═' * 80}\n")
        self.output.write(f"VENUE: {slot_info.venue}\n")
        self.output.write(f"{slot_info.day}, {slot_info.date}\n")
        self.output.write(f"Time: {slot_info.start} - {slot_info.end}\n")
        self.output.write(f"{'═' * 80}\n")
        
        # Conflict-free dances
        if slot_info.conflict_free_dances:
            self.output.write(f"\n✓ CONFLICT-FREE DANCES ({len(slot_info.conflict_free_dances)}):\n")
            self.output.write("  (Can schedule with 100% attendance)\n")
            for dance in slot_info.conflict_free_dances:
                self.output.write(
                    f"  • {dance.dance_id} (RD: {dance.rhd_id}, Cast: {dance.cast_size})\n"
                )
        else:
            self.output.write("\n✓ CONFLICT-FREE DANCES: None\n")
        
        # Cast conflict dances
        if slot_info.cast_conflict_dances:
            self.output.write(f"\n⚠ DANCES WITH CAST CONFLICTS ({len(slot_info.cast_conflict_dances)}):\n")
            self.output.write("  (Can schedule with reduced attendance)\n")
            for dance in slot_info.cast_conflict_dances:
                self.output.write(
                    f"  • {dance.dance_id} (RD: {dance.rhd_id}, "
                    f"Attendance: {dance.attendance_pct:.1f}% - "
                    f"{dance.conflicted_count}/{dance.cast_size} missing)\n"
                )
                if len(dance.conflicted_dancers) <= 5:
                    self.output.write(f"    Missing: {', '.join(dance.conflicted_dancers)}\n")
                else:
                    self.output.write(
                        f"    Missing: {', '.join(dance.conflicted_dancers[:5])}... "
                        f"({len(dance.conflicted_dancers)} total)\n"
                    )
        
        # RD blocked dances
        if slot_info.rd_blocked_dances:
            self.output.write(f"\n❌ RD UNAVAILABLE - CANNOT SCHEDULE ({len(slot_info.rd_blocked_dances)}):\n")
            for dance in slot_info.rd_blocked_dances:
                self.output.write(f"  • {dance.dance_id} (RD: {dance.rhd_id} unavailable)\n")
    
    def _display_summary(self, catalog):
        """Display summary section."""
        self.output.write("\n" + "=" * 80 + "\n")
        self.output.write("SUMMARY\n")
        self.output.write("=" * 80 + "\n")
        
        for i, slot_info in enumerate(catalog.slots, 1):
            self.output.write(f"\nSlot {i} ({slot_info.venue} {slot_info.day}):\n")
            self.output.write(f"  Conflict-free dances: {len(slot_info.conflict_free_dances)}\n")
            self.output.write(f"  Dances with cast conflicts: {len(slot_info.cast_conflict_dances)}\n")
            self.output.write(f"  RD-blocked dances: {len(slot_info.rd_blocked_dances)}\n")
    
    def write_csv(self, catalog, output_path):
        """
        Write venue catalog to CSV file.
        
        Args:
            catalog: VenueCatalog object
            output_path: Path to write CSV file
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'venue', 'day', 'date', 'time_slot', 'dance_id', 'rhd_id',
                    'status', 'attendance_pct', 'missing_dancers'
                ])
                writer.writeheader()
                
                for slot_info in catalog.slots:
                    time_slot = f"{slot_info.start} - {slot_info.end}"
                    
                    # Write conflict-free dances
                    for dance in slot_info.conflict_free_dances:
                        writer.writerow({
                            'venue': slot_info.venue,
                            'day': slot_info.day,
                            'date': slot_info.date,
                            'time_slot': time_slot,
                            'dance_id': dance.dance_id,
                            'rhd_id': dance.rhd_id,
                            'status': 'CONFLICT_FREE',
                            'attendance_pct': 100.0,
                            'missing_dancers': ''
                        })
                    
                    # Write cast conflict dances
                    for dance in slot_info.cast_conflict_dances:
                        writer.writerow({
                            'venue': slot_info.venue,
                            'day': slot_info.day,
                            'date': slot_info.date,
                            'time_slot': time_slot,
                            'dance_id': dance.dance_id,
                            'rhd_id': dance.rhd_id,
                            'status': 'CAST_CONFLICTS',
                            'attendance_pct': dance.attendance_pct,
                            'missing_dancers': ', '.join(dance.conflicted_dancers)
                        })
                    
                    # Write RD blocked dances
                    for dance in slot_info.rd_blocked_dances:
                        writer.writerow({
                            'venue': slot_info.venue,
                            'day': slot_info.day,
                            'date': slot_info.date,
                            'time_slot': time_slot,
                            'dance_id': dance.dance_id,
                            'rhd_id': dance.rhd_id,
                            'status': 'RD_UNAVAILABLE',
                            'attendance_pct': 0,
                            'missing_dancers': 'RD'
                        })
            
            self.output.write(f"\n✓ Venue catalog written to: {output_path}\n")
            self.output.flush()
        except Exception as e:
            self.errors.write(f"❌ Error writing CSV: {e}\n")
            self.errors.flush()
            raise