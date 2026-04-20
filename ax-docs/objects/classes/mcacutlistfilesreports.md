# Class: McaCutlistFilesReports

## Role
Top-level orchestration for selected actions: assign prefix, files, reports, labels, mark processed.

## Sequence (from code)
1. Save original query
2. Run file generation (optional)
3. Run report generation (optional)
4. Run labels (optional)
5. Mark processed (optional)

## Dependencies
`McaCutlistFile`, `McaCutlistReports`, `McaCutlistLabels`, `McaCutlistAssignPrefix`.
