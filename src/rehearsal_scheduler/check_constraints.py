# src/rehearsal_scheduler/check_constraints.py

import csv
import sys
from pathlib import Path
import click

from rehearsal_scheduler.grammar import validate_token


@click.group()
def cli():
    """Rehearsal Scheduler CLI tools."""
    pass


@cli.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--column', '-c', default='conflicts', 
              help='Name of the column containing constraints')
@click.option('--id-column', '-i', default='dancer_id',
              help='Name of the column containing dancer IDs')
@click.option('--verbose', '-v', is_flag=True,
              help='Show all tokens including valid ones')
@click.option('--output', '-o', type=click.Path(),
              help='Write error report to CSV file')
def validate(csv_file, column, id_column, verbose, output):
    """Validate constraint tokens in a CSV file.
    
    Splits each constraint field on commas and validates each token separately.
    Reports errors by dancer ID and token for director cleanup.
    
    Example:
        rehearsal-scheduler validate conflicts.csv
        rehearsal-scheduler validate conflicts.csv -v
        rehearsal-scheduler validate conflicts.csv -o errors.csv
    """
    csv_path = Path(csv_file)
    
    click.echo(f"Validating constraints in: {csv_path.name}")
    click.echo(f"Constraint column: '{column}', ID column: '{id_column}'")
    click.echo("=" * 70)
    
    total_rows = 0
    total_tokens = 0
    valid_tokens = 0
    invalid_tokens = 0
    empty_rows = 0
    error_records = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check if required columns exist
            if id_column not in reader.fieldnames:
                click.echo(f"❌ Error: Column '{id_column}' not found in CSV", err=True)
                click.echo(f"Available columns: {', '.join(reader.fieldnames)}", err=True)
                sys.exit(1)
                
            if column not in reader.fieldnames:
                click.echo(f"❌ Error: Column '{column}' not found in CSV", err=True)
                click.echo(f"Available columns: {', '.join(reader.fieldnames)}", err=True)
                sys.exit(1)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                total_rows += 1
                dancer_id = row.get(id_column, f"row_{row_num}").strip()
                conflicts_text = row.get(column, '').strip()
                
                # Skip empty constraints
                if not conflicts_text:
                    empty_rows += 1
                    if verbose:
                        click.echo(f"  {dancer_id}: (empty)")
                    continue
                
                # Split on commas to get individual tokens
                tokens = [t.strip() for t in conflicts_text.split(',')]
                
                for token_num, token in enumerate(tokens, start=1):
                    if not token:  # Skip empty tokens from trailing commas
                        continue
                        
                    total_tokens += 1
                    result, error = validate_token(token)
                    
                    if error is None:
                        # Valid token
                        valid_tokens += 1
                        if verbose:
                            click.echo(f"✓ {dancer_id} [token {token_num}]: {token}")
                    else:
                        # Invalid token
                        invalid_tokens += 1
                        click.echo(f"\n❌ {dancer_id} (row {row_num}, token {token_num}):", err=True)
                        click.echo(f"   Token: '{token}'", err=True)
                        click.echo(f"   {error}", err=True)
                        
                        # Store for CSV output
                        error_records.append({
                            'dancer_id': dancer_id,
                            'row': row_num,
                            'token_num': token_num,
                            'token': token,
                            'error': error.replace('\n', ' | '),   # Flatten multiline errors
                        })
                click.echo(f"{30*'='} end of {dancer_id} {30*'='}", err=True) 
    except FileNotFoundError:
        click.echo(f"❌ Error: File not found: {csv_path}", err=True)
        sys.exit(1)
    except csv.Error as e:
        click.echo(f"❌ Error reading CSV: {e}", err=True)
        sys.exit(1)
    
    # Summary
    click.echo("\n" + "=" * 70)
    click.echo("SUMMARY")
    click.echo("-" * 70)
    click.echo(f"Total dancers:        {total_rows}")
    click.echo(f"Empty constraints:    {empty_rows}")
    click.echo(f"Total tokens:         {total_tokens}")
    click.echo(f"Valid tokens:         {valid_tokens} ✓")
    
    if invalid_tokens > 0:
        click.echo(f"Invalid tokens:       {invalid_tokens} ❌", err=True)
    else:
        click.echo(f"Invalid tokens:       {invalid_tokens}")
    
    # Show success rate
    if total_tokens > 0:
        success_rate = (valid_tokens / total_tokens) * 100
        status = "✓" if invalid_tokens == 0 else "⚠"
        click.echo(f"Success rate:         {success_rate:.1f}% {status}")
    
    # Write error report if requested
    if output and error_records:
        output_path = Path(output)
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['dancer_id', 'row', 'token_num', 'token', 'error', 'tag'])
                writer.writeheader()
                writer.writerows(error_records)
            click.echo(f"\nError report written to: {output_path}")
        except Exception as e:
            click.echo(f"❌ Error writing output file: {e}", err=True)
    
    # Exit with error code if there were failures
    if invalid_tokens > 0:
        sys.exit(1)


@cli.command()
@click.argument('token_text')
def check(token_text):
    """Validate a single constraint token.
    
    Example:
        rehearsal-scheduler check "W before 1 PM"
        rehearsal-scheduler check "Jan 20 26"
    """
    result, error = validate_token(token_text)
    
    click.echo(f"Token: {token_text}")
    click.echo("-" * 50)
    
    if error is None:
        click.echo("✓ Valid!")
        click.echo(f"Parsed as: {result}")
    else:
        click.echo("❌ Invalid!")
        click.echo(f"\n{error}")
        sys.exit(1)


if __name__ == '__main__':
    cli()