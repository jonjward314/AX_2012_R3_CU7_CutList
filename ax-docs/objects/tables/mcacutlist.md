# Table: McaCutlist

## Purpose
Persistent cutlist transaction table.

## Key Fields
- Identity/context: `SalesLineRefRecId`, `KanbanId`, `PWSBuildScheduleId`
- Item modeling: `ItemId`, `ModelItemId`, `ModuleItemId`, `ComponentItemId`
- Qty metrics: `Qty`, `KitQty`, `Pieces`, `Usage`, `UnitId`
- Routing/location: `InventSiteId`, `InventLocationId`, `WMSLocationId`, `WrkCtrId`, `ShipToWarehouse`, `MoveToAreaId`
- Reporting metadata: `Pattern`, `Notes`, `BluePrint`, `Prefix`, `CutGroupId`, `MachineFilename`
- Processing state: `IsCutlistProcessed`

## Methods used by report stack
`getModelPrefixes`, `getCutGroups`, `real2FractionStr`, `usageCalcRounding` (referenced by DP).
