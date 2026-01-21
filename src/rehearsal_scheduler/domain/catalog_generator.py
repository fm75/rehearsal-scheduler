"""
Venue catalog generation domain logic.

Analyzes which dances can be scheduled in each venue slot.
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class DanceAvailability:
    """Availability info for a single dance."""
    dance_id: str
    rhd_id: str
    cast_size: int
    attendance_pct: float
    conflicted_count: int = 0
    conflicted_dancers: List[str] = None
    
    def __post_init__(self):
        if self.conflicted_dancers is None:
            self.conflicted_dancers = []


@dataclass
class VenueCatalogSlot:
    """Catalog entry for a single venue slot."""
    venue: str
    day: str
    date: str
    start: str
    end: str
    conflict_free_dances: List[DanceAvailability]
    cast_conflict_dances: List[DanceAvailability]
    rd_blocked_dances: List[DanceAvailability]


@dataclass
class VenueCatalog:
    """Complete venue catalog."""
    slots: List[VenueCatalogSlot]
    
    @property
    def total_slots(self) -> int:
        """Get total number of venue slots."""
        return len(self.slots)


class CatalogGenerator:
    """Generates venue availability catalog."""
    
    def __init__(self, validate_token_fn, check_slot_conflicts_fn):
        """
        Initialize generator.
        
        Args:
            validate_token_fn: Function to validate constraint tokens
            check_slot_conflicts_fn: Function to check slot conflicts
        """
        self.validate_token = validate_token_fn
        self.check_slot_conflicts = check_slot_conflicts_fn
    
    def generate(
        self,
        dance_cast: Dict[str, List[str]],
        dancer_constraints: Dict[str, str],
        rhd_constraints: Dict[str, str],
        dance_to_rd: Dict[str, str],
        venue_slots: List[Dict[str, Any]]
    ) -> VenueCatalog:
        """
        Generate venue availability catalog.
        
        Args:
            dance_cast: Dict mapping dance_id to list of dancer_ids
            dancer_constraints: Dict mapping dancer_id to constraints text
            rhd_constraints: Dict mapping rhd_id to constraints text
            dance_to_rd: Dict mapping dance_id to rhd_id
            venue_slots: List of venue schedule records
            
        Returns:
            VenueCatalog with availability for each slot
        """
        catalog_slots = []
        
        for slot in venue_slots:
            slot_info = VenueCatalogSlot(
                venue=slot['venue'],
                day=slot['day'],
                date=slot['date'],
                start=slot['start'],
                end=slot['end'],
                conflict_free_dances=[],
                cast_conflict_dances=[],
                rd_blocked_dances=[]
            )
            
            # Check each dance against this slot
            for dance_id in sorted(dance_cast.keys()):
                cast = dance_cast[dance_id]
                rhd_id = dance_to_rd.get(dance_id, 'Unknown')
                
                # Parse RD constraints
                rd_conflict_text = rhd_constraints.get(rhd_id, '').strip()
                rd_parsed = self._parse_constraints(rd_conflict_text)
                
                # Parse cast constraints
                cast_parsed = {}
                for dancer_id in cast:
                    dancer_conflict_text = dancer_constraints.get(dancer_id, '').strip()
                    if dancer_conflict_text:
                        cast_parsed[dancer_id] = self._parse_constraints(dancer_conflict_text)
                
                # Check RD availability
                rd_has_conflict = bool(self.check_slot_conflicts(rd_parsed, slot))
                
                # Check cast availability
                conflicted_dancers = []
                for dancer_id, constraints in cast_parsed.items():
                    if self.check_slot_conflicts(constraints, slot):
                        conflicted_dancers.append(dancer_id)
                
                # Categorize this dance
                cast_size = len(cast)
                attendance_pct = ((cast_size - len(conflicted_dancers)) / cast_size * 100) if cast_size else 100
                
                if rd_has_conflict:
                    slot_info.rd_blocked_dances.append(DanceAvailability(
                        dance_id=dance_id,
                        rhd_id=rhd_id,
                        cast_size=cast_size,
                        attendance_pct=0,
                        conflicted_count=0,
                        conflicted_dancers=['RD unavailable']
                    ))
                elif len(conflicted_dancers) == 0:
                    slot_info.conflict_free_dances.append(DanceAvailability(
                        dance_id=dance_id,
                        rhd_id=rhd_id,
                        cast_size=cast_size,
                        attendance_pct=100.0,
                        conflicted_count=0,
                        conflicted_dancers=[]
                    ))
                else:
                    slot_info.cast_conflict_dances.append(DanceAvailability(
                        dance_id=dance_id,
                        rhd_id=rhd_id,
                        cast_size=cast_size,
                        attendance_pct=attendance_pct,
                        conflicted_count=len(conflicted_dancers),
                        conflicted_dancers=conflicted_dancers
                    ))
            
            # Sort cast conflict dances by attendance percentage (highest first)
            slot_info.cast_conflict_dances.sort(
                key=lambda x: x.attendance_pct,
                reverse=True
            )
            
            catalog_slots.append(slot_info)
        
        return VenueCatalog(slots=catalog_slots)
    
    def _parse_constraints(self, constraints_text: str) -> List[Any]:
        """Parse constraint tokens."""
        if not constraints_text:
            return []
        
        tokens = [t.strip() for t in constraints_text.split(',')]
        parsed = []
        
        for token in tokens:
            if not token:
                continue
            result, error = self.validate_token(token)
            if not error:
                parsed.append(result)
        
        return parsed