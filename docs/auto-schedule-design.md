## Can We Automatically Schedule? Discussion

**Short answer:** Yes, but with important caveats.

---

## What We Have Now

**Data:**
- Priority/participation scores (ranking)
- 100% availability windows per dance group per slot
- Dance durations (from dances table)
- Slot capacities (start/end times)

**The Scheduling Problem:**
- **Bin packing** with time windows
- **Constraint satisfaction** (everyone must be available)
- **Optimization** (what's "best"?)

---

## Feasibility Analysis

### ✅ **Easy Part: Greedy Assignment**
```
For each slot (in order):
  For each unscheduled dance (priority ascending):
    If dance fits in remaining slot time AND has availability:
      Schedule it
```

**Works when:**
- Total dance time < total rehearsal time
- Conflicts are sparse
- You don't care about optimality

**Fails when:**
- Need to leave gaps for later dances (tetris problem)
- Multiple valid solutions with different quality
- Need to balance across venues/days

### 🤔 **Medium Part: Constraint Satisfaction**

**Additional constraints to consider:**
- Dance duration requirements
- Maximum dancers per venue (space limits?)
- RD workload balancing (don't exhaust one RD)
- "Same day" preferences (group related dances)
- Warm-up time between dances
- Costume/prop change time

**Solvable with:**
- Integer Linear Programming (ILP)
- Constraint Programming (CP-SAT solver)
- Backtracking search

### ❌ **Hard Part: Defining "Best"**

**What makes a schedule good?**
1. **Maximize rehearsal time used** (efficiency)
2. **Minimize gaps** (continuous blocks preferred)
3. **Balance RD workload** (fair distribution)
4. **Group similar dances** (logical flow)
5. **Prioritize constrained dances** (schedule hard ones first)
6. **Maximize flexibility for changes** (leave slack)

**These often conflict!**

---

## Proposed Approach: Hybrid

### **Phase 1: Automatic First Pass (Conservative)**
- Greedy scheduler using priority ranking
- Only schedules when 100% confident (full availability)
- Leaves uncertain cases for manual review
- Output: Partial schedule + unscheduled list

### **Phase 2: Manual Refinement (Amy)**
- Review automatic assignments
- Handle edge cases (substitutions, RD swaps)
- Make judgment calls on trade-offs
- Adjust for artistic/practical considerations

### **Phase 3: Validation**
- Check all constraints still satisfied
- Flag any conflicts introduced
- Generate final schedule

---

## What Would You Need?

**To build an automatic scheduler:**

1. **Objective function** - How do you measure "good"?
   - Simple: "Maximize scheduled dances"
   - Better: Weighted score across multiple criteria

2. **Conflict tolerance** - What's acceptable?
   - Strict: 100% availability required
   - Flexible: 90% okay if Amy approves substitution

3. **Manual override capability** - Amy's preferences
   - Pin certain dances to certain slots
   - Block out time for breaks/setup
   - Force/forbid combinations

4. **Iteration support** - Schedules change!
   - Re-run after constraints update
   - Preserve manual assignments
   - Show what changed

---

## My Recommendation

**Start simple:**
1. ✅ **Keep current CSV output** (gives Amy visibility)
2. ✅ **Add "suggested schedule" column** using greedy algorithm
3. ✅ **Flag confidence level** (high/medium/low)
4. ⏭️ **Let Amy validate/adjust** in spreadsheet
5. ⏭️ **Later: Add optimization** if greedy isn't good enough

**Why incremental:**
- Trust builds gradually (Amy needs to see it work)
- Edge cases will emerge (better to find them early)
- Requirements will evolve (Amy will discover what she cares about)

**Think:** Autocomplete, not autopilot.

---

## Specific Question for You

**What's more valuable right now:**
- A) Automatic scheduler that handles 80% of cases
- B) Better visualization/tools for Amy to schedule manually
- C) Validation checker ("tell me if my schedule has conflicts")

My gut says **C then B then A**, but you know the workflow better! 🤔