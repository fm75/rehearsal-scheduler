# Look Up Tables Worksheet Specs

## Workbook
I want a program to create a workbook in a Google Workspace Folder.


Workbook Name
- Look Up Tables

Worksheet Name
- dances

Column Names
- dance_id
- name
- music
- duration
- minutes
- seconds
- duration_seconds

Protected
- Row - Column Headings
- column - dance_id
- column - duration
- column - duration_seconds


Formulas
- duration = ArrayFormula TO_TEXT(minutes)&":"&TO_TEXT(seconds)
- duration_seconds = ArrayFormula 60*minutes+seconds
- dance_id = d_01, d_02, ...