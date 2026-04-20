# Class: McaCutlistReports

## Role in report chain
Orchestrates generating one or more report outputs (cover/detail/summary) and print medium routing.

## Notable methods
- `run()`
- `createReports()`
- `runReport(...)`
- `runReport2File(...)`
- `runReport2Printer(...)`
- `markProcessed(Query)` (static)

## Notes
Often called from `McaCutlistFilesReports` pipeline after query validation and contract setup.
