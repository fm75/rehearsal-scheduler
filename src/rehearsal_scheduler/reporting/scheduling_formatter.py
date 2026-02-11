"""
Scheduling Catalog Formatters

Formats scheduling catalog data into human-readable reports.
Shows RD conflicts, ineligible dance groups, and dancer conflicts by group.
"""

from datetime import datetime, time
from typing import List
import pandas as pd


def format_scheduling_catalog_markdown(
    catalog: List, 
    dance_groups_df: pd.DataFrame = None,
    show_availability: bool = False
) -> str:
    """
    Format scheduling catalog as Markdown report.
    
    Args:
        catalog: List of SchedulingSlotEntry objects
        dance_groups_df: Optional DataFrame with dance group info
        show_availability: If True, show availability windows instead of conflicts
        
    Returns:
        Formatted markdown string
    """
    # Build dg_id -> dg_name lookup
    group_names = {}
    if dance_groups_df is not None and not dance_groups_df.empty:
        for _, row in dance_groups_df.iterrows():
            group_names[row['dg_id']] = row['dg_name']
    
    lines = ["# Rehearsal Scheduling Catalog\n"]
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    if show_availability:
        lines.append("**Mode:** Showing dancer availability windows\n")
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
        
        # Ineligible dance groups (RD unavailable)
        ineligible_groups = entry.ineligible_groups
        if ineligible_groups:
            lines.append("\n### 🚫 Dance Groups Unavailable (RD conflicts)\n")
            for group in ineligible_groups:
                group_display = group_names.get(group.dg_id, group.dg_name)
                lines.append(f"- **{group_display}** ({group.dg_id}) - directed by {group.rd_name}")
        
        # Dancer conflicts or availability by group (only eligible groups shown)
        group_conflicts = entry.group_conflicts
        if group_conflicts:
            if show_availability:
                lines.append("\n### 💃 Dancer Availability by Dance Group\n")
                lines.append("_(Only showing dancers with constraints)_\n")
            else:
                lines.append("\n### 💃 Dancer Conflicts by Dance Group\n")
            
            for dg_id, data in sorted(group_conflicts.items()):
                # Unpack data - could be tuple (with 100% availability) or just list
                if show_availability and isinstance(data, tuple):
                    conflicts, full_availability = data
                else:
                    conflicts = data
                    full_availability = None
                
                group_display = group_names.get(dg_id, dg_id)
                
                # Format group header with 100% availability if in availability mode
                if show_availability and full_availability is not None:
                    if group_display != dg_id:
                        lines.append(f"\n**{group_display}** ({dg_id}) — 100% Available: {full_availability}")
                    else:
                        lines.append(f"\n**{dg_id}** — 100% Available: {full_availability}")
                else:
                    if group_display != dg_id:
                        lines.append(f"\n**{group_display}** ({dg_id})")
                    else:
                        lines.append(f"\n**{dg_id}**")
                
                # Show individual dancer availability/conflicts
                for conflict in conflicts:
                    lines.append(f"  - {conflict.full_name} ({conflict.entity_id}): {conflict.reason}")
        else:
            # Only show if there are eligible groups (some might be ineligible)
            if not ineligible_groups:
                if show_availability:
                    lines.append("\n### ✅ All Dancers Fully Available\n")
                else:
                    lines.append("\n### ✅ No Dancer Conflicts\n")
        
        lines.append("\n---\n")
    
    return "\n".join(lines)


def format_scheduling_catalog_text(
    catalog: List, 
    dance_groups_df: pd.DataFrame = None,
    show_availability: bool = False
) -> str:
    """
    Format scheduling catalog as plain text report.
    
    Args:
        catalog: List of SchedulingSlotEntry objects
        dance_groups_df: Optional DataFrame with dance group info
        show_availability: If True, show availability windows instead of conflicts
        
    Returns:
        Formatted text string
    """
    # Build dg_id -> dg_name lookup
    group_names = {}
    if dance_groups_df is not None and not dance_groups_df.empty:
        for _, row in dance_groups_df.iterrows():
            group_names[row['dg_id']] = row['dg_name']
    
    lines = ["REHEARSAL SCHEDULING CATALOG"]
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if show_availability:
        lines.append("Mode: Showing dancer availability windows")
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
        
        # Ineligible groups
        ineligible_groups = entry.ineligible_groups
        if ineligible_groups:
            lines.append("\nDANCE GROUPS UNAVAILABLE (RD conflicts):")
            for group in ineligible_groups:
                group_display = group_names.get(group.dg_id, group.dg_name)
                lines.append(f"  - {group_display} ({group.dg_id}) - directed by {group.rd_name}")
        
        # Dancer conflicts or availability by group
        group_conflicts = entry.group_conflicts
        if show_availability:
            lines.append("\nDANCER AVAILABILITY BY DANCE GROUP:")
            lines.append("(Only showing dancers with constraints)")
        else:
            lines.append("\nDANCER CONFLICTS BY DANCE GROUP:")
        
        if group_conflicts:
            for dg_id, data in sorted(group_conflicts.items()):
                # Unpack data - could be tuple (with 100% availability) or just list
                if show_availability and isinstance(data, tuple):
                    conflicts, full_availability = data
                else:
                    conflicts = data
                    full_availability = None
                
                group_display = group_names.get(dg_id, dg_id)
                
                # Format group header
                if show_availability and full_availability is not None:
                    if group_display != dg_id:
                        lines.append(f"\n  {group_display} ({dg_id}) — 100% Available: {full_availability}")
                    else:
                        lines.append(f"\n  {dg_id} — 100% Available: {full_availability}")
                else:
                    if group_display != dg_id:
                        lines.append(f"\n  {group_display} ({dg_id}):")
                    else:
                        lines.append(f"\n  {dg_id}:")
                
                for conflict in conflicts:
                    lines.append(f"    - {conflict.full_name} ({conflict.entity_id}): {conflict.reason}")
        else:
            if not ineligible_groups:
                if show_availability:
                    lines.append("  (All dancers fully available)")
                else:
                    lines.append("  (No conflicts)")
        
        lines.append("\n" + "=" * 80)
        lines.append("")
    
    return "\n".join(lines)


def format_scheduling_catalog_summary(catalog: List) -> str:
    """
    Format scheduling catalog as a brief summary.
    
    Args:
        catalog: List of SchedulingSlotEntry objects
        
    Returns:
        Brief summary text
    """
    lines = [f"Scheduling Catalog Summary ({len(catalog)} slots)"]
    lines.append("-" * 60)
    
    for entry in catalog:
        slot = entry.slot
        rd_count = len(entry.rd_conflicts)
        ineligible_count = len(entry.ineligible_groups)
        dancer_count = sum(len(conflicts) for conflicts in entry.group_conflicts.values())
        group_count = len(entry.group_conflicts)
        
        status = "✓" if (rd_count == 0 and dancer_count == 0) else "✗"
        
        lines.append(
            f"{status} {slot.day_of_week.title()} {slot.rehearsal_date.strftime('%m/%d/%y')}: "
            f"{rd_count} RD conflicts, {ineligible_count} groups unavailable, "
            f"{dancer_count} dancer conflicts ({group_count} groups affected)"
        )
    
    return "\n".join(lines)