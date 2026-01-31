#!/usr/bin/env python3
"""
Analyze scheduling conflicts from Google Sheets or CSV data.

Uses pandas DataFrames as common data structure, regardless of source.

Usage:
    # From Google Sheets
    python analyze_conflicts.py --config config/workbook_config.yaml
    
    # From CSV files
    python analyze_conflicts.py --csv-dir data/csv_export
"""

import sys
from pathlib import Path
import click
import pandas as pd

# Add src to path
# sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Import data loader
from rehearsal_scheduler.persistence.data_loader import SchedulingDataLoader, load_from_csv


@click.command()
@click.option('--config', type=click.Path(exists=True),
              help='YAML config for Google Sheets (use this OR --csv-dir)')
@click.option('--csv-dir', type=click.Path(exists=True),
              help='Directory with CSV files (use this OR --config)')
@click.option('--output', default='conflict_report.md',
              help='Output file for report')
def main(config, csv_dir, output):
    """
    Analyze scheduling conflicts.
    
    Loads data from either Google Sheets (via config) or CSV files,
    then runs conflict analysis and generates report.
    """
    click.echo(click.style("\n=== Conflict Analysis ===\n", fg='blue', bold=True))
    
    # Load data from appropriate source
    if config and csv_dir:
        click.echo(click.style("Error: Use --config OR --csv-dir, not both", fg='red'))
        sys.exit(1)
    
    if not config and not csv_dir:
        click.echo(click.style("Error: Must provide --config or --csv-dir", fg='red'))
        sys.exit(1)
    
    # Load data into DataFrames
    click.echo("📊 Loading data...")
    
    if config:
        click.echo(f"  Source: Google Sheets (config: {config})")
        loader = SchedulingDataLoader(config)
        data = loader.load_all()
    else:
        click.echo(f"  Source: CSV files (directory: {csv_dir})")
        data = load_from_csv(csv_dir)
    
    # Show what was loaded
    click.echo("\n📈 Data summary:")
    for name, df in data.items():
        if not df.empty:
            click.echo(f"  ✓ {name}: {len(df)} rows")
        else:
            click.echo(click.style(f"  ⚠ {name}: empty", fg='yellow'))
    
    # Now data is in consistent DataFrame format, ready for analysis
    click.echo(click.style("\n🔍 Analyzing conflicts...\n", fg='cyan', bold=True))
    
    # TODO: Call your existing conflict analysis logic here
    # It should now work the same whether data came from Sheets or CSV!
    
    rehearsals_df = data['rehearsals']
    rd_constraints_df = data['rd_constraints']
    dancer_constraints_df = data['dancer_constraints']
    
    click.echo(f"  Rehearsal slots: {len(rehearsals_df)}")
    click.echo(f"  RD constraints: {len(rd_constraints_df)}")
    click.echo(f"  Dancer constraints: {len(dancer_constraints_df)}")
    
    # Placeholder for actual analysis
    click.echo(click.style("\n✓ Analysis complete (TODO: implement actual conflict checking)\n", fg='green'))
    
    click.echo(f"Next: Implement conflict checking logic using the DataFrames above")


if __name__ == '__main__':
    main()