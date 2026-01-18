# rehearsal-scheduler/src/rehearsal_scheduler/grammar.py

import inspect
from datetime import time, date
from lark import Lark, Transformer, v_args
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken


from rehearsal_scheduler.constraints import (
    DayOfWeekConstraint,
    TimeOnDayConstraint,
    DateConstraint,
    DateRangeConstraint
)

DEBUG = False

def type_and_value(obj):  # pragma: no cover
    """Helper for debugging: returns the type and value of an object."""
    if DEBUG:
        return f"{type(obj)}: {repr(obj)}"
    return ""

class SemanticValidationError(ValueError):
    """Custom exception for semantic errors during parsing."""
    pass

# Month name to number mapping
MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
    "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
    "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# ===================================================================
# GRAMMAR: Extended to support both temporal and date constraints
# ===================================================================
GRAMMAR = r"""
    ?start: full_spec -> to_tuple

    // A full spec is a list of one or more constraints, separated by commas
    full_spec: constraint ("," constraint)*

    // A constraint can be either temporal (day/time) or date-based
    constraint: temporal_constraint | date_constraint

    // === TEMPORAL CONSTRAINTS (existing) ===
    temporal_constraint: day_spec (time_spec)?

    day_spec: MONDAY | TUESDAY | WEDNESDAY | THURSDAY | FRIDAY | SATURDAY | SUNDAY

    time_spec: after_spec | before_spec | time_range

    after_spec: "after"i tod
    before_spec: ("before"i | "until"i) tod
    time_range: tod "-" tod

    tod: std_time | military_time
      
    std_time: HOUR (":" MINUTE)? AM_PM?
    military_time: MILITARY_TIME

    // === DATE CONSTRAINTS (new) ===
    date_constraint: date_value ("-" date_value)?

    date_value: mdy_slash | mdy_text

    // Format 1: MM/DD/YYYY (year required)
    mdy_slash: MONTH_NUM "/" DAY_NUM "/" YEAR

    // Format 2: "Jan 15 2024" (year required)
    mdy_text: MONTH_TEXT DAY_NUM YEAR
        
    // === TERMINALS ===
    
    // Time terminals
    MILITARY_TIME.2: /([01][0-9]|2[0-3])[0-5][0-9]/    
    HOUR.1: "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12"
    MINUTE: "00" | "01" | "02" | "03" | "04" | "05" | "06" | "07" | "08" | "09" 
          | "10" | "11" | "12" | "13" | "14" | "15" | "16" | "17" | "18" | "19" 
          | "20" | "21" | "22" | "23" | "24" | "25" | "26" | "27" | "28" | "29" 
          | "30" | "31" | "32" | "33" | "34" | "35" | "36" | "37" | "38" | "39" 
          | "40" | "41" | "42" | "43" | "44" | "45" | "46" | "47" | "48" | "49" 
          | "50" | "51" | "52" | "53" | "54" | "55" | "56" | "57" | "58" | "59"
    AM_PM: "am"i | "pm"i

    // Day of week terminals
    MONDAY:    "monday"i    | "mon"i   | "mo"i | "m"i
    TUESDAY:   "tuesday"i   | "tues"i  | "tu"i
    WEDNESDAY: "wednesday"i | "wed"i   | "we"i | "w"i
    THURSDAY:  "thursday"i  | "thurs"i | "th"i
    FRIDAY:    "friday"i    | "fri"i   | "fr"i | "f"i
    SATURDAY:  "saturday"i  | "sat"i   | "sa"i
    SUNDAY:    "sunday"i    | "sun"i   | "su"i

    // Date terminals
    MONTH_TEXT.2: /(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)/i
    YEAR.1: /\d{4}|\d{2}/
    MONTH_NUM.1: /1[0-2]|0?[1-9]/
    DAY_NUM.1: /[12][0-9]|3[01]|0?[1-9]/

    %import common.WS
    %ignore WS
"""

@v_args(inline=True)
class ConstraintTransformer(Transformer):
    """Transforms the parsed Lark tree into constraint objects."""

    # def INT(self, i):
    #     return int(i)

    def HOUR(self, h):
        return int(h)

    def MINUTE(self, m):
        return int(m)
        
    def AM_PM(self, am_pm):
        if DEBUG:                         # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(am_pm)}")
        return am_pm.lower()
        
    # --- Day of Week Terminals ---
    def MONDAY(self, _): return "monday"
    def TUESDAY(self, _): return "tuesday"
    def WEDNESDAY(self, _): return "wednesday"
    def THURSDAY(self, _): return "thursday"
    def FRIDAY(self, _): return "friday"
    def SATURDAY(self, _): return "saturday"
    def SUNDAY(self, _): return "sunday"

    # --- Date Terminals ---
    def YEAR(self, token):
        """Convert year token to int, handling 2-digit years."""
        year_val = int(token)
        if year_val < 100:
            return 2000 + year_val
        return year_val
    
    def MONTH_NUM(self, token):
        return int(token)
    
    def DAY_NUM(self, token):
        return int(token)
    
    def MONTH_TEXT(self, token):
        return MONTH_MAP[token.upper()]

    # --- Time Parsing (existing logic) ---
    @v_args(inline=False)
    def military_time(self, children):
        if DEBUG:                         # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
        token = children[0]
        hour = int(token[0:2])
        minute = int(token[2:4])
        return (hour, minute)

    @v_args(inline=False)
    def tod(self, children):
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
        if not children:  
            # I think this is not possible
            return None           # pragma: no cover
        h, m = children[0]
        return time(h, m)

    @v_args(inline=False)
    def std_time(self, children):
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(children)}")
        if len(children) == 3:
            h, m, fmt = children
            if fmt == 'pm' and h != 12:
                h += 12
            elif fmt == 'am' and h == 12:
                h = 0
            return (h, m)
        if len(children) == 2:
            h, opt = children
            if isinstance(opt, str):
                if opt == 'pm' and h != 12:
                    h += 12
                elif opt == 'am' and h == 12:
                    h = 0
                return (h, 0)
            else:
                if h in [1, 2, 3, 4, 5, 6, 7, 12]:
                    h += 12
                # if h == 24:    Not allowed
                #     h = 12
                return (h, opt)
        
        h = children[0]
        if h in [1, 2, 3, 4, 5, 6, 7, 12]:
            h += 12
        # if h == 24:  Not allowed
        #     h = 12
        return (h, 0)

    def time_range(self, start_time, end_time):
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(start_time)} {type_and_value(end_time)}")
        if start_time >= end_time:
            raise SemanticValidationError(f"Start time {start_time} must be before end time {end_time}.")
        return (start_time, end_time)

    def after_spec(self, start_time):
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(start_time)}")
        return (start_time, time(23, 59))

    def before_spec(self, end_time):
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(end_time)}")
        return (time(0, 0), end_time)

    def time_spec(self, time_tuple):
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(time_tuple)}")
        return time_tuple

    def day_spec(self, day_of_week_str):
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(day_of_week_str)}")
        return day_of_week_str

    # --- Date Parsing (new) ---
    def _resolve_date(self, month, day, year):
        """Create date object and validate it."""
        try:
            return date(year, month, day)
        except ValueError as e:
            raise ValueError(f"Invalid date: {e}")

    def mdy_slash(self, month, day, year):
        """Process MM/DD/YYYY format."""
        return self._resolve_date(month, day, year)
    
    def mdy_text(self, month, day, year):
        """Process 'Jan 15 2026' format."""
        return self._resolve_date(month, day, year)
    
    def date_value(self, date_obj):
        return date_obj

    def date_constraint(self, *dates):
        """Process single date or date range."""
        if len(dates) == 1:
            # Single date
            return DateConstraint(date=dates[0])
        else:
            # Date range
            start_date, end_date = dates
            if end_date < start_date:
                raise SemanticValidationError(
                    f"Invalid range: end date {end_date} is before start date {start_date}"
                )
            return DateRangeConstraint(start_date=start_date, end_date=end_date)

    def constraint(self, constraint_obj):
        """Unwrap the constraint - it's either temporal or date-based."""
        if DEBUG:                          # pragma: no cover
            print(f"{inspect.stack()[0][3]} {type_and_value(constraint_obj)}")
        return constraint_obj

    # --- Temporal Constraint Assembly (existing) ---
    def temporal_constraint(self, day_of_week_str, time_spec_tuple=None):
        """
        Processes a temporal constraint: day and optional time spec.
        Returns either a DayOfWeekConstraint or a TimeOnDayConstraint.
        """
        if DEBUG:                          # pragma: no cover
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

    # --- Final Assembly ---
    @v_args(inline=False)
    def full_spec(self, constraints):
        """The constraint* rule provides a list of constraint objects."""
        return constraints

    def to_tuple(self, constraints_list):
        return tuple(constraints_list)


def constraint_parser(grammar=GRAMMAR, debug=False):
    constraint_transformer = ConstraintTransformer()
    global DEBUG 
    DEBUG = debug
    return Lark(
        grammar, 
        parser='lalr', 
        transformer=constraint_transformer,
        debug=debug
    )


def unexpected_input_message(token, exc):    # pragma: no cover
    # I have not found a case to trigger this...
    pointer = exc.column * " " + "^"
    emsg = f"{token}\n{pointer}\nExpected: {exc.expected}"
    return emsg


def value_error_message(token, exc):
    emsg = f"{token}: {exc}"
    return emsg


def unexpected_characters_message(token, exc):
    pointer = exc.column * " " + "^"
    emsg = f"{token}\n{pointer}\nExpected one of {exc.allowed}"
    return emsg


def unexpected_token_message(token, exc):
    pointer = (exc.column-1) * " " + "^"
    emsg = f"{token}\n{pointer}\nExpected: {exc.expected}"
    return emsg


def validate_token(token: str):
    parser = constraint_parser()
    try:
        result = parser.parse(token)
        return result, None
    except ValueError as e:
        return None, value_error_message(token, e)
    except UnexpectedToken as e:
        return None, unexpected_token_message(token, e)
    except UnexpectedCharacters as e:
        return None, unexpected_characters_message(token, e)
    except UnexpectedInput as e:
        # I have not found a case to trigger this...
        return None, unexpected_input_message(token, e)
