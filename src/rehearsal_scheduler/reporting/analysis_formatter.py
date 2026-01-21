"""
Formatters for analysis reports.

Handles display of time analysis and conflict reports.
"""

import sys
from typing import TextIO


class TimeAnalysisFormatter:
    """Formats time analysis results for display."""
    
    def __init__(self, output_stream=None, error_stream=None):
        """
        Initialize formatter.
        
        Args:
            output_stream: Stream for normal output (default: stdout)
            error_stream: Stream for error output (default: stderr)
        """
        self.output = output_stream or sys.stdout
        self.errors = error_stream or sys.stderr
    
    def display_analysis(self, result):
        """
        Display formatted time analysis.
        
        Args:
            result: TimeAnalysisResult object
        """
        self.output.write("=" * 70 + "\n")
        self.output.write("REHEARSAL TIME ANALYSIS\n")
        self.output.write("=" * 70 + "\n")
        
        # Requested time
        self._display_requested_time(result)
        
        # Available time
        self._display_available_time(result)
        
        # Comparison
        self._display_comparison(result)
        
        self.output.write("=" * 70 + "\n")
        self.output.flush()
    
    def _display_requested_time(self, result):
        """Display requested time section."""
        self.output.write("\n📋 TIME REQUESTED\n")
        self.output.write("-" * 70 + "\n")
        
        for rhd_id, data in sorted(result.requests_by_director.items()):
            self.output.write(
                f"\n{rhd_id}: {data['total']:.0f} minutes "
                f"({data['total']/60:.1f} hours)\n"
            )
            for dance in data['dances']:
                self.output.write(
                    f"  • {dance['number_id']}: {dance['minutes']:.0f} min\n"
                )
        
        if result.missing_requests:
            self.output.write(
                f"\n⚠ Missing time requests: {', '.join(result.missing_requests)}\n"
            )
        
        self.output.write(
            f"\n{'TOTAL REQUESTED:':.<50} {result.total_requested:.0f} min "
            f"({result.total_requested/60:.1f} hrs)\n"
        )
    
    def _display_available_time(self, result):
        """Display available time section."""
        self.output.write("\n\n🏢 VENUE AVAILABILITY\n")
        self.output.write("-" * 70 + "\n")
        
        for slot in result.venue_slots:
            self.output.write(f"\n{slot['venue']} - {slot['day']}, {slot['date']}\n")
            self.output.write(f"  {slot['start']} - {slot['end']}\n")
            self.output.write(
                f"  Duration: {slot['duration']} min "
                f"({slot['duration']/60:.1f} hrs)\n"
            )
        
        self.output.write(
            f"\n{'TOTAL AVAILABLE:':.<50} {result.total_available:.0f} min "
            f"({result.total_available/60:.1f} hrs)\n"
        )
    
    def _display_comparison(self, result):
        """Display comparison section."""
        self.output.write("\n\n⚖️  COMPARISON\n")
        self.output.write("=" * 70 + "\n")
        
        if result.has_deficit:
            self.errors.write(
                f"❌ INSUFFICIENT TIME: {result.deficit:.0f} min "
                f"({result.deficit/60:.1f} hrs) SHORT\n"
            )
            self.errors.write(
                f"\nYou need {result.deficit:.0f} more minutes of venue time.\n"
            )
            self.errors.write("Options:\n")
            self.errors.write("  1. Add more venue time slots\n")
            self.errors.write("  2. Reduce requested rehearsal times\n")
            self.errors.write("  3. Poll for additional venue availability\n")
            self.errors.flush()
        elif result.has_surplus:
            self.output.write(
                f"✓ SURPLUS: {result.surplus:.0f} min "
                f"({result.surplus/60:.1f} hrs) extra time available\n"
            )
            self.output.write(f"Venue utilization: {result.utilization_pct:.1f}%\n")
        else:
            self.output.write(
                "✓ PERFECT MATCH: Requested time equals available time\n"
            )
            self.output.write("⚠ Warning: No buffer time for adjustments\n")


class ConflictReportFormatter:
    """Formats conflict report results for display."""
    
    def __init__(self, output_stream=None, error_stream=None):
        """
        Initialize formatter.
        
        Args:
            output_stream: Stream for normal output (default: stdout)
            error_stream: Stream for error output (default: stderr)
        """
        self.output = output_stream or sys.stdout
        self.errors = error_stream or sys.stderr
    
    def display_report(self, report):
        """
        Display formatted conflict report.
        
        Args:
            report: ConflictReport object
        """
        self.output.write("=" * 80 + "\n")
        self.output.write("REHEARSAL DIRECTOR CONFLICT REPORT\n")
        self.output.write("=" * 80 + "\n")
        
        if not report.has_conflicts:
            self.output.write("\n✓ NO CONFLICTS FOUND\n")
            self.output.write("All rehearsal directors are available during all scheduled venue times.\n")
            self.output.flush()
            return
        
        self.output.write(f"\n⚠ Found {report.total_conflicts} potential scheduling conflicts\n")
        self.output.write(f"Rehearsal Directors with conflicts: {', '.join(report.rds_with_conflicts)}\n")
        self.output.write("\n" + "=" * 80 + "\n")
        
        # Group by RD
        conflicts_by_rd = {}
        for conflict in report.conflicts:
            rhd_id = conflict['rhd_id']
            if rhd_id not in conflicts_by_rd:
                conflicts_by_rd[rhd_id] = []
            conflicts_by_rd[rhd_id].append(conflict)
        
        # Display by RD
        for rhd_id in sorted(conflicts_by_rd.keys()):
            self.output.write(f"\n{'─' * 80}\n")
            self.output.write(f"REHEARSAL DIRECTOR: {rhd_id}\n")
            
            # Show all dances for this RD
            all_dances = report.rd_dances.get(rhd_id, [])
            if all_dances:
                self.output.write(f"Responsible for: {', '.join(all_dances)}\n")
            
            self.output.write(f"{'─' * 80}\n")
            
            for conflict in conflicts_by_rd[rhd_id]:
                self.output.write(f"\n  Venue:      {conflict['venue']}\n")
                self.output.write(f"  Date/Time:  {conflict['day']}, {conflict['date']} - {conflict['time_slot']}\n")
                self.output.write(f"  Conflicts:  {', '.join(conflict['conflicting_constraints'])}\n")
                
                # Show affected dances
                if conflict['affected_dances']:
                    self.output.write(f"  Affected:   {', '.join(conflict['affected_dances'])} cannot be scheduled in this slot\n")
                
                self.output.write(f"\n  ⚠ RD {rhd_id} is unavailable during this time slot\n")
                self.output.write(f"  Options:\n")
                self.output.write(f"    • Assign substitute RD for this time slot\n")
                if conflict['affected_dances']:
                    affected_display = ', '.join(conflict['affected_dances'][:3])
                    if len(conflict['affected_dances']) > 3:
                        affected_display += '...'
                    self.output.write(f"    • Do not schedule {affected_display} during this slot\n")
                else:
                    self.output.write(f"    • Do not schedule {rhd_id}'s dances during this slot\n")
        
        self.output.write("\n" + "=" * 80 + "\n")
        self.output.write("\nDIRECTOR ACTIONS:\n")
        self.output.write("  1. Review each conflict and affected dances above\n")
        self.output.write("  2. For each conflict, decide:\n")
        self.output.write("     a) Assign substitute RD and notify them, OR\n")
        self.output.write("     b) Avoid scheduling those dances in conflicted slots\n")
        self.output.write("  3. Update constraints if substitutes are assigned\n")
        self.output.write("  4. Proceed with scheduling\n")
        self.output.write("=" * 80 + "\n")
        self.output.flush()
    
    def write_csv(self, report, output_path):
        """
        Write conflict report to CSV file.
        
        Args:
            report: ConflictReport object
            output_path: Path to write CSV file
        """
        import csv
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'rhd_id', 'venue', 'day', 'date', 'time_slot', 
                    'conflicting_constraints', 'affected_dances'
                ])
                writer.writeheader()
                
                for conflict in report.conflicts:
                    writer.writerow({
                        'rhd_id': conflict['rhd_id'],
                        'venue': conflict['venue'],
                        'day': conflict['day'],
                        'date': conflict['date'],
                        'time_slot': conflict['time_slot'],
                        'conflicting_constraints': ', '.join(conflict['conflicting_constraints']),
                        'affected_dances': ', '.join(conflict['affected_dances'])
                    })
            
            self.output.write(f"\n✓ Conflict report written to: {output_path}\n")
            self.output.flush()
        except Exception as e:
            self.errors.write(f"❌ Error writing CSV: {e}\n")
            self.errors.flush()
            raise