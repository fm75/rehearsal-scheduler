"""
Integration tests for scheduling catalog.

Tests the full workflow of generating scheduling catalogs with realistic scenarios.
"""

import pytest
import pandas as pd
from datetime import date

from rehearsal_scheduler.domain.scheduling_catalog import (
    generate_scheduling_catalog,
    find_conflicted_rds,
    find_ineligible_groups,
    find_conflicts_by_group,
    parse_slot_from_row,
    check_constraint_conflicts
)
from rehearsal_scheduler.constraints import (
    RehearsalSlot,
    DayOfWeekConstraint,
    TimeOnDayConstraint,
    DateRangeConstraint
)


class TestParseSlotFromRow:
    """Test parsing rehearsal slots from DataFrame rows."""
    
    def test_parse_slot_basic(self):
        """Test parsing a basic rehearsal slot."""
        row = pd.Series({
            'date': '1-15-26',
            'weekday': 'Monday',
            'start_time': '6:00 PM',
            'end_time': '9:00 PM'
        })
        
        slot = parse_slot_from_row(row)
        
        assert slot.rehearsal_date == date(2026, 1, 15)
        assert slot.day_of_week == 'monday'
        assert slot.start_time == 1800
        assert slot.end_time == 2100
    
    def test_parse_slot_with_integer_times(self):
        """Test parsing slot with military time integers."""
        row = pd.Series({
            'date': '2-24-26',
            'weekday': 'Tuesday',
            'start_time': 1100,
            'end_time': 1600
        })
        
        slot = parse_slot_from_row(row)
        
        assert slot.start_time == 1100
        assert slot.end_time == 1600


class TestCheckConstraintConflicts:
    """Test constraint conflict checking logic."""
    
    def test_day_of_week_conflict(self):
        """Test day of week constraint matching."""
        constraint = DayOfWeekConstraint(day_of_week='monday')
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,
            end_time=2100
        )
        
        assert check_constraint_conflicts(constraint, slot) is True
    
    def test_day_of_week_no_conflict(self):
        """Test day of week constraint not matching."""
        constraint = DayOfWeekConstraint(day_of_week='tuesday')
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,
            end_time=2100
        )
        
        assert check_constraint_conflicts(constraint, slot) is False
    
    def test_time_on_day_conflict(self):
        """Test time range conflict on matching day."""
        constraint = TimeOnDayConstraint(
            day_of_week='monday',
            start_time=1700,  # 5 PM
            end_time=2359     # End of day
        )
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,  # 6 PM
            end_time=2100     # 9 PM
        )
        
        # Overlaps: 6 PM - 9 PM is within 5 PM - 11:59 PM
        assert check_constraint_conflicts(constraint, slot) is True
    
    def test_time_on_day_no_overlap(self):
        """Test time range no overlap on matching day."""
        constraint = TimeOnDayConstraint(
            day_of_week='monday',
            start_time=0,     # Midnight
            end_time=1200     # Noon
        )
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,  # 6 PM
            end_time=2100     # 9 PM
        )
        
        # No overlap: noon vs 6 PM
        assert check_constraint_conflicts(constraint, slot) is False
    
    def test_date_range_conflict(self):
        """Test date range containing slot date."""
        constraint = DateRangeConstraint(
            start_date=date(2026, 2, 20),
            end_date=date(2026, 3, 14)
        )
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 2, 24),  # Within range
            day_of_week='tuesday',
            start_time=1100,
            end_time=1600
        )
        
        assert check_constraint_conflicts(constraint, slot) is True
    
    def test_date_range_no_conflict(self):
        """Test date range not containing slot date."""
        constraint = DateRangeConstraint(
            start_date=date(2026, 2, 20),
            end_date=date(2026, 3, 14)
        )
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),  # Before range
            day_of_week='monday',
            start_time=1800,
            end_time=2100
        )
        
        assert check_constraint_conflicts(constraint, slot) is False


class TestFindConflictedRDs:
    """Test finding conflicted RDs."""
    
    def test_rd_with_day_conflict(self):
        """Test RD with day of week conflict."""
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,
            end_time=2100
        )
        
        rd_constraints_df = pd.DataFrame([
            {'rd_id': 'rd_01', 'full_name': 'Jane Dir', 'constraints': 'Monday'},
            {'rd_id': 'rd_02', 'full_name': 'Bob Dir', 'constraints': 'Tuesday'}
        ])
        
        conflicts = find_conflicted_rds(slot, rd_constraints_df)
        
        assert len(conflicts) == 1
        assert conflicts[0].entity_id == 'rd_01'
        assert conflicts[0].full_name == 'Jane Dir'
        assert 'Monday' in conflicts[0].reason
    
    def test_rd_with_no_conflicts(self):
        """Test RDs with no conflicts."""
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,
            end_time=2100
        )
        
        rd_constraints_df = pd.DataFrame([
            {'rd_id': 'rd_01', 'full_name': 'Jane Dir', 'constraints': 'Tuesday'},
            {'rd_id': 'rd_02', 'full_name': 'Bob Dir', 'constraints': ''}
        ])
        
        conflicts = find_conflicted_rds(slot, rd_constraints_df)
        
        assert len(conflicts) == 0


class TestFindIneligibleGroups:
    """Test finding ineligible dance groups due to RD conflicts."""
    
    def test_groups_with_conflicted_rd(self):
        """Test finding groups whose RD is unavailable."""
        from rehearsal_scheduler.domain.scheduling_catalog import ConflictInfo
        
        rd_conflicts = [
            ConflictInfo('rd_01', 'Jane Dir', 'Monday', 'Monday')
        ]
        
        dance_groups_df = pd.DataFrame([
            {'dg_id': 'd_01', 'dg_name': 'Opening', 'current_rd': 'rd_01', 'current_rd_name': 'Jane Dir'},
            {'dg_id': 'd_02', 'dg_name': 'Jazz', 'current_rd': 'rd_02', 'current_rd_name': 'Bob Dir'},
            {'dg_id': 'd_03', 'dg_name': 'Finale', 'current_rd': 'rd_01', 'current_rd_name': 'Jane Dir'}
        ])
        
        ineligible = find_ineligible_groups(rd_conflicts, dance_groups_df)
        
        assert len(ineligible) == 2
        assert ineligible[0].dg_id == 'd_01'
        assert ineligible[1].dg_id == 'd_03'
        assert all(g.rd_id == 'rd_01' for g in ineligible)


class TestFindConflictsByGroup:
    """Test finding dancer conflicts by dance group."""
    
    def test_dancer_conflicts_in_group(self):
        """Test finding dancers with conflicts in a group."""
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,
            end_time=2100
        )
        
        dance_groups_df = pd.DataFrame([
            {'dg_id': 'd_01', 'dg_name': 'Opening', 'current_rd': 'rd_01', 'current_rd_name': 'Jane'}
        ])
        
        # Group cast matrix: dancers in columns
        group_cast_df = pd.DataFrame(
            {'d_01': ['1', '1', '']},
            index=['dancer_01', 'dancer_02', 'dancer_03']
        )
        group_cast_df.index.name = 'dancer_id'
        
        dancer_constraints_df = pd.DataFrame([
            {'dancer_id': 'dancer_01', 'full_name': 'Alice', 'constraints': 'Monday'},
            {'dancer_id': 'dancer_02', 'full_name': 'Bob', 'constraints': 'Tuesday'},
            {'dancer_id': 'dancer_03', 'full_name': 'Carol', 'constraints': ''}
        ])
        
        ineligible_group_ids = set()
        
        conflicts = find_conflicts_by_group(
            slot,
            dance_groups_df,
            group_cast_df,
            dancer_constraints_df,
            ineligible_group_ids
        )
        
        assert 'd_01' in conflicts
        assert len(conflicts['d_01']) == 1
        assert conflicts['d_01'][0].entity_id == 'dancer_01'
        assert conflicts['d_01'][0].full_name == 'Alice'
    
    def test_skip_ineligible_groups(self):
        """Test that ineligible groups are skipped."""
        slot = RehearsalSlot(
            rehearsal_date=date(2026, 1, 15),
            day_of_week='monday',
            start_time=1800,
            end_time=2100
        )
        
        dance_groups_df = pd.DataFrame([
            {'dg_id': 'd_01', 'dg_name': 'Opening', 'current_rd': 'rd_01', 'current_rd_name': 'Jane'}
        ])
        
        group_cast_df = pd.DataFrame(
            {'d_01': ['1']},
            index=['dancer_01']
        )
        group_cast_df.index.name = 'dancer_id'
        
        dancer_constraints_df = pd.DataFrame([
            {'dancer_id': 'dancer_01', 'full_name': 'Alice', 'constraints': 'Monday'}
        ])
        
        # Mark d_01 as ineligible (RD unavailable)
        ineligible_group_ids = {'d_01'}
        
        conflicts = find_conflicts_by_group(
            slot,
            dance_groups_df,
            group_cast_df,
            dancer_constraints_df,
            ineligible_group_ids
        )
        
        # Should be empty - group was skipped
        assert len(conflicts) == 0


class TestGenerateSchedulingCatalog:
    """Integration test for full catalog generation."""
    
    def test_complete_catalog_generation(self):
        """Test generating complete catalog with realistic data."""
        data = {
            'rehearsals': pd.DataFrame([
                {
                    'date': '1-15-26',
                    'weekday': 'Monday',
                    'start_time': '6:00 PM',
                    'end_time': '9:00 PM',
                    'venue_name': 'Studio A'
                }
            ]),
            'rd_constraints': pd.DataFrame([
                {'rd_id': 'rd_01', 'full_name': 'Jane Dir', 'constraints': 'Monday'}
            ]),
            'dance_groups': pd.DataFrame([
                {'dg_id': 'd_01', 'dg_name': 'Opening', 'current_rd': 'rd_01', 'current_rd_name': 'Jane Dir'},
                {'dg_id': 'd_02', 'dg_name': 'Jazz', 'current_rd': 'rd_02', 'current_rd_name': 'Bob Dir'}
            ]),
            'group_cast': pd.DataFrame(
                {
                    'd_01': ['1', '1'],
                    'd_02': ['', '1']
                },
                index=['dancer_01', 'dancer_02']
            ),
            'dancer_constraints': pd.DataFrame([
                {'dancer_id': 'dancer_01', 'full_name': 'Alice', 'constraints': 'Monday'},
                {'dancer_id': 'dancer_02', 'full_name': 'Bob', 'constraints': ''}
            ])
        }
        
        data['group_cast'].index.name = 'dancer_id'
        
        catalog = generate_scheduling_catalog(data)
        
        assert len(catalog) == 1
        
        entry = catalog[0]
        
        # Should have RD conflict
        assert len(entry.rd_conflicts) == 1
        assert entry.rd_conflicts[0].entity_id == 'rd_01'
        
        # d_01 should be ineligible (Jane is unavailable)
        assert len(entry.ineligible_groups) == 1
        assert entry.ineligible_groups[0].dg_id == 'd_01'
        
        # d_02 should NOT appear in conflicts (Bob is available, no dancers conflict)
        assert 'd_02' not in entry.group_conflicts
        
        # d_01 should NOT appear in dancer conflicts (ineligible)
        assert 'd_01' not in entry.group_conflicts


def test_rd_with_invalid_constraint():
    """Test RD with unparseable constraint shows error."""
    slot = RehearsalSlot(
        rehearsal_date=date(2026, 1, 15),
        day_of_week='monday',
        start_time=1800,
        end_time=2100
    )
    
    rd_constraints_df = pd.DataFrame([
        {'rd_id': 'rd_01', 'full_name': 'Jane', 'constraints': 'invalid garbage @#$'}
    ])
    
    conflicts = find_conflicted_rds(slot, rd_constraints_df)
    
    assert len(conflicts) == 1
    assert 'ERROR' in conflicts[0].reason

def test_dancer_with_invalid_constraint():
    """Test dancer with unparseable constraint shows error."""
    # Similar setup but with bad dancer constraint