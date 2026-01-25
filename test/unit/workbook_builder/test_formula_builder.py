"""
Tests for workbook_builder/formula_builder.py

Tests the formula generation logic for Google Sheets.
"""

import pytest
from rehearsal_scheduler.workbook_builder.formula_builder import (
    column_letter,
    top_cell,
    target_column_condition,
    formula_component,
    build_array_formula,
    build_formulas_for_sheet
)


# ============================================================================
# column_letter Tests
# ============================================================================

def test_column_letter_first_column():
    """Test getting letter for first column."""
    columns = ['id', 'name', 'email']
    assert column_letter('id', columns) == 'A'


def test_column_letter_middle_column():
    """Test getting letter for middle column."""
    columns = ['id', 'name', 'email']
    assert column_letter('name', columns) == 'B'


def test_column_letter_last_column():
    """Test getting letter for last column."""
    columns = ['id', 'name', 'email']
    assert column_letter('email', columns) == 'C'


def test_column_letter_column_z():
    """Test getting letter for column Z (index 25)."""
    columns = [f'col{i}' for i in range(26)]
    assert column_letter('col25', columns) == 'Z'


def test_column_letter_not_found():
    """Test error when column not in list."""
    columns = ['id', 'name', 'email']
    
    with pytest.raises(ValueError, match="Column 'invalid' not found"):
        column_letter('invalid', columns)


def test_column_letter_beyond_z():
    """Test error when column index > 25."""
    columns = [f'col{i}' for i in range(27)]
    
    with pytest.raises(ValueError, match="exceeds maximum supported column Z"):
        column_letter('col26', columns)


# ============================================================================
# top_cell Tests
# ============================================================================

def test_top_cell_default_begin():
    """Test top cell with default begin row (2)."""
    columns = ['id', 'name', 'email']
    assert top_cell('name', columns) == 'B2'


def test_top_cell_custom_begin():
    """Test top cell with custom begin row."""
    columns = ['id', 'name', 'email']
    assert top_cell('email', columns, begin=5) == 'C5'


def test_top_cell_first_column():
    """Test top cell for first column."""
    columns = ['id', 'name']
    assert top_cell('id', columns) == 'A2'


# ============================================================================
# target_column_condition Tests
# ============================================================================

def test_target_column_condition_basic():
    """Test basic target column condition generation."""
    columns = ['id', 'first', 'last', 'full']
    result = target_column_condition('full', columns, end=51)
    
    assert result == '=ARRAYFORMULA((IF(ISBLANK(D2:D51),"",'


def test_target_column_condition_first_column():
    """Test condition for first column."""
    columns = ['id', 'name']
    result = target_column_condition('id', columns, end=100)
    
    assert result == '=ARRAYFORMULA((IF(ISBLANK(A2:A100),"",'


def test_target_column_condition_custom_begin():
    """Test condition with custom begin row."""
    columns = ['id', 'name']
    result = target_column_condition('name', columns, end=100, begin=10)
    
    assert result == '=ARRAYFORMULA((IF(ISBLANK(B10:B100),"",'


# ============================================================================
# formula_component Tests
# ============================================================================

def test_formula_component_simple():
    """Test simple formula component with one column."""
    columns = ['id', 'value']
    result = formula_component('value*2', columns, end=51)
    
    assert result == 'B2:B51*2)))'


def test_formula_component_concatenation():
    """Test formula with string concatenation."""
    columns = ['id', 'first', 'last']
    result = formula_component('first&" "&last', columns, end=51)
    
    assert result == 'B2:B51&" "&C2:C51)))'


def test_formula_component_complex():
    """Test complex formula with multiple operations."""
    columns = ['a', 'b', 'c']
    result = formula_component('a+b*c', columns, end=100)
    
    assert result == 'A2:A100+B2:B100*C2:C100)))'


def test_formula_component_custom_begin():
    """Test formula component with custom begin row."""
    columns = ['x', 'y']
    result = formula_component('x+y', columns, end=20, begin=5)
    
    assert result == 'A5:A20+B5:B20)))'


def test_formula_component_no_column_references():
    """Test formula with no column references."""
    columns = ['id', 'name']
    result = formula_component('"constant"', columns, end=10)
    
    # Should just add closing parens
    assert result == '"constant")))'


# ============================================================================
# build_array_formula Tests
# ============================================================================

def test_build_array_formula_full_name():
    """Test building full_name formula."""
    columns = ['dancer_id', 'first_name', 'last_name', 'full_name']
    cell_ref, formula = build_array_formula(
        'full_name',
        'first_name&" "&last_name',
        columns,
        50
    )
    
    assert cell_ref == 'D2'
    assert formula == '=ARRAYFORMULA((IF(ISBLANK(D2:D51),"",B2:B51&" "&C2:C51)))'


def test_build_array_formula_calculation():
    """Test building calculation formula."""
    columns = ['id', 'hours', 'rate', 'total']
    cell_ref, formula = build_array_formula(
        'total',
        'hours*rate',
        columns,
        100
    )
    
    assert cell_ref == 'D2'
    assert formula == '=ARRAYFORMULA((IF(ISBLANK(D2:D101),"",B2:B101*C2:C101)))'


def test_build_array_formula_duration():
    """Test building duration formula (from dances.yaml)."""
    columns = ['dance_id', 'name', 'music', 'duration', 'minutes', 'seconds', 'duration_seconds']
    cell_ref, formula = build_array_formula(
        'duration',
        'TO_TEXT(minutes)&":"&TO_TEXT(seconds)',
        columns,
        50
    )
    
    assert cell_ref == 'D2'
    assert 'E2:E51' in formula  # minutes
    assert 'F2:F51' in formula  # seconds
    assert 'TO_TEXT' in formula


def test_build_array_formula_custom_row_count():
    """Test with different row count."""
    columns = ['a', 'b', 'c']
    cell_ref, formula = build_array_formula(
        'c',
        'a+b',
        columns,
        25
    )
    
    assert cell_ref == 'C2'
    assert 'C2:C26' in formula  # 25 rows means row 2-26


# ============================================================================
# build_formulas_for_sheet Tests
# ============================================================================

def test_build_formulas_for_sheet_single():
    """Test building formulas for sheet with single formula."""
    columns = ['id', 'first', 'last', 'full']
    formulas = {'full': 'first&" "&last'}
    
    result = build_formulas_for_sheet(columns, formulas, 50)
    
    assert 'full' in result
    assert result['full'][0] == 'D2'
    assert 'B2:B51' in result['full'][1]  # first_name range


def test_build_formulas_for_sheet_multiple():
    """Test building multiple formulas."""
    columns = ['id', 'min', 'sec', 'duration', 'duration_sec']
    formulas = {
        'duration': 'TO_TEXT(min)&":"&TO_TEXT(sec)',
        'duration_sec': '60*min+sec'
    }
    
    result = build_formulas_for_sheet(columns, formulas, 50)
    
    assert len(result) == 2
    assert 'duration' in result
    assert 'duration_sec' in result


def test_build_formulas_for_sheet_empty():
    """Test with no formulas."""
    columns = ['id', 'name']
    formulas = {}
    
    result = build_formulas_for_sheet(columns, formulas, 50)
    
    assert result == {}


def test_build_formulas_for_sheet_invalid_column():
    """Test handling of invalid column in formula."""
    columns = ['id', 'name']
    formulas = {'result': 'invalid_column*2'}  # invalid_column doesn't exist
    
    # Should skip the formula and print warning
    result = build_formulas_for_sheet(columns, formulas, 50)
    
    # Should be empty since formula was skipped
    assert result == {}


def test_build_formulas_for_sheet_dancers_example():
    """Test with realistic dancers example."""
    columns = ['dancer_id', 'first_name', 'last_name', 'full_name', 'email', 'cell']
    formulas = {'full_name': 'first_name&" "&last_name'}
    
    result = build_formulas_for_sheet(columns, formulas, 50)
    
    assert len(result) == 1
    cell_ref, formula_str = result['full_name']
    assert cell_ref == 'D2'
    assert 'B2:B51' in formula_str  # first_name
    assert 'C2:C51' in formula_str  # last_name


# ============================================================================
# Integration Tests
# ============================================================================

def test_formula_round_trip():
    """Test complete formula building process."""
    columns = ['id', 'a', 'b', 'sum', 'product']
    formulas = {
        'sum': 'a+b',
        'product': 'a*b'
    }
    
    result = build_formulas_for_sheet(columns, formulas, 10)
    
    # Both formulas should be built
    assert len(result) == 2
    
    # Check sum formula
    sum_cell, sum_formula = result['sum']
    assert sum_cell == 'D2'
    assert 'B2:B11' in sum_formula
    assert 'C2:C11' in sum_formula
    
    # Check product formula
    prod_cell, prod_formula = result['product']
    assert prod_cell == 'E2'
    assert 'B2:B11' in prod_formula
    assert 'C2:C11' in prod_formula


def test_edge_case_single_row():
    """Test with only one data row."""
    columns = ['id', 'value', 'doubled']
    formulas = {'doubled': 'value*2'}
    
    result = build_formulas_for_sheet(columns, formulas, 1)
    
    cell_ref, formula = result['doubled']
    assert cell_ref == 'C2'
    assert 'C2:C2' in formula  # Only one row
