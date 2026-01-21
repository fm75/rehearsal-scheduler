"""
Conflict analysis domain logic.

Analyzes RD availability conflicts against venue schedule.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ConflictReport:
    """Results from conflict analysis."""
    conflicts: List[Dict[str, Any]]
    rds_with_conflicts: List[str]
    total_conflicts: int
    rd_dances: Dict[str, List[str]]
    
    @property
    def has_conflicts(self) -> bool:
        """Check if any conflicts were found."""
        return self.total_conflicts > 0


class ConflictAnalyzer:
    """Analyzes RD conflicts against venue schedule."""
    
    def __init__(self, validate_token_fn, check_slot_conflicts_fn, parse_date_fn, parse_time_fn, time_to_minutes_fn):
        """
        Initialize analyzer.
        
        Args:
            validate_token_fn: Function to validate constraint tokens
            check_slot_conflicts_fn: Function to check slot conflicts
            parse_date_fn: Function to parse date strings
            parse_time_fn: Function to parse time strings
            time_to_minutes_fn: Function to convert time to minutes
        """
        self.validate_token = validate_token_fn
        self.check_slot_conflicts = check_slot_conflicts_fn
        self.parse_date = parse_date_fn
        self.parse_time = parse_time_fn
        self.time_to_minutes = time_to_minutes_fn
    
    def analyze(
        self,
        rhd_conflicts: List[Dict[str, Any]],
        venue_schedule: List[Dict[str, Any]],
        dance_map: List[Dict[str, Any]]
    ) -> ConflictReport:
        """
        Analyze RD conflicts against venue schedule.
        
        Args:
            rhd_conflicts: List of RD conflict records
            venue_schedule: List of venue schedule records
            dance_map: List of dance-to-RD mapping records
            
        Returns:
            ConflictReport with all conflict data
        """
        # Build RD to dances mapping
        rd_dances = {}
        for row in dance_map:
            dance_id = row.get('dance_id', '').strip()
            rhd_id = row.get('rhd_id', '').strip()
            
            if rhd_id not in rd_dances:
                rd_dances[rhd_id] = []
            if dance_id:
                rd_dances[rhd_id].append(dance_id)
        
        conflicts_found = []
        rds_with_conflicts = set()
        
        # Parse each RD's constraints
        rd_constraints = {}
        for row in rhd_conflicts:
            rhd_id = row.get('rhd_id', '').strip()
            conflicts_text = row.get('conflicts', '').strip()
            
            if not conflicts_text:
                rd_constraints[rhd_id] = []
                continue
            
            # Parse constraint tokens
            tokens = [t.strip() for t in conflicts_text.split(',')]
            parsed_constraints = []
            
            for token in tokens:
                if not token:
                    continue
                result, error = self.validate_token(token)
                if error:
                    # Could log warning about invalid constraint
                    pass
                else:
                    parsed_constraints.append((token, result))
            
            rd_constraints[rhd_id] = parsed_constraints
        
        # Check each venue slot against each RD
        for venue_row in venue_schedule:
            venue = venue_row.get('venue', '')
            day = venue_row.get('day', '')
            date_str = venue_row.get('date', '')
            start_str = venue_row.get('start', '')
            end_str = venue_row.get('end', '')
            
            start_time = self.parse_time(start_str)
            end_time = self.parse_time(end_str)
            
            if not start_time or not end_time:
                continue
            
            # Parse the date
            try:
                slot_date = self.parse_date(date_str)
            except (ValueError, Exception):
                slot_date = None
            
            # Check each RD against this slot
            for rhd_id, constraints in rd_constraints.items():
                if not constraints:
                    continue
                
                slot_conflicts = self.check_slot_conflicts(
                    constraints, day, slot_date, start_time, end_time
                )
                
                if slot_conflicts:
                    rds_with_conflicts.add(rhd_id)
                    conflicts_found.append({
                        'rhd_id': rhd_id,
                        'venue': venue,
                        'day': day,
                        'date': date_str,
                        'time_slot': f"{start_str} - {end_str}",
                        'conflicting_constraints': slot_conflicts,
                        'affected_dances': rd_dances.get(rhd_id, [])
                    })
        
        return ConflictReport(
            conflicts=conflicts_found,
            rds_with_conflicts=sorted(rds_with_conflicts),
            total_conflicts=len(conflicts_found),
            rd_dances=rd_dances
        )