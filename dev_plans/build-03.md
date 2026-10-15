# Build 03: One-Shot Drawing Skill Retargeting

The tracked video pick-and-place archive is no longer in this repository. Active code is `src/frontend`, `src/backend`, and `src/scripts`. Checked items below record the drawing implementation; they are not a request to restore the removed archive.

## Implementation
- [x] Preserve historical video source under `deprecated/video-pick-place/`.
- [x] Preserve ignored recordings/results under `data/deprecated/video-pick-place/`; verify all 1,456 original files by SHA-256.
- [x] Keep robosuite 1.4.1 and MuJoCo 2.3.7 with three REST/JSON services.
- [x] Strict immutable raw input and separate, robot-independent DRAW skill.
- [x] Bounded stroke processing retaining order, geometry, timing, style and provided pressure.
- [x] Reachable paper transforms, rigid pen compensation and disconnected motion phases.
- [x] Measured contact-gated ink, independent robot trace and native simulator recording.
- [x] Fine-path feedback, bidirectional shape acceptance and sufficient native render capacity.
- [x] Home, shared library rows, light responsive workspace and execution progress.
- [x] Color, brush width, optional pen/touch pressure and constant mouse fallback.
- [x] Native playback at 1x, 2x, 5x and 10x; Logs, Raw Input, Skill and Trace tabs.
- [x] Confirm history removal, retain source/evidence, reject active runs and preserve request deduplication.
- [x] Compact polling, independent video/preview availability and on-demand geometry.
- [x] Shared lifecycle preserving local settings/data, production web headers and bounded CI diagnostics.

## Product Presentation Polish
- [x] Add concise product copy, a clear drawing action and a read-only recording shortcut.
- [x] Refine navigation, typography, spacing, native previews, focus/hover states and reduced-motion behavior without new dependencies.
- [x] Verify mobile/desktop layout, interaction, real execution, build checks and final Git state.

Final presentation verification: browser 3 passed, 1 intentional duplicate mobile-physics skip in 45.0 s. Coverage includes the recording shortcut, honest empty states, reduced motion, single page headings and the existing capture-to-Panda workflow. Twenty cross-view checks at 320/390/768/1,440/1,920 px found no horizontal overflow or clipped controls; keyboard focus, stable hover geometry and native previews passed. Final Home captures keep the next section's imagery in the first viewport at every checked size. Entrance motion leaves initial content readable. Build/type/format checks, actionlint, Compose and the production dependency audit passed without adding a dependency or changing physics. The rebuilt web container is healthy.

No public deployment is performed in this pass. An authenticated TLS gateway and configured hosting target are still required before exposing demonstrations, execution and history controls online.

## Human Home and Release Cleanup
- [x] Show completed human handwriting on Home, once per demo, without hardcoded IDs or fixture fallbacks.
- [x] Reuse list loading/empty states; remove duplicated drawing state, polling wrappers and unused presentation code.
- [x] Review active source headers/comments; keep annotations purposeful and preserve physics safeguards.
- [x] Share lifecycle teardown and add unused-code/dependency checks with bounded CI stages and cleanup headroom.
- [x] Verify fresh builds, affected workflows, human previews, browser edge cases and Git readiness.

Remote deployment is deferred by request. No target, credentials or publishing step is added.

Human Home cleanup checkpoint: browser 3 passed, 1 intentional duplicate mobile-physics skip in 54.3 s; lifecycle/outage 5 passed in 20.91 s. Browser coverage includes mixed-provenance Home selection, duplicate exclusion, failed/missing-preview exclusion, an empty human library, actual mouse/stylus capture-to-Panda execution, playback, artifact tabs and history deletion. Four additional 320/390/768/1,440 px checks opened the actual human runs and verified independent raw input, native previews, no overflow and no page errors.

Fresh container startup, TypeScript/Vite, unused-code checks, Ruff, Prettier, actionlint, Compose, dependency consistency and production npm audit passed. Active source purpose headers were audited; comments explain provenance, timing and safety rather than narrating syntax. Reused loading states, a single drawing-state owner/polling loop, one lifecycle teardown and removal of unused styling keep this pass scoped. No robot control, processing threshold, contract or dependency was changed; full six-fixture/service results below remain the preceding pass's evidence, not a claimed rerun.

## Drawing-Only Cleanup
- [x] Remove still-image import controls, endpoints, source contracts and processing module.
- [x] Remove raster-specific robot paths, texture rendering, metrics, settings and unused runtime dependency.
- [x] Retain six writing/line fixtures and general drawing color, width and pressure.
- [x] Remove discontinued examples and associated outputs from the active library/history; preserve original bytes outside active data mounts.
- [x] Update the existing authoritative docs and workflow scope.
- [x] Rebuild the stack and verify service, full-physics and desktop/mobile workflows.
- [x] Confirm active data, formatting, build checks and Git diff.

## Evidence
Cleanup moved 21 discontinued demonstrations, 11 associated run directories and 21 obsolete UI screenshots out of active data mounts into ignored `data/deprecated/still-images/`. All 161 moved files matched their original SHA-256 values; the four human captures remained unchanged. Active source, contracts, fixtures and current docs contain no discontinued processing references. The six remaining generated fixtures reproduce their prior JSON content unchanged.

Fresh three-service container build/startup passed. Orchestrator regressions: 27 passed in 29.49 s. Simulation regressions: 19 passed in 147.15 s. Ruff check/format, Prettier, TypeScript/Vite, Compose validation, actionlint, both runtime dependency checks and production npm audit passed. All retained raw demonstrations validate against the narrowed contract.

The initial cross-service pass overlapped service-level physics and encountered a read timeout followed by busy responses; it is not acceptance evidence. Separate service physics finished before the serial full-workflow rerun. No numerical limits or communication deadlines were loosened and no uncertain robot command was retried automatically.

Serial root verification: 11 passed, 1 optional personal-replay skip in 1,035.86 s. All six fixtures, exact-skill shifted-paper reuse, independent trace/native-video agreement, lifecycle and outage/recovery passed. Mean tracking stayed within 0.316-0.352 mm, maximum tracking below 0.755 mm and maximum shape error below 0.575 mm, with 100% bounded paper proximity. Eight additional layout checks across all four views at 390/1,440 px found no overflow, page errors or upload controls. Native previews and retained drawing tools were visually reviewed.

Final browser verification against the rebuilt web container: 3 passed, 1 intentional duplicate mobile-physics skip in 41.8 s. Capture, Undo/Clear, retained colors/width/pressure, immutable persistence, actual Panda execution, playback rates, artifact tabs and confirmed history removal passed. Combined final suites: 60 passed, 2 intentional skips. The live API exposes no still-image import routes. At that checkpoint four human captures appeared in the saved library; the fourth was removed afterward (see below). All three services are healthy, active execution is finished, intended changes are staged and Git whitespace checks pass. No commit or push was performed.

Before this cleanup, the six retained fixtures and exact-skill shifted star passed full Panda physics. The retained personal mouse capture (`2fb0a84d02e743efba4ced091537732c`) passed the tightened contract: mean tracking 0.346 mm and shape error 0.476 mm. Its later native-camera replay is `50c158c75aac452cac4b3519ead1ae06`. This recording establishes simulated drawing, not physical stylus acceptance.

The subsequently removed fourth human demo and its three associated runs are no longer in active data mounts. Obsolete UI screenshots were also removed from active output; original bytes remain in the ignored local archive. SHA-256 checks confirmed all 50 archived files and all 59 other demonstrations unchanged. The current human library contains three captures; earlier four-capture counts above describe historical checkpoints.

Default acceptance remains 1 mm mean tracking, 2 mm maximum tracking, 0.8 mm maximum bidirectional shape error and at least 95% geometric paper proximity. Physical contact is reported separately. Input waypoints are never used as output ink or substituted for native camera frames.

History deletion persists `deleted_at`, omits the record from lists and retains direct evidence access, reusable skills and request-ID deduplication. It is not disk cleanup. Native preview availability is checked independently of video availability; older videos without PNGs retain a placeholder.

Production nginx 1.30.6 serves same-origin content with security headers, hashed-asset caching and application-document revalidation. Docker contexts exclude all runtime data and local overrides. CI checks source/dependencies, builds three services, runs service/physics/browser tests, captures failures and cleans up project containers.

## Remaining Gates
- [ ] Physical Surface Pen pressure capture and operator acceptance.
- [ ] Hosted CI execution after an authorized push.
- [ ] Authenticated TLS gateway and configured target before internet-facing deployment (deferred by request).

No commit or push is authorized by this cleanup. Historical archive documents remain unchanged and do not override the active contract.
