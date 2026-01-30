#!/usr/bin/env python3
"""
Re-validate evaluation results using actual grammar parser.

Takes existing evaluation_results.csv and checks if each "actual_output"
parses with the real constraint grammar.
"""

import sys
import pandas as pd
from pathlib import Path

# Import your actual parser
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from rehearsal_scheduler.grammar import constraint_parser


def can_parse(text: str) -> bool:
    """Check if text parses with the constraint grammar."""
    if not text or text.strip() == "":
        return False
    
    try:
        parser = constraint_parser()
        parser.parse(text.strip())
        return True
    except Exception:
        return False


def main():
    # Load results
    df = pd.read_csv('evaluation_results.csv')
    
    print(f"Re-validating {len(df)} results with actual grammar parser...\n")
    
    # Add new column for grammar-based validation
    df['parses_correctly'] = df['actual_output'].apply(can_parse)
    
    # Compare old vs new success metrics
    old_success = df['success'].sum()
    new_success = df['parses_correctly'].sum()
    
    old_rate = (old_success / len(df)) * 100
    new_rate = (new_success / len(df)) * 100
    
    print(f"Original validation (string comparison):")
    print(f"  Successful: {old_success} ({old_rate:.1f}%)")
    print()
    print(f"Grammar-based validation (actual parser):")
    print(f"  Successful: {new_success} ({new_rate:.1f}%)")
    print(f"  Difference: {new_success - old_success:+d} ({new_rate - old_rate:+.1f}%)")
    print()
    
    # Save updated results
    df.to_csv('evaluation_results_validated.csv', index=False)
    print("✓ Saved updated results to evaluation_results_validated.csv")
    print()
    
    # Show examples of what changed
    changed = df[df['success'] != df['parses_correctly']]
    
    if not changed.empty:
        print(f"\n{len(changed)} results changed validation status:\n")
        
        # False positives (failed string match but parses correctly)
        false_negatives = changed[changed['parses_correctly'] == True]
        if not false_negatives.empty:
            print(f"✓ {len(false_negatives)} now PASS (were marked as failures):")
            for idx, row in false_negatives.head(5).iterrows():
                print(f"  • Input: {row['input_text']}")
                print(f"    Expected: {row['expected_output']}")
                print(f"    Got: {row['actual_output']}")
                print()
        
        # False positives (passed string match but doesn't parse)
        false_positives = changed[changed['parses_correctly'] == False]
        if not false_positives.empty:
            print(f"✗ {len(false_positives)} now FAIL (were marked as successes):")
            for idx, row in false_positives.head(5).iterrows():
                print(f"  • Input: {row['input_text']}")
                print(f"    Expected: {row['expected_output']}")
                print(f"    Got: {row['actual_output']}")
                print()
    
    # Re-run analysis with corrected data
    print("\n=== Updated Analysis ===\n")
    
    print("By Model:")
    model_stats = df.groupby('model')['parses_correctly'].agg(['sum', 'count', 'mean'])
    model_stats.columns = ['Successful', 'Total', 'Rate']
    model_stats['Rate'] = (model_stats['Rate'] * 100).round(1)
    print(model_stats.to_string())
    print()
    
    print("By Prompt:")
    prompt_stats = df.groupby('prompt_version')['parses_correctly'].agg(['sum', 'count', 'mean'])
    prompt_stats.columns = ['Successful', 'Total', 'Rate']
    prompt_stats['Rate'] = (prompt_stats['Rate'] * 100).round(1)
    print(prompt_stats.to_string())
    print()
    
    print("Best Combinations:")
    combo_stats = df.groupby(['model', 'prompt_version'])['parses_correctly'].mean() * 100
    combo_stats = combo_stats.sort_values(ascending=False)
    print(combo_stats.head(10).to_string())
    print()


if __name__ == '__main__':
    main()