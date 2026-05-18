
<!-- BACKLOG.MD MCP GUIDELINES START -->

<CRITICAL_INSTRUCTION>

## BACKLOG WORKFLOW INSTRUCTIONS

This project uses Backlog.md MCP for all task and project management activities.

**CRITICAL GUIDANCE**

- If your client supports MCP resources, read `backlog://workflow/overview` to understand when and how to use Backlog for this project.
- If your client only supports tools or the above request fails, call `backlog.get_backlog_instructions()` to load the tool-oriented overview. Use the `instruction` selector when you need `task-creation`, `task-execution`, or `task-finalization`.

- **First time working here?** Read the overview resource IMMEDIATELY to learn the workflow
- **Already familiar?** You should have the overview cached ("## Backlog.md Overview (MCP)")
- **When to read it**: BEFORE creating tasks, or when you're unsure whether to track work

These guides cover:
- Decision framework for when to create tasks
- Search-first workflow to avoid duplicates
- Links to detailed guides for task creation, execution, and finalization
- MCP tools reference

You MUST read the overview resource to understand the complete workflow. The information is NOT summarized here.

</CRITICAL_INSTRUCTION>

<!-- BACKLOG.MD MCP GUIDELINES END -->

## Learned User Preferences

- Prefer **full codebase reviews delivered in chat**, not the `/code-review` PR workflow (no `gh pr comment`, no PR-only diff scope).
- When asked to fix the Chrome extension, **outline or implement in the extension repo** — do not land extension changes under `case-parser/chrome-extension/`.
- Several parser review findings are **accepted tradeoffs** (do not re-propose unless asked): e.g. anesthesia defaulting to GA for unmapped MPOG types, broad `except Exception` / swallowed row errors, intracerebral unknown-approach behavior, loose service-name categorization rules, ML thread-pool behavior, silent ML disable when model missing.
- **PHI logging in the extension is acceptable** to the user when fixing extension behavior.

## Learned Workspace Facts

- The ACGME Chrome extension is maintained in a **separate repository**: `acgme-case-parser-extension` (not `case-parser/chrome-extension/`).
- The Python parser defines the Excel contract: hidden `_meta` sheet (`version`, `format_type`), default **`CaseLog`** data sheet, and output labels such as `Double Lumen Tube`, `Pulmonary Artery Catheter`, `Electrophysiologic mon`, `Invasive neuro mon`, and procedure category `Intrathoracic non-cardiac`.
- Extension work the user cares about: **parser label alignment** (aliases/maps), **`_meta` + CaseLog sheet selection**, and **thoracic intrathoracic cases defaulting to DLT** when airway is undocumented.
