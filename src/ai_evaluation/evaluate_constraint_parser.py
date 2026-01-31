#!/usr/bin/env python3
"""
Constraint Parser Evaluation Framework

Tests multiple LLMs with different prompts against test cases to find
optimal model/prompt combination for constraint parsing.

Usage:
    # Phase 1: Discover working models
    python evaluate_constraint_parser.py discover
    
    # Phase 2: Run full evaluation
    python evaluate_constraint_parser.py evaluate --output results.csv
    
    # Phase 3: Analyze results
    python evaluate_constraint_parser.py analyze results.csv
"""

import os
import sys
import time
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import click
import anthropic
from google import genai


# =============================================================================
# Configuration
# =============================================================================

ANTHROPIC_MODELS = [
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514", 
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-20251001",
    "claude-haiku-4-5-20251001",
    "claude-3-5-sonnet-20241022",
    # "claude-3-5-haiku-20241022",
]

GEMINI_MODELS = [
    "gemini-3.0-pro-preview",
    "gemini-2.5-pro",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-thinking-exp",
    "gemini-exp-1206",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

# Grammar definition
LARK_GRAMMAR = """
start: constraint ("," constraint)*
constraint: temporal_constraint | date_constraint

temporal_constraint: day_spec (time_spec)?
day_spec: MONDAY | TUESDAY | WEDNESDAY | THURSDAY | FRIDAY | SATURDAY | SUNDAY
time_spec: after_spec | before_spec | time_range
after_spec: "after"i tod
before_spec: ("before"i | "until"i) tod
time_range: tod "-" tod
tod: std_time | military_time
std_time: HOUR (":" MINUTE)? AM_PM?
military_time: MILITARY_TIME

date_constraint: date_value (time_spec)? | date_value ("-" date_value)?
date_value: mdy_slash | mdy_text
mdy_slash: MONTH_NUM "/" DAY_NUM "/" YEAR
mdy_text: MONTH_TEXT DAY_NUM YEAR
    
MILITARY_TIME.2: /([01][0-9]|2[0-3])[0-5][0-9]/    
HOUR.1: "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "10" | "11" | "12"
MINUTE: "00" | "01" | "02" | ... | "59"
AM_PM: "am"i | "pm"i
MONDAY:    "monday"i    | "mon"i   | "mo"i | "m"i
TUESDAY:   "tuesday"i   | "tues"i  | "tu"i
WEDNESDAY: "wednesday"i | "wed"i   | "we"i | "w"i
THURSDAY:  "thursday"i  | "thurs"i | "th"i
FRIDAY:    "friday"i    | "fri"i   | "fr"i | "f"i
SATURDAY:  "saturday"i  | "sat"i   | "sa"i
SUNDAY:    "sunday"i    | "sun"i   | "su"i
MONTH_TEXT.2: /(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)/i
YEAR.1: /\\d{4}|\\d{2}/
MONTH_NUM.1: /1[0-2]|0?[1-9]/
DAY_NUM.1: /[12][0-9]|3[01]|0?[1-9]/
"""


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TestCase:
    """A single test case."""
    input: str
    expected: str
    category: str  # 'natural', 'conforming', 'edge_case'
    description: str = ""


@dataclass
class EvaluationResult:
    """Result of a single evaluation."""
    test_case: str
    category: str
    model: str
    prompt_version: str
    input_text: str
    expected_output: str
    actual_output: str
    success: bool
    latency_ms: float
    error: Optional[str] = None
    timestamp: str = ""


# =============================================================================
# Test Cases
# =============================================================================

TEST_CASES = [
    # Conforming (already in grammar format)
    TestCase("Monday", "Monday", "conforming", "Simple day"),
    TestCase("M after 5pm", "Monday after 5:00 pm", "conforming", "Day with time"),
    TestCase("W before 10am", "Wednesday before 10:00 am", "conforming", "Before time"),
    TestCase("F 11:30am-1pm", "Friday 11:30 am-1:00 pm", "conforming", "Time range"),
    TestCase("Jan 15 2026", "Jan 15 2026", "conforming", "Date"),
    TestCase("Mar 15 2026-Mar 20 2026", "Mar 15 2026-Mar 20 2026", "conforming", "Date range"),
    TestCase("Feb 2 2026 after 2pm", "Feb 2 2026 after 2:00 pm", "conforming", "Date with time"),
    
    # Natural language (needs interpretation)
    TestCase("I can't make it Mondays", "Monday", "natural", "Casual unavailability"),
    TestCase("unavailable tuesdays after 5", "Tuesday after 5:00 pm", "natural", "Missing PM"),
    TestCase("Can't do Wed before 6", "Wednesday before 6:00 pm", "natural", "Casual + ambiguous time"),
    TestCase("out of town march 15-20", "Mar 15 2026-Mar 20 2026", "natural", "Casual date range"),
    TestCase("I have a doctor appointment Feb 2 after 2", "Feb 2 2026 after 2:00 pm", "natural", "Context with date/time"),
    TestCase("mondays and fridays I work late", "Monday, Friday", "natural", "Multiple days"),
    TestCase("m, f before 5", "Monday, Friday before 5:00 pm", "natural", "Abbreviated multiple"),
    
    # Edge cases
    TestCase("", "NO IDEA", "edge", "Empty input"),
    TestCase("asdfghjkl", "NO IDEA", "edge", "Gibberish"),
    TestCase("maybe tuesday?", "Tuesday", "edge", "Uncertain language"),
    TestCase("M after 5, W before 10", "Monday after 5:00 pm, Wednesday before 10:00 am", "edge", "Multiple complex"),
]


# =============================================================================
# Prompt Templates
# =============================================================================

def get_prompt_v1(grammar: str, user_input: str) -> str:
    """Original prompt from JS version."""
    return f"""You are a Strict Parsing Engine.
Your goal is to convert natural language availability into a string that strictly satisfies the LARK GRAMMAR below.

### LARK GRAMMAR:
{grammar}

### CONTEXT
- Dancers are 55+ (retired/working mixed).
- "Before 6" usually means PM.
- "After 5" always means PM.
- The input was their natural language response to a request for when they would not be available to rehearse.

### EXAMPLES (Human -> EBNF):
Input: "Wed"
Output: Wednesday

Input: "mon, fri before 5"
Output: Monday, Friday before 5:00 pm

Input: "jan 5 26"
Output: Jan 5 26

Input: "I can't do tuesdays after 8pm"
Output: Tuesday after 8:00 pm

Input: "Feb 2 26 before 1pm"
Output: Feb 2 26 before 1:00 pm

### CRITICAL:
- Output ONLY the final grammar string. 
- If you are not sure what the input means, return "NO IDEA".

Input: {user_input}
Output:"""


def get_prompt_v2(grammar: str, user_input: str) -> str:
    """Simplified prompt."""
    return f"""Convert dancer unavailability to this grammar format:

GRAMMAR:
{grammar}

RULES:
- Output ONLY the converted string
- Times without AM/PM default to PM for "after 5" or "before 6"
- If unclear, output "NO IDEA"
- Current year is 2026

EXAMPLES:
"I can't do Mondays" → Monday
"wed before 6" → Wednesday before 6:00 pm
"march 15-20" → Mar 15 2026-Mar 20 2026

Convert: {user_input}"""


PROMPT_VERSIONS = {
    'v1_detailed': get_prompt_v1,
    'v2_simple': get_prompt_v2,
}


# =============================================================================
# LLM Clients
# =============================================================================

def call_anthropic(model: str, prompt: str) -> Tuple[str, float, Optional[str]]:
    """Call Anthropic API and return (response, latency_ms, error)."""
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            return "", 0, "ANTHROPIC_API_KEY not set"
        
        client = anthropic.Anthropic(api_key=api_key)
        
        start = time.time()
        message = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )
        latency = (time.time() - start) * 1000
        
        response = message.content[0].text.strip()
        return response, latency, None
        
    except Exception as e:
        return "", 0, str(e)


def call_gemini(model: str, prompt: str) -> Tuple[str, float, Optional[str]]:
    """Call Gemini API and return (response, latency_ms, error)."""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return "", 0, "GEMINI_API_KEY not set"
        
        client = genai.Client(api_key=api_key)
        
        start = time.time()
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        latency = (time.time() - start) * 1000
        
        return response.text.strip(), latency, None
        
    except Exception as e:
        return "", 0, str(e)


# =============================================================================
# Phase 1: Model Discovery
# =============================================================================

@click.group()
def cli():
    """Constraint parser evaluation framework."""
    pass


@cli.command()
def discover():
    """Discover which models are accessible."""
    click.echo(click.style("\n=== Phase 1: Model Discovery ===\n", fg='blue', bold=True))
    
    results = {'anthropic': {}, 'gemini': {}}
    
    # Test Anthropic
    click.echo("Testing Anthropic models...")
    for model in ANTHROPIC_MODELS:
        click.echo(f"  {model}...", nl=False)
        response, latency, error = call_anthropic(model, "Say 'OK'")
        
        if error:
            click.echo(click.style(f" ✗ {error}", fg='red'))
            results['anthropic'][model] = {'available': False, 'error': error}
        else:
            click.echo(click.style(f" ✓ ({latency:.0f}ms)", fg='green'))
            results['anthropic'][model] = {'available': True, 'latency': latency}
    
    # Test Gemini
    click.echo("\nTesting Gemini models...")
    for model in GEMINI_MODELS:
        click.echo(f"  {model}...", nl=False)
        response, latency, error = call_gemini(model, "Say 'OK'")
        
        if error:
            click.echo(click.style(f" ✗ {error}", fg='red'))
            results['gemini'][model] = {'available': False, 'error': error}
        else:
            click.echo(click.style(f" ✓ ({latency:.0f}ms)", fg='green'))
            results['gemini'][model] = {'available': True, 'latency': latency}
    
    # Save results
    with open('model_discovery.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    click.echo(click.style("\n✓ Results saved to model_discovery.json\n", fg='green'))


# =============================================================================
# Phase 2: Evaluation
# =============================================================================

@cli.command()
@click.option('--output', default='evaluation_results.csv', help='Output CSV file')
@click.option('--models', help='Comma-separated list of models (or leave empty for all working)')
@click.option('--prompts', help='Comma-separated prompt versions (default: all)')
@click.option('--verbose', is_flag=True, help='Show detailed prompt/response info')
@click.option('--limit', type=int, help='Limit number of test cases (for quick testing)')
def evaluate(output, models, prompts, verbose, limit):
    """Run full evaluation matrix."""
    click.echo(click.style("\n=== Phase 2: Evaluation ===\n", fg='blue', bold=True))
    
    # Load working models from discovery
    try:
        with open('model_discovery.json') as f:
            discovery = json.load(f)
        
        working_models = []
        for provider, models_dict in discovery.items():
            for model, info in models_dict.items():
                if info['available']:
                    working_models.append((provider, model))
        
        click.echo(f"Found {len(working_models)} working models from discovery")
    except FileNotFoundError:
        click.echo(click.style("⚠ model_discovery.json not found. Run 'discover' first.", fg='yellow'))
        return
    
    # Select prompts to test
    prompt_versions = list(PROMPT_VERSIONS.keys()) if not prompts else prompts.split(',')
    
    # Limit test cases if requested
    test_cases = TEST_CASES[:limit] if limit else TEST_CASES
    
    click.echo(f"Testing {len(prompt_versions)} prompt versions: {', '.join(prompt_versions)}")
    click.echo(f"Running {len(test_cases)} test cases")
    click.echo(f"Total evaluations: {len(working_models)} × {len(prompt_versions)} × {len(test_cases)} = {len(working_models) * len(prompt_versions) * len(test_cases)}\n")
    
    # Confirm before running
    if not click.confirm("This will make API calls. Continue?"):
        return
    
    results = []
    total = len(working_models) * len(prompt_versions) * len(test_cases)
    count = 0
    
    # Run evaluation matrix
    for provider, model in working_models:
        click.echo(click.style(f"\n📊 Testing {model}...", fg='cyan', bold=True))
        
        for prompt_name in prompt_versions:
            click.echo(f"  Prompt: {prompt_name}")
            
            for test_case in test_cases:
                count += 1
                click.echo(f"    [{count}/{total}] {test_case.description}...", nl=False)
                
                # Build prompt
                prompt_func = PROMPT_VERSIONS[prompt_name]
                prompt = prompt_func(LARK_GRAMMAR, test_case.input)
                
                if verbose:
                    click.echo(f"\n      Input: {test_case.input}")
                    click.echo(f"      Expected: {test_case.expected}")
                
                # Call LLM
                if provider == 'anthropic':
                    response, latency, error = call_anthropic(model, prompt)
                else:  # gemini
                    response, latency, error = call_gemini(model, prompt)
                
                if verbose:
                    click.echo(f"      Actual: {response}")
                    if error:
                        click.echo(f"      Error: {error}")
                
                # Check success - flexible matching
                success = False
                if not error and response:
                    # Very lenient check - just see if it's not gibberish
                    # Real validation would parse with your actual grammar
                    response_clean = response.strip().lower()
                    expected_clean = test_case.expected.strip().lower()
                    
                    # Consider it success if it's close or contains key parts
                    if response_clean == expected_clean:
                        success = True
                    elif test_case.category == 'edge' and response_clean == 'no idea':
                        success = True
                    # Add more flexible matching here
                
                # Record result
                result = EvaluationResult(
                    test_case=test_case.description,
                    category=test_case.category,
                    model=model,
                    prompt_version=prompt_name,
                    input_text=test_case.input,
                    expected_output=test_case.expected,
                    actual_output=response,
                    success=success,
                    latency_ms=latency,
                    error=error,
                    timestamp=datetime.now().isoformat()
                )
                results.append(result)
                
                # Show result
                if error:
                    click.echo(click.style(f" ✗ ERROR", fg='red'))
                elif success:
                    click.echo(click.style(f" ✓ ({latency:.0f}ms)", fg='green'))
                else:
                    click.echo(click.style(f" ✗ Wrong ({latency:.0f}ms)", fg='yellow'))
                
                if not verbose:
                    # Small delay to avoid rate limits
                    time.sleep(0.5)
    
    # Save results to CSV
    click.echo(click.style(f"\n💾 Saving results to {output}...", fg='blue'))
    
    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'model', 'prompt_version', 'category', 'test_case',
            'input_text', 'expected_output', 'actual_output', 'success', 
            'latency_ms', 'error'
        ])
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))
    
    # Quick summary
    total_tests = len(results)
    successful = sum(1 for r in results if r.success)
    success_rate = (successful / total_tests * 100) if total_tests > 0 else 0
    
    click.echo(click.style(f"\n✓ Evaluation complete!", fg='green', bold=True))
    click.echo(f"  Total tests: {total_tests}")
    click.echo(f"  Successful: {successful} ({success_rate:.1f}%)")
    click.echo(f"  Results saved to: {output}\n")
    
    # Load working models from discovery
    try:
        with open('model_discovery.json') as f:
            discovery = json.load(f)
        
        working_models = []
        for provider, models_dict in discovery.items():
            for model, info in models_dict.items():
                if info['available']:
                    working_models.append((provider, model))
        
        click.echo(f"Found {len(working_models)} working models from discovery")
    except FileNotFoundError:
        click.echo(click.style("⚠ model_discovery.json not found. Run 'discover' first.", fg='yellow'))
        return
    
    # Select prompts to test
    prompt_versions = list(PROMPT_VERSIONS.keys()) if not prompts else prompts.split(',')
    
    click.echo(f"Testing {len(prompt_versions)} prompt versions: {', '.join(prompt_versions)}")
    click.echo(f"Running {len(TEST_CASES)} test cases")
    click.echo(f"Total evaluations: {len(working_models)} × {len(prompt_versions)} × {len(TEST_CASES)} = {len(working_models) * len(prompt_versions) * len(TEST_CASES)}\n")
    
    # Confirm before running
    if not click.confirm("This will make API calls. Continue?"):
        return
    
    results = []
    total = len(working_models) * len(prompt_versions) * len(TEST_CASES)
    count = 0
    
    # Run evaluation matrix
    for provider, model in working_models:
        click.echo(click.style(f"\n📊 Testing {model}...", fg='cyan', bold=True))
        
        for prompt_name in prompt_versions:
            click.echo(f"  Prompt: {prompt_name}")
            
            for test_case in TEST_CASES:
                count += 1
                click.echo(f"    [{count}/{total}] {test_case.description}...", nl=False)
                
                # Build prompt
                prompt_func = PROMPT_VERSIONS[prompt_name]
                prompt = prompt_func(LARK_GRAMMAR).replace('{input}', test_case.input)
                
                # Call LLM
                if provider == 'anthropic':
                    response, latency, error = call_anthropic(model, prompt)
                else:  # gemini
                    response, latency, error = call_gemini(model, prompt)
                
                # Check success
                success = False
                if not error:
                    # Simple string comparison (can be improved)
                    success = response.strip().lower() == test_case.expected.strip().lower()
                
                # Record result
                result = EvaluationResult(
                    test_case=test_case.description,
                    category=test_case.category,
                    model=model,
                    prompt_version=prompt_name,
                    input_text=test_case.input,
                    expected_output=test_case.expected,
                    actual_output=response,
                    success=success,
                    latency_ms=latency,
                    error=error,
                    timestamp=datetime.now().isoformat()
                )
                results.append(result)
                
                # Show result
                if error:
                    click.echo(click.style(f" ✗ ERROR", fg='red'))
                elif success:
                    click.echo(click.style(f" ✓ ({latency:.0f}ms)", fg='green'))
                else:
                    click.echo(click.style(f" ✗ Wrong ({latency:.0f}ms)", fg='yellow'))
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
    
    # Save results to CSV
    click.echo(click.style(f"\n💾 Saving results to {output}...", fg='blue'))
    
    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'timestamp', 'model', 'prompt_version', 'category', 'test_case',
            'input_text', 'expected_output', 'actual_output', 'success', 
            'latency_ms', 'error'
        ])
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))
    
    # Quick summary
    total_tests = len(results)
    successful = sum(1 for r in results if r.success)
    success_rate = (successful / total_tests * 100) if total_tests > 0 else 0
    
    click.echo(click.style(f"\n✓ Evaluation complete!", fg='green', bold=True))
    click.echo(f"  Total tests: {total_tests}")
    click.echo(f"  Successful: {successful} ({success_rate:.1f}%)")
    click.echo(f"  Results saved to: {output}\n")


@cli.command()
@click.argument('results_file')
def analyze(results_file):
    """Analyze evaluation results."""
    click.echo(click.style(f"\n=== Phase 3: Analysis ===\n", fg='blue', bold=True))
    
    try:
        import pandas as pd
    except ImportError:
        click.echo(click.style("Error: pandas not installed. Run: pip install pandas", fg='red'))
        return
    
    # Load results
    try:
        df = pd.read_csv(results_file)
    except FileNotFoundError:
        click.echo(click.style(f"Error: {results_file} not found", fg='red'))
        return
    
    click.echo(f"Loaded {len(df)} test results\n")
    
    # Overall statistics
    click.echo(click.style("=== Overall Results ===", fg='cyan', bold=True))
    total_tests = len(df)
    successful = df['success'].sum()
    success_rate = (successful / total_tests * 100) if total_tests > 0 else 0
    click.echo(f"Total tests: {total_tests}")
    click.echo(f"Successful: {successful} ({success_rate:.1f}%)")
    click.echo(f"Failed: {total_tests - successful} ({100-success_rate:.1f}%)\n")
    
    # Results by model
    click.echo(click.style("=== Results by Model ===", fg='cyan', bold=True))
    model_stats = df.groupby('model').agg({
        'success': ['sum', 'count', 'mean'],
        'latency_ms': 'mean'
    }).round(2)
    model_stats.columns = ['Successful', 'Total', 'Success Rate', 'Avg Latency (ms)']
    model_stats['Success Rate'] = (model_stats['Success Rate'] * 100).round(1)
    click.echo(model_stats.to_string())
    click.echo()
    
    # Results by prompt version
    click.echo(click.style("=== Results by Prompt ===", fg='cyan', bold=True))
    prompt_stats = df.groupby('prompt_version').agg({
        'success': ['sum', 'count', 'mean'],
        'latency_ms': 'mean'
    }).round(2)
    prompt_stats.columns = ['Successful', 'Total', 'Success Rate', 'Avg Latency (ms)']
    prompt_stats['Success Rate'] = (prompt_stats['Success Rate'] * 100).round(1)
    click.echo(prompt_stats.to_string())
    click.echo()
    
    # Results by category
    click.echo(click.style("=== Results by Category ===", fg='cyan', bold=True))
    category_stats = df.groupby('category').agg({
        'success': ['sum', 'count', 'mean']
    }).round(2)
    category_stats.columns = ['Successful', 'Total', 'Success Rate']
    category_stats['Success Rate'] = (category_stats['Success Rate'] * 100).round(1)
    click.echo(category_stats.to_string())
    click.echo()
    
    # Best model/prompt combinations
    click.echo(click.style("=== Best Combinations ===", fg='cyan', bold=True))
    combo_stats = df.groupby(['model', 'prompt_version']).agg({
        'success': 'mean',
        'latency_ms': 'mean'
    }).round(2)
    combo_stats.columns = ['Success Rate', 'Avg Latency (ms)']
    combo_stats['Success Rate'] = (combo_stats['Success Rate'] * 100).round(1)
    combo_stats = combo_stats.sort_values('Success Rate', ascending=False)
    click.echo(combo_stats.head(10).to_string())
    click.echo()
    
    # Recommendations
    click.echo(click.style("=== Recommendations ===", fg='green', bold=True))
    
    best_accuracy = combo_stats['Success Rate'].max()
    best_combo = combo_stats[combo_stats['Success Rate'] == best_accuracy].index[0]
    click.echo(f"🏆 Best Accuracy: {best_combo[0]} + {best_combo[1]} ({best_accuracy:.1f}%)")
    
    # Fastest with >80% accuracy
    good_combos = combo_stats[combo_stats['Success Rate'] >= 80]
    if not good_combos.empty:
        fastest = good_combos['Avg Latency (ms)'].min()
        fastest_combo = good_combos[good_combos['Avg Latency (ms)'] == fastest].index[0]
        fastest_rate = good_combos.loc[fastest_combo, 'Success Rate']
        click.echo(f"⚡ Fastest (>80% accuracy): {fastest_combo[0]} + {fastest_combo[1]} ({fastest:.0f}ms, {fastest_rate:.1f}%)")
    
    click.echo()
    
    # Show some failures for debugging
    failures = df[df['success'] == False].head(5)
    if not failures.empty:
        click.echo(click.style("=== Sample Failures (first 5) ===", fg='yellow', bold=True))
        for idx, row in failures.iterrows():
            click.echo(f"\nTest: {row['test_case']}")
            click.echo(f"  Input: {row['input_text']}")
            click.echo(f"  Expected: {row['expected_output']}")
            click.echo(f"  Got: {row['actual_output']}")
            click.echo(f"  Model: {row['model']}, Prompt: {row['prompt_version']}")
    
    click.echo()


if __name__ == '__main__':
    cli()