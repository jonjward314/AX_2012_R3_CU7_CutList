# Class: McaCutlistReportContract

## Type
Data contract class.

## Data Members
- `parmQuery` (AIF query type attribute bound to `McaCutlistQuery`)
- `parmCoverSheet`
- `parmPrintDetail`
- `parmPrintSummary`

## Methods
- `setQuery(Query)` stores base64 packed query.
- `getQuery()` reconstructs query.
- `setFromContract(McaCutlistCreateContract)` copies packed query.

## Notes
- This contract is the handoff boundary from controllers/orchestrators into report DP.
