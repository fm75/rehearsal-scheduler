"""Scheduling Constraint Grammar"""

from lark import Lark, Transformer, v_args
from typing import TypeAlias, Optional

import inspect

DEBUG = False


def type_and_value(xxx):
    if DEBUG:                                   # pragma: no cover
        return f" type {type(xxx)} value {xxx}"
    return ""                                   # pragma: no cover


    
# --- Import your data models ---
from .constraints import DayOfWeekConstraint, TimeOnDayConstraint 


constraint_grammar = r"""
    ?start: conflict_text
    
    conflict_text: unavailability_spec ("," unavailability_spec)*

    unavailability_spec: day_spec (time_range)? -> build_unavailability
    
    // --- Time Range Rules ---
    time_range: until_range | after_range | explicit_range
    
    until_range: ("until"i | "before"i ) time -> build_until_range
    after_range: "after"i time                -> build_after_range
    explicit_range: time "-" time             -> build_explicit_range

    time: INT (AM | PM)? -> normalize_time
    
    AM: "am"i
    PM: "pm"i
    
    // A simple day spec (e.g., "Monday") becomes a DayOfWeekConstraint
    day_spec: MONDAY | TUESDAY | WEDNESDAY | THURSDAY | FRIDAY | SATURDAY | SUNDAY
    
    // --- Day of Week Terminals (Unchanged) ---
    MONDAY:    "monday"i    | "mon"i   | "mo"i | "m"i
    TUESDAY:   "tuesday"i   | "tues"i  | "tu"i
    WEDNESDAY: "wednesday"i | "wed"i   | "we"i | "w"i
    THURSDAY:  "thursday"i  | "thurs"i | "th"i
    FRIDAY:    "friday"i    | "fri"i   | "fr"i | "f"i
    SATURDAY:  "saturday"i  | "sat"i   | "sa"i
    SUNDAY:    "sunday"i    | "sun"i   | "su"i

    %import common.INT
    %import common.WS
    %ignore WS
"""


# --- A custom exception for semantic errors ---
class SemanticValidationError(ValueError):
    """Raised when the syntax is valid but the meaning is not."""
    pass


@v_args(inline=True)
class ConstraintTransformer(Transformer):
    def conflict_text(self, *children):
        """
        This method corresponds to the `conflict_text` rule.
        By default, a transformer method receives all transformed children
        as a list. We simply return that list.

        This guarantees that `conflict_text` ALWAYS produces a list,
        whether it parsed "monday" or "monday, tuesday, wednesday".
        """
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} children {type_and_value(children)}")
        return children
    
   
    def build_unavailability(self, day_spec_result, time_range_result=None):
        # The `time_range_result` will be None if the optional `(time_range)?`
        # part was not present in the input string.
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(day_spec_result)} {type_and_value(time_range_result)}")

        if time_range_result is None:
            # Scenario 1: Just a day was provided.
            # `day_spec_result` holds the processed value from your day_spec rule.
            if DEBUG:                                # pragma: no cover
                print(f"Building constraint for the entirety of: {day_spec_result}\n")
            return day_spec_result
            # return [DayOfWeekConstraint(day_spec_result.day_of_week)]
        else:
            # Scenario 2: A day and a time range were provided.
            # `day_spec_result` holds the day.
            # `time_range_result` holds the processed object from your
            # build_until_range, build_after_range, etc. methods.
            if DEBUG:                                # pragma: no cover
                    print(f"Building constraint for day '{day_spec_result}' with time range: {time_range_result}\n")
            return TimeOnDayConstraint(day_spec_result.day_of_week, time_range_result[0], time_range_result[1])
    
    # --- Time Normalization and Validation Helper ---
    def normalize_time(self, hour: int, am_pm: Optional[str] = None) -> int:
        """
        Converts various time formats to a military time integer.
        This is where semantic validation happens!
        """
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(hour)}")
            print(f"{inspect.stack()[0][3]} {type_and_value(am_pm)}")
        hour = int(hour)
        
        if am_pm:
            am_pm = am_pm.lower()
            if not (1 <= hour <= 12):
                raise SemanticValidationError(f"Invalid 12-hour format: Hour '{hour}' must be between 1 and 12.")
            if am_pm == 'pm' and hour < 12:
                hour += 12
            elif am_pm == 'am' and hour == 12: # Midnight case
                hour = 0
        else:
            # Handles military time (e.g., 1400) or simple hours (e.g., 2 in "2-4")
            if hour > 24: # This catches your "after 25" case!
                raise SemanticValidationError(f"Invalid 24-hour format: Hour '{hour}' cannot be greater than 24.")
            if hour >= 1 and hour <= 7: # Heuristic for "2-4" meaning PM
                # If you write "w 2-4", you almost certainly mean 2 PM to 4 PM.
                hour += 12
        
        return hour * 100 # Convert to military time format (e.g., 14 -> 1400)

    # # --- Time Parsing Methods ---
    # def number_only(self, hour_token):
    #     if DEBUG:                                # pragma: no cover
    #         print(f"{inspect.stack()[0][3]} {type_and_value(hour_token)}")
    #     return self.normalize_time(hour_token.value)

    # def number_with_ampm(self, hour_token, am_pm_token):
    #     if DEBUG:                                # pragma: no cover
    #         print(f"{inspect.stack()[0][3]} {type_and_value(hour_token)}")
    #         print(f"{inspect.stack()[0][3]} {type_and_value(am_pm_token)}")
    #     return self.normalize_time(hour_token.value, am_pm_token.value)

    # --- Time Range Builders ---
    def build_until_range(self, end_time):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(end_time)}")
        return (0, end_time) # 0 is the start of the day
        
    # def until_range(self, end_time):
    #     if DEBUG:                                # pragma: no cover
    #         print(f"{inspect.stack()[0][3]} {type_and_value(end_time)}")
    #     return self.build_until_range(end_time)
        
    def build_after_range(self, start_time):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(start_time)}")
        return (start_time, 2359) # 2359 is the end of the day

    def build_explicit_range(self, start_time, end_time):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(start_time)}")
            print(f"{inspect.stack()[0][3]} {type_and_value(end_time)}")
        if start_time >= end_time:
            raise SemanticValidationError(f"Invalid time range: Start time {start_time} must be before end time {end_time}.")
        return (start_time, end_time)

    # def time_on_day_constraint(self, children):
    #     # NOW, this method will correctly receive ['monday', (0, 1200)]
    #     # and the unpacking will succeed.
    #     if DEBUG:                                # pragma: no cover
    #         print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
    #     day_of_week, time_tuple = children
    #     start_time, end_time = time_tuple
             
    # # --- Constraint Object Creation ---
    # def time_on_day_spec(self, day_of_week_obj, time_range_tuple):
    #     # day_of_week_obj is a DayOfWeekConstraint, we just need its string value
    #     if DEBUG:                                # pragma: no cover
    #         print(f"{inspect.stack()[0][3]} {type_and_value(day_of_week_obj)}")
    #         print(f"{inspect.stack()[0][3]} {type_and_value(time_range_tuple)}")
    #     day_str = day_of_week_obj.day_of_week
    #     start_time, end_time = time_range_tuple
    #     return TimeOnDayConstraint(day_str, start_time, end_time)

    # --- Day of Week Rules (now create DayOfWeekConstraint) ---
    def MONDAY(self, _): return DayOfWeekConstraint("monday")
    def TUESDAY(self, _): return DayOfWeekConstraint("tuesday")
    def WEDNESDAY(self, _): return DayOfWeekConstraint("wednesday")
    def THURSDAY(self, _): return DayOfWeekConstraint("thursday")
    def FRIDAY(self, _): return DayOfWeekConstraint("friday")
    def SATURDAY(self, _): return DayOfWeekConstraint("saturday")
    def SUNDAY(self, _): return DayOfWeekConstraint("sunday")

    # --- Structural/Collection Rules ---
    def day_spec(self, day): 
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(day)}")
        return day
    
    # def unavailability_spec(self, *spec): 
    #     if DEBUG:                                # pragma: no cover
    #         print(f"{inspect.stack()[0][3]} {type_and_value(spec)}")
    #     return spec
           
    def time_range(self, children):
        # children will be a list with one item, e.g., [UntilConstraint(...)]
        # We just need to extract that single item from the list.
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
        return children


def constraint_parser(grammar=constraint_grammar, debug=False):
    constraint_transformer = ConstraintTransformer()
    global DEBUG 
    DEBUG = debug
    return Lark(grammar, 
        parser='lalr', 
        transformer=constraint_transformer,
        debug=debug
        )
