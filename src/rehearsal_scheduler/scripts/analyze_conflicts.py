#!/usr/bin/env python3
"""
Conflict Catalog CLI

Generates a catalog showing which RDs and dancers are unavailable for each rehearsal slot.
Helps directors manually schedule dances by identifying constraints upfront.

Usage:
    # From Google Sheets
    python -m rehearsal_scheduler.scripts.analyze_conflicts --config config/workbook_config.yaml
    
    # From CSV files
    python -m rehearsal_scheduler.scripts.analyze_conflicts --csv-dir data/csv_export
    
    # Specify output file and format
    python -m rehearsal_scheduler.scripts.analyze_conflicts \\
        --config config.yaml \\
        --output report.md \\
        --format markdown
"""

import sys
from pathlib import Path
import click

from rehearsal_scheduler.persistence.data_loader import SchedulingDataLoader, load_from_csv
from rehearsal_scheduler.domain.conflict_catalog import generate_conflict_catalog
from rehearsal_scheduler.reporting.catalog_formatter import (
    format_catalog_markdown,
    format_catalog_text,
    format_catalog_summary
)


@click.command()
@click.option('--config', type=click.Path(exists=True),
              help='YAML config for Google Sheets (use this OR --csv-dir)')
@click.option('--csv-dir', type=click.Path(exists=True),
              help='Directory with CSV files (use this OR --config)')
@click.option('--output', default='conflict_catalog.md',
              help='Output file for report')
@click.option('--format', 'output_format',
              type=click.Choice(['markdown', 'text', 'summary']), 
              default='markdown',
              help='Report format')
@click.option('--verbose', is_flag=True,
              help='Show detailed progress')
def cli(config, csv_dir, output, output_format, verbose):
    """
    Generate rehearsal conflict catalog.
    
    Shows which RDs and dancers are unavailable for each rehearsal slot,
    helping directors manually decide what to schedule where.
    """
    click.echo(click.style("\n=== Conflict Catalog Generator ===\n", fg='blue', bold=True))
    
    # Validate inputs
    if config and csv_dir:
        click.echo(click.style("Error: Use --config OR --csv-dir, not both", fg='red'))
        sys.exit(1)
    
    if not config and not csv_dir:
        click.echo(click.style("Error: Must provide --config or --csv-dir", fg='red'))
        sys.exit(1)
    
    # Load data into DataFrames
    click.echo("📊 Loading data...")
    
    try:
        if config:
            if verbose:
                click.echo(f"  Source: Google Sheets")
                click.echo(f"  Config: {config}")
            loader = SchedulingDataLoader(config)
            data = loader.load_all()
        else:
            if verbose:
                click.echo(f"  Source: CSV files")
                click.echo(f"  Directory: {csv_dir}")
            data = load_from_csv(csv_dir)
    except Exception as e:
        click.echo(click.style(f"Error loading data: {e}", fg='red'))
        sys.exit(1)
    
    # Show what was loaded
    if verbose:
        click.echo("\n📈 Data loaded:")
        for name, df in data.items():
            if not df.empty:
                click.echo(f"  ✓ {name}: {len(df)} rows")
            else:
                click.echo(click.style(f"  ⚠ {name}: empty", fg='yellow'))
    else:
        click.echo(click.style("  ✓ Data loaded successfully", fg='green'))
    
    # Generate conflict catalog
    click.echo(click.style("\n🔍 Analyzing conflicts...", fg='cyan'))
    
    try:
        catalog = generate_conflict_catalog(data)
    except Exception as e:
        click.echo(click.style(f"Error analyzing conflicts: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Count conflicts
    total_rd_conflicts = sum(len(entry.rd_conflicts) for entry in catalog)
    total_dancer_conflicts = sum(
        sum(len(conflicts) for conflicts in entry.dance_conflicts.values())
        for entry in catalog
    )
    
    click.echo(f"  Analyzed {len(catalog)} rehearsal slots")
    click.echo(f"  Found {total_rd_conflicts} RD conflicts")
    click.echo(f"  Found {total_dancer_conflicts} dancer conflicts")
    
    # Format report
    click.echo(f"\n📝 Generating {output_format} report...")
    
    try:
        if output_format == 'markdown':
            report = format_catalog_markdown(catalog, data.get('dances'))
        elif output_format == 'text':
            report = format_catalog_text(catalog, data.get('dances'))
        else:  # summary
            report = format_catalog_summary(catalog)
    except Exception as e:
        click.echo(click.style(f"Error formatting report: {e}", fg='red'))
        sys.exit(1)
    
    # Save to file
    try:
        with open(output, 'w') as f:
            f.write(report)
    except Exception as e:
        click.echo(click.style(f"Error saving report: {e}", fg='red'))
        sys.exit(1)
    
    click.echo(click.style(f"\n✅ Report saved to {output}\n", fg='green', bold=True))
    
    # Show preview
    if output_format != 'summary':
        click.echo("Preview (first 20 lines):")
        click.echo("-" * 80)
        for line in report.split('\n')[:20]:
            click.echo(line)
        click.echo("-" * 80)
        click.echo(f"\n(See full report in {output})")
    else:
        # For summary, show the whole thing
        click.echo(report)


if __name__ == '__main__':
    cli()