# Rehearsal Scheduling Assistant

The goal is to assist in optimizing the rehearsals of dances for a production.

## The players
- Director
  - Arranges for venues and times for rehearsal
  - Gets requests from rehearsal leaders for the amount of time desired for their dances
  - Gets conflicts from dancers and rehearsal leaders
  - Schedules each rehearsal
- Choreographers
  - Dance choreography originators
- Rehearsal leaders
  - Lead the dances being rehearsed
  - Usually done by the choreographers
- Dancers
 
## Scheduling rehearsals
Rehearsals are a time when dancers learn and practice the dances for a production.
The time required or available for rehearsing each dance will vary between when they
are first introduced and when the last rehearsal occurs.

Schedules are set periodically to allow the flexibility of meeting the artistic
levels needed for the performance. The director arranges for venues and time slots
periodically and schedules the rehearsals as needed. Key aspects involve collecting
when each leader or dancer might not be available for a time slot and allocating
the time to achieve production-ready performance efficiently.

## Potential Conflicts
Dancers and leaders are aware of the normal venue availability.
In addition to scheduled availability, some venues may be polled to get additional
rehearsal resources. The dancers and leaders report times when they won't be available
for rehearsing. These reports are "natural language". For example, "Monday 2-4" would 
mean that the reporter could not meet on any Monday between 2 PM and 4 PM. They
might also report date ranges when they will be unavailable. 

This type of reporting isthe messiest part of the problem, as it tends to include reports 
whose meaning is ambiguous.

## Data
For the most part, data are collected in tables. Typically, these are in Google Sheets.
### Tables
- Dancers - dancer_id, name, contact info
- Dance numbers - dance_id, name, choreo_id, leader_id, elapsed_time
- Choreographers - choreo_id, name, contact info (not used for scheduling)
- Rehearsal Leaders leader_id, name, etc.
- Requirements leader_id, dance_id, minutes_requested
- Conflicts - dancer_id, text
- Cast - dance_id - dancer_id matrix
- Show order - list of dance_ids in the order of the performance.
- Venue schedule = name, date, time-range

## Current heuristic
- Total the minutes requested from the requirements data
- Determine whether that exceeds the time alloted in the venue_schedule
- If it does, try to poll for additional time
- Cut time, if necessary, in requirements
- Set per dancer actual conflicts after mapping potential conflicts against the venue_schedule
- Determine dance with conflicts.
- Starting with the dances with the most conflicts, assign them to a slot
- Complete schedule from dances with no conflicts
- Create sheet of the schedule and email pdf version of it.
