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