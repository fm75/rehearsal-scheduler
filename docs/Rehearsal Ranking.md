Excellent analysis! Let's think through the ranking heuristic systematically.

## Two Fundamental Measures

**Measure 1: Group Time Availability** (scheduling feasibility)
- How much rehearsal time can this group use across ALL slots?
- Formula: `sum(100% available minutes per slot) / sum(total slot minutes)`
- Range: 0 (impossible to schedule) → 1.0 (can use any time)

**Measure 2: Dancer Participation** (resource utilization)
- What % of possible dancer-minutes are actually available?
- Formula: `sum(individual dancer available minutes) / (num_dancers × sum(slot minutes))`
- Range: 0 (no one available) → 1.0 (everyone always available)

## Why Two Measures Matter

**Example where they differ:**

**Dance Group A:**
- 5 dancers, all available 2-4pm Monday (2 hrs = 100% overlap)
- Measure 1: 2/10 = 0.2 (low - only one window)
- Measure 2: (5 × 2) / (5 × 10) = 0.2 (matches)

**Dance Group B:**
- 5 dancers, each available different 2-hour windows (no overlap)
- Measure 1: 0/10 = 0.0 (can't schedule - no 100% time!)
- Measure 2: (5 × 2) / (5 × 10) = 0.2 (same availability, but dispersed)

**Dance Group B is your "zero with potential" case** - can't schedule now, but maybe with substitutions or RD flexibility.

## Proposed Ranking Strategy

**Priority Score = Measure 1 × 10** (primary: feasibility)
- 0-10 scale where 10 = unconstrained

**Secondary Sort = Measure 2** (tiebreaker: utilization)
- When two groups have similar feasibility, favor higher participation

**Buckets:**
- **0.0-0.5**: Critical (hard to schedule)
- **0.5-2.0**: Constrained (schedule early)
- **2.0-8.0**: Moderate (flexible)
- **8.0-10.0**: Unconstrained (schedule last)

## Output Format

```markdown
**d_01 Opening Number** [Priority: 1.2, Participation: 0.15]
**d_05 Jazz Piece** [Priority: 0.0, Participation: 0.30] ← No overlap but dancers available
**d_12 Finale** [Priority: 9.8, Participation: 1.0] ← Easy, save for last
```

**Thoughts:**
1. Keep measures separate or combine into single score?
2. Should we weight Measure 2 more for "zeros with potential"?
3. Include duration requirements in ranking (long dances need more time)?

What direction feels right? 🎯