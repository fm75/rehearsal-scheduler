# rehearsal-scheduler/src/rehearsal_scheduler/grammar_new.py

import inspect
from datetime import time
from lark import Lark, Transformer, v_args

from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint,
    TimeOnDayConstraint
)

DEBUG = False
def type_and_value(obj):                       # pragma: no cover
    """Helper for debugging: returns the type and value of an object."""
    if DEBUG:                                   # pragma: no cover
        return f"{type(obj)}: {repr(obj)}"
    return ""                                   # pragma: no cover

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

    constraint: day_spec (time_spec)?

    day_spec: MONDAY | TUESDAY | WEDNESDAY | THURSDAY | FRIDAY | SATURDAY | SUNDAY

    time_spec: after_spec | before_spec | time_range

    after_spec: "after"i tod
    before_spec: ("before"i | "until"i) tod
    time_range: tod "-" tod

    tod: std_time | military_time
      
    std_time: HOUR (":" MINUTE)? AM_PM?
    military_time: MILITARY_TIME
        
    // TERMINALS 
    // HOUR is lower priority than MILITARY_TIME
    
    MILITARY_TIME.2: /([01][0-9]|2[0-3])[0-5][0-9]/    
    HOUR.1: "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12"
    
    MINUTE : "00" | "01" | "02" | "03" | "04" | "05" | "06" | "07" | "08" | "09" 
           | "10" | "11" | "12" | "13" | "14" | "15" | "16" | "17" | "18" | "19" 
           | "20" | "21" | "22" | "23" | "24" | "25" | "26" | "27" | "28" | "29" 
           | "30" | "31" | "32" | "33" | "34" | "35" | "36" | "37" | "38" | "39" 
           | "40" | "41" | "42" | "43" | "44" | "45" | "46" | "47" | "48" | "49" 
           | "50" | "51" | "52" | "53" | "54" | "55" | "56" | "57" | "58" | "59"

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

    def HOUR(self, h):
        return int(h)

    def MINUTE(self, m):
        return int(m)
        
    def AM_PM(self, am_pm):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(am_pm)}")
        return am_pm.lower()
        
    # --- Day of Week Terminals & Rules ---
    def MONDAY(self, _): return "monday"
    def TUESDAY(self, _): return "tuesday"
    def WEDNESDAY(self, _): return "wednesday"
    def THURSDAY(self, _): return "thursday"
    def FRIDAY(self, _): return "friday"
    def SATURDAY(self, _): return "saturday"
    def SUNDAY(self, _): return "sunday"

    @v_args(inline=False)
    def military_time(self, children):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
        # hour, minute = children
        hour = int(token[0:2])
        minute = int(token[2:4])
        return (hour, minute)

                
    @v_args(inline=False)
    def tod(self, children):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
        if not children:
            return None
        h, m = children[0]
        print(f"h m {h} {m}")
        return time(h, m)


    @v_args(inline=False)
    def std_time(self, children):
        """possible inputs
        h        : 10,11 = am, everything else is pm, m = 0
        h ampm   : h 0 ampm
        h m      : same rule for hours as h 
        h m ampm :
        """
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
        if len(children) == 3:
            h, m, fmt = children
            if fmt == 'pm':
                h += 12
            return (h, m)
        if len(children) == 2:

            
            h, opt = children
            print(f" h opt {h} {opt} {type(opt)}")
            if isinstance(opt, str):
                if opt == 'pm':
                    h += 12
                    if h == 24:
                        h = 12
                else:
                    if h == 12:
                        h = 0
                return (h, 0)
            else:
                if h in [1, 2, 3, 4, 5, 6, 7, 12]:
                     h += 12
                if h == 24:
                    h = 12
                return (h, opt)
        
        h = children[0]
        if h in [1, 2, 3, 4, 5, 6, 7, 12]:
             h += 12
        if h == 24:
            h = 12
        return (h, 0)

    def time_range(self, start_time, end_time):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(start_time)} {type_and_value(end_time)}")
        if start_time >= end_time:
            raise SemanticValidationError(f"Start time {start_time} must be before end time {end_time}.")

        return (start_time, end_time)

    def after_spec(self, start_time):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(start_time)}")
        return (start_time, time(23,59))

    def before_spec(self, end_time):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(end_time)}")
        return (time(0,0), end_time)

    def time_spec(self, time_tuple):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(time_tuple)}")
        return time_tuple

    def AM_PM(self, am_pm):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(am_pm)}")
        return am_pm.lower()

    def day_spec(self, day_of_week_str):
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(day_of_week_str)}")
        return day_of_week_str

    # --- Final Assembly ---

    # **FIX**: Replaced the ambiguous `unavailability_spec` and `day_specs` methods
    # with a single, unambiguous `constraint` method.
    def constraint(self, day_of_week_str, time_spec_tuple=None):
        """
        Processes a single constraint, which is one day and an optional time spec.
        Returns either a DayOfWeekConstraint or a TimeOnDayConstraint.
        """
        if DEBUG:                                # pragma: no cover
            print(f"{inspect.stack()[0][3]}  {type_and_value(day_of_week_str)} {type_and_value(time_spec_tuple)}")
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

def constraint_parser(grammar=GRAMMAR, debug=False):
    constraint_transformer = ConstraintTransformer()
    global DEBUG 
    DEBUG = debug
    return Lark(grammar, 
        parser='lalr', 
        transformer=constraint_transformer,
        debug=debug
        )