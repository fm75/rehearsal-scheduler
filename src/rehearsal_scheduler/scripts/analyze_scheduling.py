#!/usr/bin/env python3
"""
Scheduling Catalog CLI

Generates a catalog showing RD and dancer availability for rehearsal scheduling.
Uses dance_groups (with RD assignments) and group_cast (dancer assignments).

This is the scheduling-focused version that works with the Scheduling workbook.

Usage:
    # From Google Sheets
    python -m rehearsal_scheduler.scripts.analyze_scheduling --config config/workbook_config.yaml
    
    # From CSV files
    python -m rehearsal_scheduler.scripts.analyze_scheduling --csv-dir data/csv_export
    
    # Specify output file and format
    python -m rehearsal_scheduler.scripts.analyze_scheduling \\
        --config config.yaml \\
        --output scheduling_catalog.md \\
        --format markdown
"""

import sys
from pathlib import Path
import click

from rehearsal_scheduler.persistence.data_loader import SchedulingDataLoader, load_from_csv
from rehearsal_scheduler.domain.scheduling_catalog import generate_scheduling_catalog
from rehearsal_scheduler.reporting.scheduling_formatter import (
    format_scheduling_catalog_markdown,
    format_scheduling_catalog_text,
    format_scheduling_catalog_summary
)


@click.command()
@click.option('--config', type=click.Path(exists=True),
              help='YAML config for Google Sheets (use this OR --csv-dir)')
@click.option('--csv-dir', type=click.Path(exists=True),
              help='Directory with CSV files (use this OR --config)')
@click.option('--output', default='scheduling_catalog.md',
              help='Output file for report')
@click.option('--format', 'output_format',
              type=click.Choice(['markdown', 'text', 'summary']), 
              default='markdown',
              help='Report format')
@click.option('--verbose', is_flag=True,
              help='Show detailed progress')
def cli(config, csv_dir, output, output_format, verbose):
    """
    Generate rehearsal scheduling catalog.
    
    Shows RD conflicts, ineligible dance groups (RD unavailable), and dancer
    conflicts by dance group. Uses data from the Scheduling workbook.
    """
    click.echo(click.style("\n=== Rehearsal Scheduling Catalog ===\n", fg='blue', bold=True))
    
    # Validate inputs
    if config and csv_dir:
        click.echo(click.style("Error: Use --config OR --csv-dir, not both", fg='red'))
        sys.exit(1)
    
    if not config and not csv_dir:
        click.echo(click.style("Error: Must provide --config or --csv-dir", fg='red'))
        sys.exit(1)
    
    # Load data into DataFrames
    click.echo("📊 Loading scheduling data...")
    
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
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Verify we have scheduling data
    required = ['rehearsals', 'rd_constraints', 'dancer_constraints', 'dance_groups', 'group_cast']
    missing = [name for name in required if name not in data or data[name].empty]
    
    if missing:
        click.echo(click.style(f"Error: Missing required data: {', '.join(missing)}", fg='red'))
        click.echo("\nThis tool requires scheduling workbook data:")
        click.echo("  - rehearsals (schedule)")
        click.echo("  - rd_constraints (RD availability)")
        click.echo("  - dancer_constraints (dancer availability)")
        click.echo("  - dance_groups (groups with RD assignments)")
        click.echo("  - group_cast (dancer assignments to groups)")
        sys.exit(1)
    
    # Show what was loaded
    if verbose:
        click.echo("\n📈 Data loaded:")
        for name in required:
            df = data[name]
            click.echo(f"  ✓ {name}: {len(df)} rows")
    else:
        click.echo(click.style("  ✓ Data loaded successfully", fg='green'))
    
    # Generate scheduling catalog
    click.echo(click.style("\n🔍 Analyzing scheduling conflicts...", fg='cyan'))
    
    try:
        catalog = generate_scheduling_catalog(data)
    except Exception as e:
        click.echo(click.style(f"Error analyzing conflicts: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Count conflicts
    total_rd_conflicts = sum(len(entry.rd_conflicts) for entry in catalog)
    total_ineligible = sum(len(entry.ineligible_groups) for entry in catalog)
    total_dancer_conflicts = sum(
        sum(len(conflicts) for conflicts in entry.group_conflicts.values())
        for entry in catalog
    )
    
    click.echo(f"  Analyzed {len(catalog)} rehearsal slots")
    click.echo(f"  Found {total_rd_conflicts} RD conflicts")
    click.echo(f"  Found {total_ineligible} ineligible dance groups")
    click.echo(f"  Found {total_dancer_conflicts} dancer conflicts")
    
    # Format report
    click.echo(f"\n📝 Generating {output_format} report...")
    
    try:
        if output_format == 'markdown':
            report = format_scheduling_catalog_markdown(catalog, data.get('dance_groups'))
        elif output_format == 'text':
            report = format_scheduling_catalog_text(catalog, data.get('dance_groups'))
        else:  # summary
            report = format_scheduling_catalog_summary(catalog)
    except Exception as e:
        click.echo(click.style(f"Error formatting report: {e}", fg='red'))
        if verbose:
            import traceback
            traceback.print_exc()
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