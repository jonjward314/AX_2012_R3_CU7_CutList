# Total Units Calculation (Model + Prefix)

## Approved calculation rule
Use `COUNT(DISTINCT SALESLINEREFRECID)` grouped by `MODELITEMID` and `Prefix`, scoped by build schedule.

```sql
DECLARE @BuildScheduleId NVARCHAR(20) = '005180';

SELECT 
    mc.MODELITEMID,
    mc.Prefix,
    COUNT(DISTINCT mc.SALESLINEREFRECID) AS [Total Units]
FROM McaCutlist mc
WHERE mc.PWSBUILDSCHEDULEID = @BuildScheduleId
GROUP BY 
    mc.MODELITEMID,
    mc.Prefix
ORDER BY 
    mc.MODELITEMID,
    mc.Prefix;
```

## Why this is the correct rule
- The unit identity for this report requirement is the unique sales-line reference (`SALESLINEREFRECID`) within the selected build schedule.
- Totals are required at **Model + Prefix** level, so those fields are the grouping columns.
- Filtering by `PWSBUILDSCHEDULEID` keeps totals scoped to the requested document/run key and prevents cross-schedule bleed.

## AX implementation note
When populating report header totals in DP logic, use the same semantic rule as above:
- scope by document/build-schedule key,
- aggregate by `ModelItemId + Prefix`,
- count distinct `SalesLineRefRecId`.

This ensures DP-computed totals match SQL validation exactly.
