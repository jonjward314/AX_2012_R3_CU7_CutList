# SR423365 - Development Request: Change Cutsheet PDFs

## Service Request Details
| Field | Value |
|-------|-------|
| Title | Change Cutsheet PDFs |
| Jayco Change ID | 1560 |
| Requested By | Rohrer, Nichole |
| Supervisor | Forgey, Ryan |
| Assigned To | Ward, Jonathon |
| Priority | Low |
| Source | Portal |
| Status | **In Progress — Step 6: Test in DEV → UAT → Production pipeline** |
| TFS Branch | DEV-AX-JDEV12 |

## Request Description
- Change PDF formatting and add additional fields
- **Justification:** Better utilization of reports by side departments

## Current Status (2026-04-14)

> **Testing environment changed from Sandbox → DEV.**
> Sandbox is off the table (permissions wall hit on deployment attempt).
> UAT is being refreshed today (per Shook, Brad). DEV refresh process being provided
> by Burke, David so Jon can refresh at his leisure going forward.

- Kelly Gordon is back from sick leave + vacation (back as of Apr 15)
- Kelly has confirmed she is **ready to test** — asking which AX environment
- **Blocker:** DEV needs to be refreshed before Kelly can meaningfully test
- Dave Burke to provide self-serve DEV refresh process
- Once DEV is refreshed: Kelly tests cutsheets in DEV, not Sandbox

### Previous Status (2026-03-24)
- Changes redeployed to DEV on **03/24/2026** (CS 7737 — JDEV12 to DEV)

### Previous Status (2026-03-18/19)
- Changes made **03/18/2026** — resubmitted for DEV testing
- Message to Kelly Gordon (Teams):
  > "So I hit a lucky streak and should have cutlist for me to test in DEV tomorrow.
  > Assuming that goes well I will reach back out to you for further testing."

## Workflow Progress
| Step | Activity | Status |
|------|----------|--------|
| 1 | Supervisor Review | ✅ Complete |
| 2 | IT Review | ✅ Complete |
| 3 | Finance Review | ✅ Complete |
| 4 | Pending Assignment | ✅ Complete |
| 5 | Development | ✅ Complete |
| **6** | **Test in DEV** | 🔄 **In Progress** |
| 7 | Hold for UAT | ⏳ Pending |
| 8 | Test in UAT | ⏳ Pending |
| 9 | Approve for PRD | ⏳ Pending |
| 10 | Hold for Prod | ⏳ Pending |
| 11 | Complete | ⏳ Pending |

> **Note:** DEV Test failed twice previously (02/17/2026 and 03/04/2026) before current attempt.

## TFS Changeset History
| Changeset | Date | Description |
|-----------|------|-------------|
| 7673 | 01/20/2026 | Initial resolve — J_SR423365_1560_Enhance_Cutsheets |
| 7675 | 01/21/2026 | [DEV-AX-12 to DEV] SR423365 - 1560 - Enhance Cutsheets Reports |
| 7678 | 01/26/2026 | Associated |
| 7679 | 01/26/2026 | Changed Coversheet header to go across the top (consistent with other reports) |
| 7706 | 02/24/2026 | Associated |
| 7707 | 02/24/2026 | [DEVAX-JDEV12 to DEV] SR423365 - 1560 - Enhance_Cutsheets |
| 7710 | 02/25/2026 | Associated |
| 7712 | 02/25/2026 | Associated |
| 7713 | 02/25/2026 | Enhance Cutsheet Changes Redeploy [Forced] |
| 7723 | 03/10/2026 | Enhance Cutsheet Changes Redeploy + **Piece Fields added to Selection** [Forced] |
| 7726 | 03/18/2026 | Associated |
| 7730 | 03/20/2026 | Associated |
| 7731 | 03/20/2026 | Enhance Cutsheet Changes Redeploy (ref CS 7725 from 03/18) |
| 7735 | 03/23/2026 | [DEV-AX-JDEV12] Enhance Cutsheet Changes Redeploy |
| 7736 | 03/24/2026 | Associated |
| 7737 | 03/24/2026 | [DEV-AX-JDEV12 to DEV] Enhance Cutsheet Changes Redeploy |

## Key Design Decisions

### File Naming Convention
Agreed format (Option 1 — confirmed by Rhonda Rowe 06/17/2025):
```
[Site]_[ScheduleRange]_[ModelRange]_[PrefixRange]_[Machine]_[Proto]_[CutGroups]_DocType.pdf
```
**Important:** `[Proto]` segment is **conditional** — only included when the cutlist actually
meets proto classification criteria. Not every cutlist is a proto. (Rhonda Rowe 06/17/2025)

### Path Length Warning
Full naming convention + folder path risks exceeding Windows max path length (especially
over the network). Recommended: use full naming in **filename only**; keep folder structure
shorter for network/backup/email compatibility.

### Retention Policy (Millroom Folders)
Per conversation with Wilmer Beachy (06/17/2025): a blanket retention policy requires all
Millroom-related folders consolidated under a **single root directory** (e.g., `\\Corp\Cutlist\Millroom\`).
Awaiting confirmation from Wilmer on feasibility.

## Stakeholders / Contacts
| Name | Role | Notes |
|------|------|-------|
| Rohrer, Nichole | Requestor | Original submitter |
| Forgey, Ryan | Supervisor | Approver |
| Rowe, Rhonda | End User — Millroom | Confirmed file naming Option 1, [Proto] conditional |
| Miller, Jennifer | End User — CC | Copied on folder structure discussions |
| Beachy, Wilmer | IT/Infrastructure | Retention policy input |
| Gordon, Kelly | Tester | Next for DEV testing once self-test passes |

## Pipeline — DEV → UAT → Production

### Step 6 — DEV Confirmation (current)
> **Environment:** DEV (Sandbox removed — permissions wall). UAT refreshing today.
> Dev box and DEV refresh process being provided by Burke, David.
- [ ] Obtain DEV refresh process from Burke, David
- [ ] Refresh DEV environment
- [ ] Notify Kelly Gordon — confirm DEV is ready for her to test
- [ ] Add pertinent source files to this repo (SR423365 folder)
- [ ] Use Claude Code to document the changes from source
- [ ] Kelly sign-off → advance to Step 7

### Step 7–8 — UAT
- [ ] Advance to Step 7: Hold for UAT
- [ ] UAT testing with Rhonda Rowe / Millroom team
- [ ] Confirm file naming convention: `[Site]_[ScheduleRange]_[ModelRange]_[PrefixRange]_[Machine]_[Proto]_[CutGroups]_DocType.pdf`
- [ ] Validate [Proto] conditional segment correct
- [ ] Confirm path length within Windows limits over network
- [ ] UAT sign-off → advance to Step 9

### Step 9–11 — Production
- [ ] Step 9: Approve for PRD
- [ ] Step 10: Hold for Prod — coordinate with Burke, David for formal promotion
- [ ] Step 11: Complete — close SR423365
