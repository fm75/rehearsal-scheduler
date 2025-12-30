# src/dance_scheduler/scheduler.py

from datetime import datetime
from typing import List

from .conflict_finder import ConflictFinder
from .scheduling_rule import SchedulingRule
from .temporal_parser import TemporalParser


class Scheduler:
    """
    The main class for managing and checking scheduling rules.
    """

    def __init__(self, rules: List[str]):
        """
        Initializes the Scheduler with a list of rule strings.
        """
        self._parser = TemporalParser()
        self.rules: List[SchedulingRule] = [
            self._parser.parse(rule_string) for rule_string in rules
        ]
        self._conflict_finder = ConflictFinder(self.rules)

    def find_conflicts_in_range(
        self, start: datetime, end: datetime
    ) -> List[List[SchedulingRule]]:
        """
        Finds all conflicting rules within a given datetime range.

        This is the method we updated. It now correctly passes the
        list of pre-parsed `SchedulingRule` objects directly to the
        conflict finder, rather than expecting the finder to parse strings.
        """
        return self._conflict_finder.find(start, end)
