"""
Formula builder for Google Sheets.

Converts column-name-based formulas to Google Sheets ArrayFormula syntax.
"""

from typing import List, Dict


def column_letter(col_name: str, columns: List[str]) -> str:
    """
    Convert column name to spreadsheet letter (A-Z).
    
    Args:
        col_name: Name of the column
        columns: Ordered list of all column names
        
    Returns:
        Column letter (A-Z)
        
    Raises:
        ValueError: If column not found or index > 25 (beyond Z)
    """
    if col_name not in columns:
        raise ValueError(f"Column '{col_name}' not found in columns list")
    
    col_index = columns.index(col_name)
    
    if col_index > 25:
        raise ValueError(
            f"Column '{col_name}' is at index {col_index}, "
            f"which exceeds maximum supported column Z (index 25)"
        )
    
    return chr(65 + col_index)


def top_cell(col_name: str, columns: List[str], begin: int = 2) -> str:
    """
    Get the top cell reference for a column.
    
    Args:
        col_name: Name of the column
        columns: Ordered list of all column names
        begin: Starting row number (default 2, after header)
        
    Returns:
        Cell reference (e.g., "C2")
        
    Raises:
        ValueError: If column not found
    """
    letter = column_letter(col_name, columns)
    return f"{letter}{begin}"


def target_column_condition(col_name: str, columns: List[str], end: int, begin: int = 2) -> str:
    """
    Create the ARRAYFORMULA condition part for the target column.
    
    Generates: =ARRAYFORMULA((IF(ISBLANK(C2:C51),"",
    
    Args:
        col_name: Target column name
        columns: Ordered list of all column names
        end: Last row number
        begin: Starting row number (default 2)
        
    Returns:
        Formula condition string
    """
    start_cell = top_cell(col_name, columns, begin)
    col_letter = column_letter(col_name, columns)
    
    return f'=ARRAYFORMULA((IF(ISBLANK({start_cell}:{col_letter}{end}),"",'


def formula_component(rule: str, columns: List[str], end: int, begin: int = 2) -> str:
    """
    Convert column names in formula to range references.
    
    Converts: 'first_name&" "&last_name'
    To: 'B2:B51&" "&C2:C51)))'
    
    Args:
        rule: Formula using column names
        columns: Ordered list of all column names
        end: Last row number
        begin: Starting row number (default 2)
        
    Returns:
        Formula with column references and closing parens
    """
    for col_name in columns:
        if col_name in rule:
            col_letter = column_letter(col_name, columns)
            # Replace column name with range reference
            rule = rule.replace(col_name, f"{col_letter}{begin}:{col_letter}{end}")
    
    # Add closing parentheses for ARRAYFORMULA and IF
    rule += ")))"
    return rule


def build_array_formula(target_col: str, formula_rule: str, columns: List[str], 
                       row_count: int, begin: int = 2) -> tuple[str, str]:
    """
    Build complete ARRAYFORMULA for a column.
    
    Args:
        target_col: Column name where formula will go
        formula_rule: Formula using column names (e.g., 'first_name&" "&last_name')
        columns: Ordered list of all column names
        row_count: Number of data rows
        begin: Starting row (default 2, after header)
        
    Returns:
        Tuple of (cell_reference, formula_string)
        
    Example:
        >>> build_array_formula(
        ...     'full_name', 
        ...     'first_name&" "&last_name',
        ...     ['dancer_id', 'first_name', 'last_name', 'full_name'],
        ...     50
        ... )
        ('D2', '=ARRAYFORMULA((IF(ISBLANK(D2:D51),"",B2:B51&" "&C2:C51)))')
    """
    end = row_count + begin - 1
    
    cell_ref = top_cell(target_col, columns, begin)
    
    condition = target_column_condition(target_col, columns, end, begin)
    component = formula_component(formula_rule, columns, end, begin)
    
    full_formula = condition + component
    
    return cell_ref, full_formula


def build_formulas_for_sheet(columns: List[str], formulas: Dict[str, str], 
                             row_count: int) -> Dict[str, tuple[str, str]]:
    """
    Build all formulas for a sheet.
    
    Args:
        columns: Ordered list of all column names
        formulas: Dict of {column_name: formula_rule}
        row_count: Number of data rows
        
    Returns:
        Dict of {column_name: (cell_reference, formula_string)}
        
    Example:
        >>> build_formulas_for_sheet(
        ...     ['id', 'first', 'last', 'full'],
        ...     {'full': 'first&" "&last'},
        ...     50
        ... )
        {'full': ('D2', '=ARRAYFORMULA((IF(ISBLANK(D2:D51),"",B2:B51&" "&C2:C51)))')}
    """
    result = {}
    
    for col_name, formula_rule in formulas.items():
        try:
            cell_ref, formula = build_array_formula(
                col_name, formula_rule, columns, row_count
            )
            result[col_name] = (cell_ref, formula)
        except ValueError as e:
            print(f"Warning: Skipping formula for '{col_name}': {e}")
            continue
    
    return result
