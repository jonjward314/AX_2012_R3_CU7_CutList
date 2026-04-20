# McaCutlistBaseReport

## Overview
- **Report object:** `McaCutlistBaseReport`. **[Confirmed from XPO]**
- **Designs:** `WorkOrderCoverSheet`, `WorkOrderDetail`, `WorkOrderSummary` selected by controller `parmReportName(...)`. **[Confirmed from XPO]**
- **Primary data provider:** [`McaCutlistReportDP`](../objects/classes/mcacutlistreportdp.md). **[Confirmed from XPO]**
- **Primary contract:** [`McaCutlistReportContract`](../objects/classes/mcacutlistreportcontract.md). **[Confirmed from XPO]**
- **Purpose:** Generate cutlist print artifacts for millroom/cutting operations and downstream departments. **[From analysis notes]**

## Business Context
- Supports wave/build-schedule driven cut preparation and printable shop-floor instructions. **[From analysis notes]**
- Typical users: production planners, millroom operators, support analysts. **[Inferred]**

## Execution Flow
```mermaid
flowchart LR
A[McaCutlistRecords / FilesReports action] --> B[Report controller main()]
B --> C[preRun/prePrompt set query + flags]
C --> D[McaCutlistReportContract]
D --> E[McaCutlistReportDP.processReport]
E --> F[processCover/processDetail/processSummary]
F --> G[McaCutlistTmp TempDB]
G --> H[SSRS dataset McaCutlistTmp]
H --> I[WorkOrderCoverSheet/Detail/Summary render]
```

- Entry points by design:
  - Cover: `McaCutlistCoverReportController.main()` -> `WorkOrderCoverSheet`
  - Detail: `McaCutlistDetailReportController.main()` -> `WorkOrderDetail`
  - Summary: `McaCutlistSumReportController.main()` -> `WorkOrderSummary`
  **[Confirmed from XPO]**

## Data Sources
- `McaCutlistQuery` (RDP query attribute) with fallback creation when no runtime query passed. **[Confirmed from XPO]**
- Runtime enrichment uses `SalesLine::findRecId`, `InventTable::find(...).productName(...)`, and `McaCutlistMoveToAreas::find(...)`. **[Confirmed from XPO]**
- Temp staging table: `McaCutlistTmp` (TempDB). **[Confirmed from XPO]**
- AX hidden dataset filters include partition/company/user context query parameters in the RDL. **[Confirmed from XPO]**

## X++ Logic Deep Dive
- `processReport()` dispatches by booleans from contract:
  - `parmCoverSheet()` -> `processCoverReport()`
  - `parmPrintDetail()` -> `processDetailReport()`
  - `parmPrintSummary()` -> `processSummaryReport()`
  **[Confirmed from XPO]**
- Cover and summary paths add `GROUP BY` to query via `SysQuery::findOrCreateGroupByField(...)`. **[Confirmed from XPO]**
- Detail path performs row-level copy + formatting (`real2FractionStr`, filename split, dynamic page grouping key). **[Confirmed from XPO]**
- Detail computes usage with `usageCalcRounding()` and sets unit from `InventTableModule::find(..., ModuleInventPurchSales::Invent).UnitId` (2024 change note embedded in X++ comments). **[Confirmed from XPO]**

## Parameters & Filters
- Contract fields:
  - `packedQuery` (`parmQuery` + `setQuery/getQuery`)
  - `printCoverSheet`, `printSummary`, `printDetail`
  **[Confirmed from XPO]**
- Controllers load query from `Args.parmObject()`. **[Confirmed from XPO]**
- Summary controller sets print flag in `preRunModifyContract`; cover/detail set corresponding flags in both prePrompt and preRun. **[Confirmed from XPO]**

## Calculated Fields / Business Rules
- `NewPageGroupBy` for cover sheet: composite of model/prefix/site/move-to/date. **[Confirmed from XPO]**
- `NewWOPageGroupBy` for detail has branch logic:
  - `UsageType::Linear` => warehouse + move-to + machine file + item
  - `UsageType::Sheet` => item + warehouse + move-to
  **[Confirmed from XPO]**
- `Pieces` in detail = `real2int(cutlist.Pieces * cutlist.KitQty)` (risk of double multiply depending on RDL expression region). **[Confirmed from XPO] [From analysis notes]**

## Output Layout Mapping
- Dataset fields include `ModelItemId`, `ComponentItemId`, `Pieces`, `KitQty`, `CutGroupId`, `MachineFilename`, `UsageType`, etc. **[Confirmed from XPO]**
- Same dataset feeds 3 designs with different grouping/visibility logic. **[Confirmed from XPO]**

## Dependencies
- Classes: controllers + contract + DP + utility table methods in `McaCutlist`. **[Confirmed from XPO]**
- Tables: `McaCutlist`, `McaCutlistTmp`, `SalesLine`, `InventTable`, `McaCutlistMoveToAreas`, `InventTableModule`. **[Confirmed from XPO]**
- Query object: `McaCutlistQuery` referenced; definition not exported in provided standalone xpo files. **[Confirmed from XPO]**

## Security & Access
- Specific privileges/duties/roles for report menu items are **Not determinable from provided XPO/MD**.
- Controllers imply Output menu-item execution path via report orchestration classes. **[Inferred]**

## Performance Considerations
- Cover/Summary query mutation (grouping on many columns) can degrade with high volume if query indexes mismatch. **[Inferred]**
- Detail per-row calls (`SalesLine::findRecId`, `InventTable::find`) are repeated and may cause DB chatter. **[Confirmed from XPO] [Inferred]**

## Edge Cases / Known Risks
- Null/blank `MoveToAreaId` yields missing move-to description. **[Confirmed from XPO]**
- Mixed semantics of `Pieces` (raw vs expanded) across paths can confuse totals. **[From analysis notes]**
- DEV/PROD conflict around `Per_Series` logic documented in notes; production snapshot here does not expose `Per_Series` in report dataset. **[From analysis notes] [Confirmed from XPO]**

## Change Impact Guidance
Retest at minimum when editing:
1. `processDetailReport()` quantity or group key logic.
2. SSRS expressions using `Pieces`, `KitQty`, `UsageType`.
3. Controller `preRun` flag-setting behavior.
4. Query ranges passed from form/report orchestration (`parmObject` query).
