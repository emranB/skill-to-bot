# Development Rules

## 1. Purpose

This document is the implementation contract for contributors working on `skill-to-bot`. Drawing Architecture controls active scope and ownership; this document controls development practice. Historical video documents do not override the active drawing contract.

The priorities are clarity, consistency, traceability, maintainability, and a polished but simple user experience.

## 2. Source of truth and naming

The architecture documents define component ownership and boundaries.

The canonical project name, root directory, repository name, and Compose project name are `skill-to-bot`. The web package name is `@skill-to-bot/web`. `Skill To Robot` names only the simulation pipeline process. Runtime service names are `simulation`, `orchestrator`, and `web`.

Canonical rule:

`DFD Name = Directory Name = Primary Module Name = Documentation Name`

Only formatting changes between media.

Examples:

- Diagram: `Stroke Processing`
- Directory: `stroke_processing/`
- Python module: `stroke_processing.py`
- Test: `test_stroke_processing.py`

Do not introduce parallel modules such as `mapping_engine` when the canonical architecture name is `Skill To Robot`. Keep the embodiment boundary inside that module, not a new service.

### Naming conventions

Python:

- files and directories: `snake_case`
- variables: `snake_case`
- functions: `snake_case`
- constants: `UPPER_SNAKE_CASE`
- classes: `PascalCase`
- private implementation members: leading underscore only when genuinely private

TypeScript and React:

- variables and functions: `camelCase`
- constants: `UPPER_SNAKE_CASE` only for true module-level constants; otherwise use `camelCase`
- components, types, and interfaces: `PascalCase`
- component files: `PascalCase.tsx`
- non-component utility files: `camelCase.ts`

Names must describe purpose. Avoid unexplained abbreviations.

## 3. Formatting

### Python

- 4 spaces per indentation level.
- Never use tabs for indentation.
- Target a maximum line length of 100 characters where practical.
- One blank line between logical blocks inside functions only when it improves readability.
- Two blank lines between top-level classes and functions.
- Prefer explicit imports.
- Keep imports grouped: standard library, third-party packages, local modules.

### TypeScript, React, CSS

- 2 spaces per indentation level.
- Use semicolons consistently.
- Prefer single quotes in TypeScript unless tooling establishes another repository-wide rule.
- Keep JSX shallow. Extract a component when a section has a distinct responsibility or becomes difficult to scan.
- Do not create wrapper components with no behavioral or visual purpose.

Use automatic formatters where appropriate, but formatter configuration must match these rules.

Install `requirements-dev.txt` into the project environment. Run `python -m ruff check src/backend src/scripts tests` and `python -m ruff format --check src/backend src/scripts tests` with that environment's Python, from the repository root. Apply formatting with `python -m ruff format src/backend src/scripts tests` before committing. Ruff is pinned to 0.11.13 in both the development requirements and `pyproject.toml`; update both together. A different global formatter must not silently change repository formatting.

## 4. Comments and documentation

Comments must explain information the code cannot express clearly by itself.

Do not narrate obvious code.

Bad:

```python
# Increment index by one
index += 1
```

Good:

```python
# Keep the first point because it anchors the stroke endpoint.
index += 1
```

### File header

Every source file uses the same concise header form:

```text
Purpose: <one sentence describing the responsibility of this file.>
```

Use the comment syntax appropriate for the language. Do not add author names, generated timestamps, legal boilerplate, ASCII art, or change logs to source file headers unless legally required.

JSON files use valid JSON without comments. A source placeholder contains only its purpose header and an explicit unimplemented marker; it must not pretend to provide working behavior.

### Function and class documentation

- Public functions and classes should have concise documentation when purpose, parameters, return value, side effects, or failure behavior are not obvious from the signature.
- Keep documentation factual and short.
- Do not repeat parameter names without adding useful information.
- Private trivial helpers do not need documentation merely to satisfy a quota.
- Keep documentation style symmetric across files.

### Comment tone

Comments must read like normal professional engineering notes.

Avoid:

- excessive comments
- tutorial narration inside production code
- jokes or conversational filler
- authorship attribution or tool-specific narration
- phrases such as `obviously`, `simply`, `just`, or `magic`
- decorative Unicode symbols
- emoji
- em dashes and en dashes in code comments and project documentation

Use ordinary punctuation and direct sentences.

## 5. Code design

- Prefer the smallest implementation that satisfies the active architecture.
- Do not build future architecture speculatively.
- Keep functions focused on one responsibility.
- Prefer explicit data flow over hidden global state.
- Avoid mutable module-level state unless the design requires it.
- Use dependency injection where it materially improves testing, not as ceremony.
- Do not introduce abstractions until at least one concrete responsibility requires them.
- Do not create a class when a small function is clearer.
- Do not create a network service for an internal algorithmic boundary.
- Keep robotics control loops close to the simulation state they require.
- Fail with useful errors at service boundaries.
- Validate external inputs.

## 6. Constants and configuration

A value is a constant when it is conceptually fixed by the implementation. Use `UPPER_SNAKE_CASE` in Python.

A value belongs in `config.json` when an operator or experiment may reasonably tune it, such as:

- drawing speed
- contact tolerance
- camera FPS
- simulation timestep
- render dimensions
- evaluation tolerance

A value belongs in `.env` when it depends on the execution environment, such as:

- service hostnames
- ports
- environment mode
- external credentials if introduced later

Do not hardcode environment-specific URLs or secrets.

## 7. Environment files and Git

Every runtime service and the root system may have a local `.env`.

Every corresponding location must provide a committed `.env.example` with safe placeholder values.

Never commit:

- `.env`
- credentials
- tokens
- private keys
- generated runtime data
- unapproved personal JSON demonstrations and archived local recordings
- Python virtual environments
- `node_modules`
- IDE-specific state that is not intentionally shared
- build output
- coverage output
- temporary simulation output

The root `.gitignore` is the default repository policy. Add a nested `.gitignore` only when a service has unique generated files that are clearer to manage locally.

Build 04 explicitly approves the three captures listed in `evidence/manifest.json` and representative native simulator outputs for public submission. This narrow evidence exception does not permit publishing other personal/runtime data. Preserve raw bytes, verify checksums and label provenance honestly. Full evaluation traces stay in ignored local exports.

Branch names, commit messages, and pull request descriptions must describe the project change. Do not add tool attribution, generated-by notices, or automatic co-author trailers. Commit and push only when explicitly requested.

## 8. Testing contract

Prioritize a small number of complete user workflows and real container/physics checks. Do not add a test file for every UI detail or a second frontend test framework. Retain focused service regressions for safety, contract boundaries, persistence, and failure handling.

When a service regression needs a separate file, use the owning module name:

```text
src/stroke_processing/stroke_processing.py
tests/test_stroke_processing.py
```

Root `tests/` contains cross-service and complete pipeline tests.

Browser tests use Playwright on desktop and mobile. Root tests cover drawing-to-robot execution, actual ink/trace, paper retargeting, lifecycle, and isolated dependency recovery. The GitHub workflow builds the runtime and executes these complete paths; isolated service tests are used when their modules change.

Tests should be:

- deterministic where practical
- isolated
- small enough to diagnose failures
- explicit about expected behavior
- free of arbitrary sleeps when a readiness condition can be checked

A bug fix should include a regression test when practical.

Drawing physics tests verify all six synthetic fixtures, real pen-tip ink, stroke style/pressure, pen-up gaps, tracking and bidirectional shape thresholds, encoded-video agreement with actual rendering and a second reachable paper pose. Optional local personal replays preserve raw bytes. Fixtures are not personally collected challenge evidence. Physical stylus pressure remains a manual gate. Run service physics, root outage/physics and browser execution serially. Communication failure must not trigger automatic robot-command retry.

The public Build 04 comparison reuses the three approved captures and fixed manifest poses. Extract each skill once, preserve unsuccessful baseline outcomes and record both geometric proximity and physical contact. Compare only the declared compensation settings; do not tune poses or acceptance limits after seeing results. Keep numerical thread limits equal across methods. A clean source snapshot must prepare the approved inputs without private data.

Do not make a unit test depend on the full Docker stack unless the behavior is genuinely integration-level.

## 9. Service lifecycle contract

Every service uses the same lifecycle names:

- `build-and-run.sh`
- `run.sh`
- `stop.sh`
- `clean.sh`

Do not invent alternate lifecycle names for individual services.

Scripts should use strict shell behavior and return non-zero status on failure.

`build-and-run.sh` should provide a known-clean executable environment. It may remove containers, generated state, and build artifacts required for reproducibility. It must not silently delete persistent human demonstrations or other source data.

## 10. API and failure behavior

Backend services should expose, where applicable:

- `/health`
- `/ready`
- `/version`

Use consistent response shapes across services.

Network calls must have timeouts. Retries must be bounded. Dependency failure must be surfaced as a state the orchestrator can report.

Do not allow one unavailable service to terminate another service.

## 11. Logging

Use structured, concise logs.

Each important log should answer at least one of these:

- What happened?
- Which run or operation did it affect?
- What should an engineer inspect next?

Do not log every frame or simulation step by default.

Use conventional levels: debug, info, warning, error.

Do not log secrets or full environment contents.

## 12. UI design principles

Use a compact, readable drawing workspace with paired human and robot surfaces.

Home is the default tab: completed human handwriting with native previews, saved demonstrations and direct drawing actions. Show the latest eligible run per human demonstration, up to three; never substitute fixtures, incomplete runs or fabricated previews. Empty installations remain empty until a human drawing completes. Reuse library rows, loading/empty states and request handling across views. Keep one owner for drawing-session state and one non-overlapping polling loop. Run-history deletion requires confirmation, rejects active runs and persists removal while retaining demonstrations, execution evidence and request-ID deduplication. State this retention in the dialog; do not present history removal as disk cleanup.

Introduce the product with brief, factual copy that distinguishes simulation from hardware. Keep one page heading, obvious actions and visible native examples. Motion is CSS-only and restrained: never hide initial content, shift button geometry or ignore reduced-motion preferences. Recording shortcuts are read-only; they must not execute a robot command.

Core characteristics:

- light theme
- white or very lightly tinted page background
- clear, compact headings
- consistent spacing
- unframed page sections and genuinely framed media/tools
- minimal text
- touch-sized primary controls
- subtle borders
- restrained shadows
- restrained 4-8px corners
- one obvious primary action per screen or section
- status shown clearly without visual noise
- Pointer Events drawing with pen/touch/mouse, optional pressure/tilt and no panning
- Undo, Clear and one Save & Run action
- inline Logs, Raw Input, Skill and Trace details
- actual drawing phases, stroke progress and honest failure states

Avoid:

- unstructured dense dashboards
- tiny text
- excessive cards inside cards
- heavy gradients
- neon colors
- glassmorphism
- large areas of dark UI
- excessive icons
- decorative animation
- multiple competing primary buttons

## 13. UI color system

Use CSS custom properties. These are the default approved design tokens.

```css
:root {
  --color-page: #f8fafd;
  --color-surface: #ffffff;
  --color-surface-subtle: #f1f4f9;
  --color-surface-blue: #eef4ff;
  --color-surface-green: #eef8f1;
  --color-surface-yellow: #fff8e6;
  --color-surface-red: #fceeee;

  --color-text-primary: #202124;
  --color-text-secondary: #5f6368;
  --color-text-muted: #80868b;

  --color-border: #e1e5eb;
  --color-border-strong: #c9d0da;

  --color-primary: #1a73e8;
  --color-primary-hover: #1765cc;
  --color-primary-soft: #e8f0fe;

  --color-success: #188038;
  --color-warning: #b06000;
  --color-error: #d93025;

  --color-focus: #1a73e8;
}
```

Use semantic variables in components rather than scattering literal hex values throughout CSS.

The palette is intentionally light and restrained. Color should communicate hierarchy and status, not decorate every surface.

## 14. Typography

Preferred font stack:

```css
font-family: Inter, Roboto, Arial, sans-serif;
```

Use Inter as the primary UI font when available. Roboto is the preferred fallback for a clean Google-like visual character. Do not require a proprietary font.

Default typography scale:

```css
--font-size-xs: 12px;
--font-size-sm: 14px;
--font-size-base: 16px;
--font-size-lg: 18px;
--font-size-xl: 22px;
--font-size-2xl: 28px;
--font-size-3xl: 36px;
```

Recommended usage:

- helper/status text: 12 to 14px
- normal body text: 16px
- emphasized body or small card title: 18px
- section title: 22 to 28px
- page title: 36px
- workspace headings: 22 to 28px; do not use hero-scale type in tools or panels

Use primarily 400, 500, and 600 font weights. Avoid unnecessary 700 to 900 weight text.

Body line height: approximately 1.5.
Heading line height: approximately 1.15 to 1.25.

## 15. Spacing and sizing

Use an 8px-based spacing system with a 4px half-step when needed.

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 24px;
--space-6: 32px;
--space-7: 48px;
--space-8: 64px;
```

Defaults:

- normal component gap: 16px
- card padding: 24px
- major section gap: 24 to 32px
- desktop content maximum width: approximately 1200px
- primary button height: 48 to 52px
- standard input height: 44 to 48px
- minimum comfortable touch target: 44px

## 16. Borders, radius, and shadows

Default border:

```css
border: 1px solid var(--color-border);
```

Radius scale:

```css
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;
--radius-pill: 999px;
```

Use at most `8px` for repeated items, framed tools and dialogs. Page sections are not floating cards, and cards must not contain other cards.

Shadows should be subtle and uncommon:

```css
--shadow-soft: 0 1px 3px rgba(60, 64, 67, 0.12), 0 1px 2px rgba(60, 64, 67, 0.08);
```

Prefer a border with no shadow for ordinary panels. Use the soft shadow only when elevation communicates interaction or hierarchy.

## 17. Buttons

Primary buttons:

- primary blue background
- white text
- 48 to 52px high
- medium font weight
- at most 8px radius
- clear hover and focus states

Secondary buttons:

- white or subtle surface background
- standard border
- primary or primary-text color

Destructive actions use error red only when the action is genuinely destructive.

Button labels should normally be short verbs or verb phrases such as:

- `Save & Run`
- `Undo`
- `Reset`
- `Try Again`

## 18. Responsive behavior

Design mobile-first.

- Single-column layout is the default.
- Add multi-column presentation only when screen width makes it clearer.
- Human and simulation views may sit side by side on desktop and stack vertically on mobile.
- Do not hide essential functionality behind hover-only interactions.
- Controls must remain usable by touch.

## 19. Accessibility

- Use semantic HTML.
- Provide keyboard focus states.
- Keep run-detail tabs keyboard navigable and use a focus-contained, Escape-dismissible confirmation dialog.
- Maintain readable contrast.
- Associate labels with controls.
- Provide text alternatives for meaningful imagery.
- Do not communicate success, warning, or error using color alone.
- Respect reduced-motion preferences if animation is added.

## 20. Human-readable output rule

All user-facing text, documentation, code comments, errors, and logs should sound like concise professional engineering work written by a person.

Avoid filler and unnecessary headings. Avoid exaggerated claims. Avoid decorative punctuation. Do not use emoji or em dashes. Prefer short, ordinary sentences.

## 21. Change discipline

Before adding a new container, directory, major dependency, persistent datastore, or architectural abstraction:

1. Identify the requirement it solves.
2. Confirm the existing architecture cannot solve it cleanly.
3. Update the appropriate architecture document.
4. Keep canonical names synchronized.
5. Add or update tests.

Architecture changes happen deliberately. Implementation must not silently redefine the architecture.

## 22. Build and implementation handoff

Drawing Build 03 and submission Build 04 implementation are authorized. The active architecture is `architecture.md`; their build plans record executed evidence and external gates.

- Configuration owns non-secret tunable defaults; environment files own deployment values. Validate both service boundaries and finite numerical values.
- `contracts/demonstration.schema.json` and `contracts/skill.schema.json` strictly separate immutable raw input from robot-independent skill. Keep actual robot traces independent.
- Mark checks complete only after execution. Synthetic fixtures, actual simulation and physical Surface Pen acceptance are separate evidence categories.
- Lifecycle scripts delegate to `src/scripts/lifecycle.sh`, preserve demonstrations/runs and never overwrite local settings.
- Linux containers are the runtime target; use Git Bash on Windows or working Bash on Linux. Do not claim native PowerShell lifecycle support.
- Keep unapproved personal demonstration data out of Git. Do not restore the removed video pick-and-place archive into the active tree.
- Active docs are README, Drawing Architecture, Development Rules, Build 03 and Build 04. Do not proliferate Markdown.
- No commit or push without explicit authorization. Archival tracked renames use `git mv` as requested.

Implement incrementally through strict input, processing, real Panda drawing and measured ink before final UI polish. Quantitative failure must remain visible; never render desired input as simulated output or claim manual hardware validation from generated fixtures.
