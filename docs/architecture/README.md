# Architecture Documents

This directory separates the active initial build target from the final system roadmap.

## Active document

- `architecture-01.md` is the current implementation target.

Build only what this document requires. Promote future requirements by updating this existing document in place.

## Roadmap document

- `architecture-final.md` describes the intended long-term system.

Use it to keep names, boundaries, and future direction consistent. Do not treat it as permission to add optional services, schemas, algorithms, or infrastructure to the MVP.

## Implementation contract

- `development-rules.md` defines the coding, documentation, test, UI, configuration, and lifecycle rules.

If an implementation choice is unclear, follow this order:

1. `architecture-01.md`
2. `development-rules.md`
3. `architecture-final.md`

## Promotion rule

The requested [Build 02 checklist](../../dev_plans/build-02.md) extends the verified [Build 01 baseline](../../dev_plans/build-01.md). Tier 1 selection, support reasoning, viewpoint checks and ordered transport are promoted in Architecture 01. Optional waypoints and explicit projected-table calibration require updated validators and producers to be deployed together. Preserve the existing four-service boundaries. Tier 1 remains unfrozen until the recorded physical and hosted acceptance gates pass.

A final-architecture feature becomes implementable only when the existing `architecture-01.md` promotes it and defines:

- the requirement it satisfies
- the owning container or module
- the contract change, if any
- the test coverage required

Keep scope, decisions, and contract changes in the existing authoritative documents. Do not add architecture-02, architecture-03, decision documents, or other Markdown files unless explicitly requested. The requested [Build 01 checklist](../../dev_plans/build-01.md) tracks execution and evidence; it cannot override the architecture or development contract. Architecture 01 controls scope and ownership; development rules control implementation practice; the final architecture supplies future direction only. Resolve conflicts in these documents before implementing the affected behavior.
