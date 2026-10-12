# skill-to-bot Documentation

This directory is the design source of truth for the `skill-to-bot` robot skill transfer project. The existing architecture and development documents define requirements; the requested build checklists track their execution and verification. Maintain these documents in place.

## Documents

- `../README.md` - project overview and current build target.
- `architecture/README.md` - architecture document index and promotion rules.
- `architecture/architecture-01.md` - initial minimal challenge MVP architecture.
- `architecture/architecture-final.md` - final envisioned architecture and expansion roadmap.
- `architecture/development-rules.md` - mandatory implementation, naming, testing, UI, CSS, and code style contract.
- [Build 01 checklist](../dev_plans/build-01.md) - build sequence, setup verification, and completion gates.
- [Build 02 checklist](../dev_plans/build-02.md) - Tier 1 selection, support reasoning, ordered transport and cumulative verification.

## Source of truth rule

Names must remain traceable across the design and implementation.

`DFD Name = Directory Name = Primary Module Name = Documentation Name`

Formatting may change only to match the medium. For example, `Skill To Robot` in a diagram becomes `skill_to_robot` in Python and directory names.

The project name is always `skill-to-bot`. `Skill To Robot` is a pipeline process, not an alternate project name.

## Implementation priority

Build `architecture-01.md` first. Do not implement items from `architecture-final.md` unless they are explicitly promoted into the active architecture.
