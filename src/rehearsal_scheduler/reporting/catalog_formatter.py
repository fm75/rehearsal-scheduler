"""
Conflict Catalog Formatters

Formats conflict catalog data into human-readable reports (markdown, text, etc.)
"""

from datetime import datetime
from typing import List
import pandas as pd


def format_catalog_markdown(catalog: List, dances_df: pd.DataFrame = None) -> str:
    """
    Format catalog as Markdown report.
    
    Args:
        catalog: List of SlotCatalogEntry objects
        dances_df: Optional DataFrame with dance info (dance_id, dance_name columns)
        
    Returns:
        Formatted markdown string
    """
    # Build dance_id -> dance_name lookup
    dance_names = {}
    if dances_df is not None and not dances_df.empty:
        for _, row in dances_df.iterrows():
            dance_names[row['dance_id']] = row['name']

    lines = ["# Rehearsal Conflict Catalog\n"]
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    lines.append("---\n")
    
    for entry in catalog:
        slot = entry.slot
        venue = entry.venue_name
        
        # Slot header
        lines.append(f"## {slot.day_of_week.title()} {slot.rehearsal_date.strftime('%m/%d/%y')}")
        lines.append(f"**Time:** {slot.start_time // 100}:{slot.start_time % 100:02d} - {slot.end_time // 100}:{slot.end_time % 100:02d}")
        lines.append(f"**Venue:** {venue}\n")
        
        # RD conflicts
        rd_conflicts = entry.rd_conflicts
        if rd_conflicts:
            lines.append("### ❌ RD Conflicts\n")
            for conflict in rd_conflicts:
                lines.append(f"- **{conflict.full_name}** ({conflict.entity_id}): {conflict.reason}")
        else:
            lines.append("### ✅ All RDs Available\n")
        
        # Dance conflicts
        dance_conflicts = entry.dance_conflicts
        if dance_conflicts:
            lines.append("\n### 💃 Dancer Conflicts by Dance\n")
            
            for dance_id, conflicts in sorted(dance_conflicts.items()):
                # Get dance name if available
                dance_display = dance_names.get(dance_id, dance_id)
                if dance_display != dance_id:
                    lines.append(f"\n**{dance_display}** ({dance_id})")
                else:
                    lines.append(f"\n**{dance_id}**")
                
                for conflict in conflicts:
                    lines.append(f"  - {conflict.full_name} ({conflict.entity_id}): {conflict.reason}")
        else:
            lines.append("\n### ✅ No Dancer Conflicts\n")
        
        lines.append("\n---\n")
    
    return "\n".join(lines)


def format_catalog_text(catalog: List, dances_df: pd.DataFrame = None) -> str:
    """
    Format catalog as plain text report.
    
    Args:
        catalog: List of SlotCatalogEntry objects
        dances_df: Optional DataFrame with dance info
        
    Returns:
        Formatted text string
    """
    # Build dance_id -> dance_name lookup
    dance_names = {}
    if dances_df is not None and not dances_df.empty:
        for _, row in dances_df.iterrows():
            dance_names[row['dance_id']] = row['name']
    lines = ["REHEARSAL CONFLICT CATALOG"]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 80)
    lines.append("")
    
    for entry in catalog:
        slot = entry.slot
        venue = entry.venue_name
        
        # Slot header
        lines.append(f"{slot.day_of_week.upper()} {slot.rehearsal_date.strftime('%m/%d/%y')}")
        lines.append(f"Time: {slot.start_time // 100}:{slot.start_time % 100:02d} - {slot.end_time // 100}:{slot.end_time % 100:02d}")
        lines.append(f"Venue: {venue}")
        lines.append("-" * 80)
        
        # RD conflicts
        rd_conflicts = entry.rd_conflicts
        lines.append("\nRD CONFLICTS:")
        if rd_conflicts:
            for conflict in rd_conflicts:
                lines.append(f"  X {conflict.full_name} ({conflict.entity_id}): {conflict.reason}")
        else:
            lines.append("  (All RDs available)")
        
        # Dance conflicts
        dance_conflicts = entry.dance_conflicts
        lines.append("\nDANCER CONFLICTS BY DANCE:")
        if dance_conflicts:
            for dance_id, conflicts in sorted(dance_conflicts.items()):
                dance_display = dance_names.get(dance_id, dance_id)
                if dance_display != dance_id:
                    lines.append(f"\n  {dance_display} ({dance_id}):")
                else:
                    lines.append(f"\n  {dance_id}:")
                
                for conflict in conflicts:
                    lines.append(f"    - {conflict.full_name} ({conflict.entity_id}): {conflict.reason}")
        else:
            lines.append("  (No conflicts)")
        
        lines.append("\n" + "=" * 80)
        lines.append("")
    
    return "\n".join(lines)


def format_catalog_summary(catalog: List) -> str:
    """
    Format catalog as a brief summary.
    
    Args:
        catalog: List of SlotCatalogEntry objects
        
    Returns:
        Brief summary text
    """
    lines = [f"Conflict Catalog Summary ({len(catalog)} slots)"]
    lines.append("-" * 50)
    
    for entry in catalog:
        slot = entry.slot
        rd_count = len(entry.rd_conflicts)
        dancer_count = sum(len(conflicts) for conflicts in entry.dance_conflicts.values())
        dance_count = len(entry.dance_conflicts)
        
        status = "✓" if (rd_count == 0 and dancer_count == 0) else "✗"
        
        lines.append(
            f"{status} {slot.day_of_week.title()} {slot.rehearsal_date.strftime('%m/%d/%y')}: "
            f"{rd_count} RD conflicts, {dancer_count} dancer conflicts ({dance_count} dances affected)"
        )
    
    return "\n".join(lines)