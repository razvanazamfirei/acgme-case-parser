---
id: TASK-001
title: Keep resident export names discoverable
status: Done
assignee:
  - Codex
created_date: '2026-09-05 02:47'
updated_date: '2026-09-05 02:51'
labels: []
dependencies: []
references:
  - batch_process.py
  - tests/test_batch_process.py
priority: medium
type: bug
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Supported resident export filenames can be normalized into an order that does not identify their corresponding configured resident list entry. Batch generation must continue to find these residents so their case logs are not silently skipped.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Supported resident filename forms produce paths that remain discoverable by the resident list
- [x] #2 Regression tests cover pair discovery through output-name formatting
- [x] #3 Relevant test suite passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Keep normalized resident keys for CaseList/ProcedureList matching and error identifiers, but derive the display/output name from the original CaseList filename stem.
2. Add a regression that discovers a First.Supervised_Last pair and verifies the generated output path uses First Last; retain coverage for the comma form.
3. Run focused batch and sorter tests, then the project quality checks. The full pending diff was reviewed; no additional confirmed correctness defect was identified outside this output-name ordering issue.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Kept pair matching on normalized keys while deriving output labels from the original CaseList filename. Reviewed the rest of the pending parser change set; no additional confirmed functional regression was found. Applied formatter-only cleanup to the pending sorter and CSV aggregation edits.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed batch output naming for supported First.Supervised_Last exports. `find_resident_pairs` still uses normalized keys to pair CaseList and ProcedureList files, while `process_resident` now formats the original CaseList stem for resident folders and workbook names. Added an end-to-end regression from pair discovery through generated output names and formatted the related pending files.

Validation: `uv run pytest -q` (369 passed); targeted Ruff and formatter checks across the modified parser files; `ty check batch_process.py` passed. Repository-wide Ruff and `ty check` retain unrelated baseline findings in processor and ML code.
<!-- SECTION:FINAL_SUMMARY:END -->
