# rehearsal-scheduler/src/rehearsal_scheduler/grammar.py

import inspect
from datetime import time
from pprint import pprint

from lark import Lark, Transformer, v_args

from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint,
    TimeOnDayConstraint
)

DEBUG = False

def type_and_value(obj):
    """Helper for debugging: returns the type and value of an object."""
    return f"{type(obj)}: {repr(obj)}"

class SemanticValidationError(ValueError):
    """Custom exception for semantic errors during parsing."""
    pass

# ===================================================================
# GRAMMAR: The fix is a complete redesign to remove ambiguity.
# ===================================================================
GRAMMAR = r"""
    // **FIX**: Redesigned the grammar to be unambiguous.
    ?start: full_spec -> to_tuple

    // A full spec is a list of one or more constraints, separated by commas.
    full_spec: constraint ("," constraint)*

    // A constraint is now simply a single day with an optional time spec.
    // This removes the ambiguity between commas separating days and commas separating constraints.
    constraint: day_spec (time_spec)?

    day_spec: MONDAY | TUESDAY | WEDNESDAY | THURSDAY | FRIDAY | SATURDAY | SUNDAY

    time_spec: after_spec | before_spec | time_range

    after_spec: "after"i time
    before_spec: ("before"i | "until"i) time
    time_range: time "-" time

    time: INT (":" INT)? AM_PM?

    AM_PM: "am"i | "pm"i

    MONDAY:    "monday"i    | "mon"i   | "mo"i | "m"i
    TUESDAY:   "tuesday"i   | "tues"i  | "tu"i
    WEDNESDAY: "wednesday"i | "wed"i   | "we"i | "w"i
    THURSDAY:  "thursday"i  | "thurs"i | "th"i
    FRIDAY:    "friday"i    | "fri"i   | "fr"i | "f"i
    SATURDAY:  "saturday"i  | "sat"i   | "sa"i
    SUNDAY:    "sunday"i    | "sun"i   | "su"i

    %import common.INT
    %import common.WS
    %import common.COMMA
    %ignore WS
"""

@v_args(inline=True)
class ConstraintTransformer(Transformer):
    """Transforms the parsed Lark tree into constraint objects."""

    def INT(self, i):
        return int(i)

    @v_args(inline=False)
    def time(self, children):
        hour = children[0]
        minute = 0
        am_pm = None

        if len(children) > 1:
            if isinstance(children[1], str):
                am_pm = children[1]
            else:
                minute = children[1]
                if len(children) > 2:
                    am_pm = children[2]

        if not (0 <= minute <= 59):
            raise SemanticValidationError(f"Minute must be between 0 and 59, but got {minute}.")

        time_format = "military"
        if am_pm:
            time_format = "ampm"
            if not (1 <= hour <= 12):
                raise SemanticValidationError(f"With am/pm, hour must be between 1 and 12, but got {hour}.")
            if am_pm == 'pm' and hour != 12:
                hour += 12
            elif am_pm == 'am' and hour == 12:
                hour = 0
        else:
            if not (0 <= hour <= 23):
                raise SemanticValidationError(f"Without am/pm, hour must be between 0 and 23, but got {hour}.")

        return (time(hour, minute), time_format)

    def time_range(self, start_tuple, end_tuple):
        start_time, start_format = start_tuple
        end_time, end_format = end_tuple

        if end_format == 'ampm' and start_format == 'military' and end_time.hour >= 12:
            if start_time.hour < 12 and start_time.hour < end_time.hour:
                start_time = start_time.replace(hour=start_time.hour + 12)
        elif start_format == 'ampm' and end_format == 'military':
            if start_time.hour < 12 and end_time < start_time and end_time.hour < 12:
                end_time = end_time.replace(hour=end_time.hour + 12)
        elif start_format == 'military' and end_format == 'military':
            if start_time > end_time:
                end_time = end_time.replace(hour=end_time.hour + 12)
            elif 1 <= start_time.hour <= 7 and start_time < end_time:
                 start_time = start_time.replace(hour=start_time.hour + 12)
                 end_time = end_time.replace(hour=end_time.hour + 12)

        if start_time >= end_time:
            raise SemanticValidationError(f"Start time {start_time} must be before end time {end_time}.")

        return start_time, end_time

    def after_spec(self, time_tuple):
        time_obj, _ = time_tuple
        if time_obj == time(0, 0):
            return (time(0, 0), time(23, 59))
        return (time_obj, time(23, 59))

    def before_spec(self, time_tuple):
        time_obj, _ = time_tuple
        return (time(0, 0), time_obj)

    def time_spec(self, time_tuple):
        return time_tuple

    def AM_PM(self, am_pm):
        return am_pm.lower()

    # --- Day of Week Terminals & Rules ---
    def MONDAY(self, _): return "monday"
    def TUESDAY(self, _): return "tuesday"
    def WEDNESDAY(self, _): return "wednesday"
    def THURSDAY(self, _): return "thursday"
    def FRIDAY(self, _): return "friday"
    def SATURDAY(self, _): return "saturday"
    def SUNDAY(self, _): return "sunday"

    def day_spec(self, day_of_week_str):
        return day_of_week_str

    # --- Final Assembly ---

    # **FIX**: Replaced the ambiguous `unavailability_spec` and `day_specs` methods
    # with a single, unambiguous `constraint` method.
    def constraint(self, day_of_week_str, time_spec_tuple=None):
        """
        Processes a single constraint, which is one day and an optional time spec.
        Returns either a DayOfWeekConstraint or a TimeOnDayConstraint.
        """
        if time_spec_tuple:
            start_time, end_time = time_spec_tuple
            start_time_int = start_time.hour * 100 + start_time.minute
            end_time_int = end_time.hour * 100 + end_time.minute
            return TimeOnDayConstraint(
                day_of_week=day_of_week_str,
                start_time=start_time_int,
                end_time=end_time_int
            )
        else:
            return DayOfWeekConstraint(day_of_week=day_of_week_str)

    # **FIX**: The `full_spec` method is now much simpler as it receives a flat
    # list of constraint objects directly from the parser.
    @v_args(inline=False)
    def full_spec(self, constraints):
        """
        The `constraint*` rule provides a simple list of constraint objects.
        """
        return constraints

    def to_tuple(self, constraints_list):
        return tuple(constraints_list)

def constraint_parser():
    """Builds and returns the Lark parser for constraints."""
    return Lark(GRAMMAR, parser='lalr', transformer=ConstraintTransformer())