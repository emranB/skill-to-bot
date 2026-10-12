# Development Rules

## 1. Purpose

This document is the implementation contract for contributors working on `skill-to-bot`. Architecture 01 controls active scope and ownership, this document controls development practice, and Architecture Final is a roadmap only. Any override must be explicitly recorded in Architecture 01; a roadmap statement never overrides this contract.

The priorities are clarity, consistency, traceability, maintainability, and a polished but simple user experience.

## 2. Source of truth and naming

The architecture documents define component ownership and boundaries.

The canonical project name, root directory, repository name, and Compose project name are `skill-to-bot`. The web package name is `@skill-to-bot/web`. `Skill To Robot` names only the simulation pipeline process. Runtime service names are `perception`, `simulation`, `orchestrator`, and `web`.

Canonical rule:

`DFD Name = Directory Name = Primary Module Name = Documentation Name`

Only formatting changes between media.

Examples:

- Diagram: `Video Input`
- Directory: `video_input/`
- Python module: `video_input.py`
- Test: `test_video_input.py`

Do not introduce synonyms such as `retargeting`, `mapping_engine`, or `adapter` when the canonical architecture name is `Skill To Robot`.

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

Install `requirements-dev.txt` into the project environment. Run `python -m ruff check services tests` and `python -m ruff format --check services tests` with that environment's Python, from the repository root. Apply formatting with `python -m ruff format services tests` before committing. Ruff is pinned to 0.11.13 in both the development requirements and `pyproject.toml`; update both together. A different global formatter must not silently change repository formatting.

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
# Skip the first frame because it establishes the calibration baseline.
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

- tracking confidence
- grasp threshold
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
- local camera recordings under `data/live_demos` (retain only the directory marker in Git)
- Python virtual environments
- `node_modules`
- IDE-specific state that is not intentionally shared
- build output
- coverage output
- temporary simulation output

The root `.gitignore` is the default repository policy. Add a nested `.gitignore` only when a service has unique generated files that are clearer to manage locally.

Branch names, commit messages, and pull request descriptions must describe the project change. Do not add tool attribution, generated-by notices, or automatic co-author trailers. Commit and push only when explicitly requested.

## 8. Testing contract

Prioritize a small number of complete user workflows and real container/physics checks. Do not add a test file for every UI detail or a second frontend test framework. Retain focused service regressions for safety, contract boundaries, persistence, and failure handling.

When a service regression needs a separate file, use the owning module name:

```text
src/video_input/video_input.py
tests/test_video_input.py
```

Root `tests/` contains cross-service and complete pipeline tests.

Browser tests use Playwright on desktop and mobile. Root tests cover video-to-robot execution, failed manipulation, lifecycle, and isolated dependency recovery. The GitHub workflow builds the runtime and executes these complete paths; isolated service tests are used when their modules change.

Tests should be:

- deterministic where practical
- isolated
- small enough to diagnose failures
- explicit about expected behavior
- free of arbitrary sleeps when a readiness condition can be checked

A bug fix should include a regression test when practical.

Calibrated motion tests must check support axes and ordered paths against known projection geometry, then exercise the saved/uploaded path and actual Panda physics. Do not validate depth from raw image Y, or count a projected command completion as physical-direction truth. Record assumed measurements separately from measured calibration; missing intrinsics/corners and unverified physical views remain open Build 02 gates. Run root physics/outage checks and browser execution serially against the shared stack. A rejected episode or communication failure must not trigger an automatic robot-command retry.

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

Use a compact, readable manipulation workspace with paired source and robot media.

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
- yellow Confirm Mapping action with an exclamation icon, replaced by Run Demo after confirmation
- inline Logs, Skill, and Observations tabs under Run status
- live camera preview and Start/Stop Recording with an explicit Yes/No save prompt
- actual processing/control phases, completed steps, and honest failure states

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

- `Run Demo`
- `Upload Video`
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

Architecture 01 implementation is authorized. The initial scaffold reserved required paths; replace placeholders only with verified behavior and update `dev_plans/build-01.md` as each stage passes. Do not create roadmap-only paths.

- Configuration files define validated non-secret runtime defaults; environment files hold deployment values. Preserve the documented distinction.
- `contracts/skill.schema.json` is the versioned manipulation contract. Validate it at perception, orchestration, and simulation boundaries; never replace it with a permissive empty schema.
- Mark tests complete only after they execute and pass. Container and physics tests must use the actual runtime; mocked tests alone cannot establish pipeline success.
- Run Dockerfiles, Compose, and lifecycle scripts only once they contain reviewed executable behavior. Root and service commands delegate to the common `scripts/lifecycle.sh` implementation.
- `.gitkeep` retains any required empty directory until it contains real files. Generated run data remains ignored; persistent demonstrations are never removed by cleanup.
- `.env.example` contains safe defaults; ignored local `.env` files initially mirror it. Never overwrite existing local settings automatically.
- Linux containers are the runtime target. Root and service `.sh` commands run through the verified Git Bash executable on Windows, or a working Bash environment on Linux/WSL; do not claim native PowerShell support. The current default WSL distribution is not a usable development shell.
- Before implementation, read the root README, every existing document under `docs/`, and `dev_plans/build-01.md`. Keep requirements, decisions, dependency versions, and interfaces in the existing architecture and development documents. Track execution and validation evidence in the requested build checklist; do not add further Markdown documents unless explicitly requested.

Implementation proceeds through the skill contract and deterministic fixtures, simulation environment and robot execution, perception extraction, orchestrator coordination, web presentation, then full pipeline verification. Verify supported dependency versions and platform requirements before selecting packages; no dependency version is approved by the scaffold.

Each implemented stage must validate its inputs, define coordinate frames and units at relevant boundaries, document failure behavior, and pass meaningful tests in its owning service. The final pipeline must satisfy the Architecture 01 success condition and demonstrate dependency failure isolation. Do not call the system runnable or the MVP complete before these checks pass.
