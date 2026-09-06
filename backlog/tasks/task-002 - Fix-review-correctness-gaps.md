---
id: TASK-002
title: Fix review correctness gaps
status: Done
assignee:
  - Codex
created_date: '2026-09-05 21:20'
updated_date: '2026-09-05 21:35'
labels: []
dependencies: []
references:
  - src/case_parser/processor.py
  - src/case_parser/patterns/airway_patterns.py
  - src/case_parser/patterns/procedure_patterns.py
  - src/case_parser/standalone_exports.py
  - batch_process.py
  - sort_logs.py
priority: high
type: bug
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Full-codebase review found silent date loss on mixed formats, over-broad extraction/categorization patterns, operator-script data-loss paths, and a few empty-input crashes. Fix the confirmed correctness gaps without a workbench split or a breaking ML feature-vector change.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Mixed US/ISO date batches keep the original calendar dates
- [x] #2 Chest/NG tubes are not extracted as Oral ETT; laryngeal-mask text is not also Mask
- [x] #3 AV fistula is not intracerebral; DEEP VEIN THROMBECTOMY is not excluded by EP
- [x] #4 Heart-block notes do not route standalone OB cases to the blocks workbook
- [x] #5 sort_logs refuses identical input/output dirs; batch_process errors on format_name collisions and warns on unpaired files
- [x] #6 Empty cases_to_dataframe succeeds; stale standalone workbooks are removed
- [x] #7 Relevant tests pass
<!-- AC:END -->
