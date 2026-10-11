# skill-to-bot Build 01

## Live camera addition

- [x] Add camera selection, live preview, mapping, bounded recording, and Yes/No save confirmation.
- [x] Save confirmed recordings as timestamped MP4s in `data/live_demos` before starting the existing pipeline.
- [x] Handle denied permissions, unavailable camera/recorder, discarded clips, interrupted capture, and failed save/run without losing saved input.
- [x] Extend Docker mounts, ignored runtime data, existing docs, and CI coverage without adding a service.
- [x] Verify synthetic-camera capture/discard/save, persisted video, real perception/Panda pipeline, regressions, and desktop/mobile layout.
- [x] Leave the stack healthy, artifacts excluded, and source ready for an explicit Git commit.

## Polish and push readiness

- [x] Review all source, documentation, dependencies, and repository contents for unnecessary complexity.
- [x] Replace mapping checkbox with yellow Confirm Mapping action, then Run Demo; invalidate confirmation when inputs change.
- [x] Show live run phases and readable Logs, Skill, and Observations tabs without downloads.
- [x] Simplify frontend structure and remove overlapping component-test tooling; retain safety regressions and prioritize full pipeline tests.
- [x] Add reproducible GitHub build and end-to-end verification with failure diagnostics.
- [x] Update authoritative docs, run checks and real desktop/mobile workflows, inspect screenshots and Git contents.
- [x] Leave the local stack healthy and the repository ready for an explicit commit/push.

## Scope and checklist rules

Build the deterministic Architecture 01 MVP: one personally collected human manipulation video becomes a compact skill representation and drives a simulated Panda through pick, move, place, and release, with both videos and a measured result visible in the browser.

Requirements come from [Architecture 01](../docs/architecture/architecture-01.md) and [Development Rules](../docs/architecture/development-rules.md). [Architecture Final](../docs/architecture/architecture-final.md) supplies future direction only. This checklist tracks implementation and evidence; it does not authorize new scope. Read those documents and both documentation indexes before building.

Use `skill-to-bot` for the project and Compose project, `@skill-to-bot/web` for the web package, and the canonical module names already present in the scaffold. Keep exactly four runtime containers: `perception`, `simulation`, `orchestrator`, and `web`.

Check an item only after its behavior or evidence has been verified. An existing placeholder does not count as implementation. Record material decisions in the existing architecture documents and brief verification results in this file. Complete each stage's checks before wiring dependent stages. Implementation is now authorized; this checklist is updated alongside the build.

## Final review and transport decision

- [x] Review the architecture and existing scaffold before implementation; preserve personally collected videos in `data/demonstrations/`.
- [x] Select HTTP REST/JSON for all inter-service operations and browser commands, with orchestrator-to-browser WebSockets for status snapshots.
- [x] Serve video artifacts over HTTP and keep robot control/physics stepping inside simulation; do not add Kafka, ZeroMQ, or an external queue.
- [x] Finalize documented interfaces, calibration requirements, and honest failure behavior before service integration.
- [x] Remove obsolete scaffold-only statements as verified implementations replace them.
- [x] Complete final code, documentation, configuration, and generated-artifact review after integration tests.

## 0. Repository and machine preflight

- [x] Read the existing architecture, roadmap, development contract, and repository indexes.
- [x] Confirm the project directory, repository name, and documented naming are `skill-to-bot`.
- [x] Reserve all Architecture 01 root, service, application, contract, test, and data paths.
- [x] Verify source, tests, Dockerfiles, Compose, and lifecycle placeholders were explicitly marked unimplemented before building.
- [x] Verify the initial skill schema rejected all payloads until its versioned contract was designed.
- [x] Provide root and four service `.env.example` files and initially matching ignored local `.env` files; preserve local overrides as examples evolve.
- [x] Ignore credentials, generated runs, dependencies, caches, and build output while retaining demonstration and fixture directories.
- [x] Configure `origin` as `git@github.com:emranB/skill-to-bot.git` and verify repository access over SSH.
- [x] Confirm Git Bash is available for the planned `.sh` lifecycle commands.
- [x] Confirm Docker CLI and Compose are installed.
- [x] Confirm Node, npm, and Python are available; treat host versions as observations, not approved dependency versions.
- [x] Confirm the Docker daemon is available and targets Linux containers.
- [x] Prove a minimal Linux container can execute before beginning container integration.
- [x] Recheck required paths, JSON, Markdown links, environment pairs, and Git exclusions after this plan is linked into the docs.

Preflight observations on 2026-10-11: SSH repository access succeeded. Git Bash 5.2.12, Docker CLI 24.0.6, Compose 2.23.0, Node 26.10.0, npm 11.19.1, and Python 3.11.0 are installed. The initial Docker daemon check failed because it was stopped; Docker Desktop was then launched, reported a Linux engine, and passed `docker run --rm hello-world`. WSL's default distribution is `docker-desktop-data`, and the Windows `bash` launcher failed. Use the verified Git Bash executable at `C:/Program Files/Git/bin/bash.exe`; do not rely on the current WSL default or change it as part of this planning task.

## 1. Dependency and build foundation

- [x] Verify supported Python, Node, LIBERO, robosuite, MuJoCo, React, TypeScript, and Vite versions using primary documentation before choosing packages.
- [x] Prove compatible simulation dependencies, Panda scene initialization, and offscreen rendering together in a Linux container; resolve this feasibility gate before building the full pipeline.
- [x] Confirm required upstream assets, licenses, model downloads, and rendering libraries; document reproducible acquisition without committing downloaded caches.
- [x] Select the minimal backend interface framework, video processing dependencies, JSON Schema validator, test runners, and formatting/lint tools needed by the MVP.
- [x] Record chosen versions and platform constraints in the existing architecture documents; add service dependency manifests and lockfiles during implementation.
- [x] Set reproducible Python service builds and web install/build/typecheck commands; make module imports and test discovery work without cross-service source imports.
- [x] Configure the documented formatting conventions and shell LF line endings; retain purpose headers and executable script permissions where required.
- [x] Replace empty behavior configuration objects with documented validated defaults; keep deployment values in environment files and preserve local overrides.
- [x] Verify each service can install its own dependencies and run its isolated test command without the complete stack.

## 2. Skill contract and deterministic inputs

- [x] Define a versioned skill JSON Schema with object/goal references, start and goal poses, approach, grasp, transport, place, release, and calibration metadata.
- [x] Specify coordinate frames, physical units, pose/orientation representation, timestamps, event ordering, uncertainty, and required versus optional fields.
- [x] Specify how demonstrator coordinates are calibrated into robot workspace coordinates; reject unsupported or missing calibration rather than guessing physical depth.
- [x] Replace the scaffold schema with the approved contract and validate it in both perception and simulation boundaries.
- [x] Add small deterministic valid and invalid skill fixtures plus a minimal representative video fixture with known expected events.
- [x] Define measurable MVP placement, grasp, release, completion, and timeout criteria in Architecture 01 and non-secret configuration.
- [x] Test malformed schemas/payloads, unknown versions, invalid poses, missing targets, unsafe workspace targets, and out-of-order manipulation events.

## 3. Simulation service

- [x] Implement `simulation_environment` initialization, Panda/scene/object ownership, reset, fixed-step physics, deterministic fixture setup, and resource shutdown.
- [x] Implement offscreen camera rendering and simulation video artifacts with validated dimensions, FPS, timestep, and output paths.
- [x] Implement `skill_to_robot` conversion from the approved skill representation to reachable end-effector and gripper targets.
- [x] Implement `robot_control` approach, grasp, transport, place, and release execution using the simulation's controller and physics state.
- [x] Keep stepping and control inside simulation; enforce bounded execution, workspace limits, and useful controller failure reporting.
- [x] Determine success from physics state and configured tolerances, including object placement and gripper release; do not report success solely because commands were sent.
- [x] Define simulation execute, reset, status, and artifact interfaces without introducing additional shared schema files or runtime services.
- [x] Implement consistent `/health`, `/ready`, and `/version` behavior, including initialization/rendering failures.
- [x] Complete `test_simulation_environment.py`, `test_skill_to_robot.py`, and `test_robot_control.py` for reset, conversion, execution, failure, and rendering behavior.
- [x] Run a validated deterministic skill fixture through pick, move, place, and release and inspect the resulting nonblank video and physical outcome.

## 4. Perception service

- [x] Implement `video_input` for uploaded or selected demonstrations, format validation, bounded file size/duration, metadata, and deterministic frame sampling.
- [x] Handle empty, corrupt, unsupported, and unreadable videos with actionable errors.
- [x] Implement `object_tracking` for the controlled MVP scene, stable target identity, confidence, occlusion handling, and calibrated motion observations.
- [x] Implement `skill_extraction` to derive manipulation intent and the required events from observations, not a hardcoded result disconnected from the video.
- [x] Emit the versioned skill contract with traceable calibration and confidence metadata; reject insufficient evidence with a clear failure.
- [x] Define process/status/artifact interfaces and implement `/health`, `/ready`, and `/version` consistently with simulation.
- [x] Complete `test_video_input.py`, `test_object_tracking.py`, and `test_skill_extraction.py` using deterministic video/observation fixtures and invalid-input cases.
- [x] Process a representative video and validate its skill output against the schema and known event expectations.

## 5. Orchestrator service

- [x] Specify and document API requests/responses, artifact transfer, run IDs, statuses, errors, and status streaming behavior in Architecture 01 before connecting services.
- [x] Implement `api` for demonstration selection/upload, starting runs, retrieving status/results/artifacts, and simulation reset.
- [x] Implement `workflow` coordination from video input through perception, schema validation, simulation execution, and result reporting.
- [x] Define bounded run concurrency and reset behavior while a run is active; prevent duplicate execution and artifact collisions.
- [x] Define queued/running/completed/failed or equivalent explicit states and preserve useful errors across the complete run lifecycle.
- [x] Add bounded request timeouts/retries and report unavailable dependencies without crashing the orchestrator or unrelated services.
- [x] Define process health versus dependency readiness and expose consistent `/health`, `/ready`, and `/version` responses.
- [x] Keep service-health checks, run coordination, clients, and streaming inside the existing API/Workflow boundaries for the MVP.
- [x] Use per-run generated artifact paths under `data/runs/`; prevent path traversal and ensure safe upload/storage/serving behavior.
- [x] Add structured logs with run IDs and useful failure context without logging secrets or every frame/step.
- [x] Complete `test_api.py` and `test_workflow.py` for normal runs, input rejection, timeout, reset/concurrency, artifact access, and unavailable dependencies.

## 6. Web application

- [x] Initialize the existing `@skill-to-bot/web` package with React, TypeScript, and Vite; implement only Architecture 01 UI responsibilities.
- [x] Implement demonstration selection/upload, run and reset actions, human video, simulation output, run status, and measured success/failure.
- [x] Connect web only to orchestrator application interfaces; keep physics and robot control in simulation.
- [x] Implement loading, validation, disabled-action, empty-result, failed-run, disconnected, and unavailable-service states.
- [x] Apply the development contract's semantic CSS colors, typography, spacing, controls, focus states, and restrained light presentation.
- [x] Use semantic HTML, labelled controls, keyboard/touch access, meaningful media alternatives, and status indicators that do not rely on color alone.
- [x] Verify video/control layout on desktop and mobile, including long errors, stable media dimensions, no overlapping text, and stacked views on small screens.
- [x] Verify select, mapping confirmation, start/reset, status/results, and readable failures through browser workflows; run typecheck and production build. Upload input boundaries and dependency failure isolation are covered by backend/pipeline checks.
- [x] Verify the actual browser workflow and screenshots at desktop/mobile sizes; check media loading and visible simulation content.

## 7. Containers, environment, and lifecycle

- [x] Implement four Dockerfiles with reproducible installs, explicit startup, required runtime assets, and health checks where applicable.
- [x] Replace placeholder Compose with project `skill-to-bot`, the four canonical service names, explicit networking/ports, and documented volumes.
- [x] Distinguish container DNS names from browser `localhost` URLs; finalize host/port/environment examples and preserve local overrides.
- [x] Verify web-to-orchestrator browser connectivity, service-to-service connectivity, and narrowly configured development CORS where needed.
- [x] Keep demonstrations persistent, generated runs isolated, and fixtures reproducible; define artifact retention without silently deleting source data.
- [x] Implement root and four service `build-and-run.sh`, `run.sh`, `stop.sh`, and `clean.sh` using strict Bash and nonzero failure exits.
- [x] Make clean builds stop/remove only the intended runtime, rebuild, start, wait with bounded health checks, and report startup failures clearly.
- [x] Ensure service lifecycle operations do not stop unrelated services and root operations affect only this Compose project.
- [x] Verify run, stop, restart, clean-start, startup timeout, and failure paths through Git Bash on this Windows machine.
- [x] Confirm offscreen rendering works through the complete container path and output artifacts are accessible in the browser.

## 8. Full pipeline and acceptance

- [x] Implement `tests/test_pipeline.py` for video-to-skill-to-Panda execution, artifacts, measured success/failure, reset, and repeated runs.
- [x] Implement `tests/test_service_health.py` for perception/simulation unavailability, recovery of availability, and absence of cascading service failures.
- [x] Verify perception can remain available when simulation is unavailable, and web/orchestrator remain usable when either dependency fails.
- [x] Capture or select one personally collected human pick/move/place/release video with the calibration and controlled-scene assumptions recorded.
- [x] Run that video through the complete pipeline and inspect both videos, extracted skill, simulation physics outcome, status history, and error-free completion.
- [x] Demonstrate a failed/unsupported video and a failed simulated manipulation produce honest failure states rather than false success.
- [x] Run the relevant service, integration, browser, format/lint, typecheck, and build checks; record commands, results, and any limitations here.
- [x] Reproduce a clean start using the committed examples/dependency locks and documented lifecycle commands.
- [x] Update existing docs from scaffold status to verified implementation status; remove unimplemented markers only where behavior is actually complete.
- [x] Inspect the final Git changes for naming drift, accidental secrets, generated artifacts, unintended dependencies, and roadmap-only scope.
- [x] Record remaining limitations, the reproducible local URL/start commands, and acceptance evidence; call the MVP complete only when Architecture 01's success condition passes.

## Verification record

Initial preflight verified on 2026-10-11:

- `git ls-remote origin` succeeded through the SSH remote. The remote currently returns no refs.
- `docker info --format '{{.OSType}} {{.ServerVersion}}'` reported `linux 24.0.6`.
- `docker run --rm hello-world` pulled its image, executed successfully, and removed the test container.
- A complete Architecture 01 path inventory passed, including all canonical modules, matching test files, lifecycle files, config/environment files, and fixture/data directories.
- All JSON files parsed; the placeholder skill schema remained `false`.
- All Markdown links resolved, including links to this checklist, and both architecture trees include `dev_plans/build-01.md`.
- All five local/example environment pairs matched. Git excluded local environment files, run/export data, dependency output, and virtual environments, while retaining environment examples and source fixture/demonstration markers.
- Source, test, Dockerfile, Compose, and lifecycle placeholders retained their explicit unimplemented markers. No stale project name or obsolete blanket prohibition on the requested plan was found.

The initial preflight established repository and machine readiness. Stage 1 subsequently proved the LIBERO/robosuite/MuJoCo stack, followed by the real pipeline and outage tests recorded below. Preflight evidence alone was not used to claim application success.

Build 01 acceptance passed on 2026-10-11. The supplied `pop-can-pick-up-1.mp4` produced 329 tracked samples and a mapped sideways goal of approximately 0.167 m. Run `a0a03a750c8a4e71ab7ba486b38ee8d1` completed with 2.2 mm placement error, verified grasp/lift/release, and a rendered simulation video. Repeated browser-triggered runs also completed after the final UI changes. No object position was teleported during controller execution.

Initial implementation verification evidence (before the polish pass):

- Perception: `python -m pytest services/perception/tests -q` passed 10 tests; the isolated Linux service tests also passed.
- Orchestrator: `python -m pytest services/orchestrator/tests -q` and container tests passed 8 tests, covering inputs, upload corruption, failure isolation, concurrency/idempotency, persistence, and WebSocket snapshots.
- Simulation: isolated Linux execution of `python -m pytest tests -q` with the service/contract/fixture mounts passed 11 tests, including actual rendering, reset, physical transfer, input boundaries, and invalid configuration. The dependency-resolution check container was removed afterward.
- Root lifecycle: `python -m pytest tests/test_lifecycle.py -q` passed 4 tests. Project scope, bounded health waits, and nonzero startup failure propagation were verified, alongside two successful actual root clean builds.
- Integration: `RUN_INTEGRATION=1 python -m pytest tests/test_pipeline.py tests/test_service_health.py -q` passed the complete video pipeline, invalid video/selection, and both outage/recovery cases. The additional low-clearance physical manipulation test passed by correctly reporting failure. Five integration cases are covered.
- Web component tests: `npm test` passed 5 tests, including upload, start/reset, unavailable simulation, and correct video/result pairing.
- Browser: the final desktop real-run test passed; four desktop/mobile media, playback, layout, and long-error checks passed. JPEG and decoded video pixel checks were nonblank, playback advanced, and screenshots were visually inspected. The mobile duplicate full-run case is intentionally skipped; the mobile workflow remains available.
- `npm run build`, `npm run typecheck`, `npm run format:check`, Ruff lint/format checks, Bash syntax checks, and Compose validation passed. `npm audit --audit-level=moderate` reported zero vulnerabilities.
- All seven authoritative documents and their links, required runtime paths, and JSON files validated. Local environments, dependencies, build output, test output, and generated runs remain ignored. Both supplied original videos retained their original sizes and modification times.
- All four runtime containers are healthy. The application remains running at [localhost:5173](http://localhost:5173); start with `bash build-and-run.sh` and manage it with the other documented lifecycle commands.

Remaining scope limits: fixed front-plane videos, operator-selected textured can and workspace span, motion-estimated human grasp/release events, one active run, and process-local simulation job tracking. Depth reconstruction, general object recognition, learning, and final-roadmap capabilities are not implemented. Generated artifacts are retained until deliberately removed. Restarted or disconnected executions can have unknown outcomes and must be inspected/reset before reuse. These limits do not block the verified Architecture 01 controlled-scene acceptance condition.

At the initial build handoff, the project files were uncommitted and there was no commit history. The developer subsequently committed the baseline as `5a8c960` (First pass). Later additions remain uncommitted until explicitly requested. SSH authentication and repository read access were verified; push permissions have not been tested by these build passes.

## Polish verification

Completed on 2026-10-11:

- Split run presentation into `RunStatus.tsx`; replaced nested rendering branches with short, explicit detail paths. Kept canonical backend modules and required lifecycle wrappers.
- Replaced the checkbox with yellow Confirm Mapping and an exclamation icon, followed by Run Demo. Input edits clear confirmation; out-of-frame rectangles cannot be confirmed. Demo labels now come from filenames, not changing list positions; uploads have readable labels.
- Added actual processing/controller phases, completed-step indicators, persisted timestamped run logs, and inline Skill/Observations tabs. All 329 observation rows, including rectangles, are accessible without downloading. Historical runs without logs remain labelled as such.
- Removed overlapping React component tests and Vitest, jsdom, and Testing Library dependencies. Playwright is the only web test runner. The web install now audits 29 packages with zero reported vulnerabilities. Small backend safety/contract regressions remain intentionally.
- `RUN_INTEGRATION=1 python -m pytest tests -q` passed all 9 root cases in 160 seconds, including the complete supplied-video pipeline, failed physical lift, invalid input, lifecycle, and both outages/recoveries.
- Orchestrator regressions passed all 8 cases, including new log persistence and restart assertions.
- Final `npm test` passed 5 browser cases in 36.5 seconds. Only the duplicate mobile physical execution is skipped; desktop/mobile layout, media pixels/playback, mapping invalidation, invalid rectangle, observations, and long errors are verified. The desktop case executes the real pipeline and checks logs, skill, all tracked rows, result video, and reset.
- Final browser run `e22bb97c409f4d0f97465100ae938c41` completed with 2.2 mm placement error and 12 recorded log entries. Desktop/mobile screenshots, yellow confirmation state, and the mobile observations panel were visually inspected.
- All four production images built. Final web TypeScript/production build, Prettier, Ruff lint/format, Bash syntax, Compose configuration, document links, and repository input/ignore checks passed. Docker build contexts exclude test traces, caches, generated fixtures, and runtime output.
- `.github/workflows/build.yml` builds the runtime and runs root/browser end-to-end checks with pinned actions, read-only permissions, time limits, and failure diagnostics. Equivalent commands passed locally; hosted verification of these later changes requires committing and pushing them.
- Git dry-run includes only intended source/docs/configuration and named demonstrations/fixture. Generated UUID uploads, local environments, dependencies, build output, traces, and run data are excluded. Original videos are unchanged, and SSH remote read access still works.

The stack remains healthy at [localhost:5173](http://localhost:5173). The repository is ready for an explicit commit/push; no staging, commit, push, external deployment, or publication was performed.

## Live camera verification

Completed on 2026-10-11:

- Camera selection populates Human demonstration. Mapping confirmation precedes capture; recording and review lock source/mapping changes. Stop opens a native Yes/No dialog. No restores live preview and idle controls without uploading. Yes saves first and then submits the normal run request.
- Camera capture is video-only, limited to 59 seconds and 100 MB, with supported WebM/MP4 negotiation. Leaving the view stops tracks and releases timers/blob URLs. Permission denial, unsupported recording, disconnect/reconnect, discard, and save errors are handled. Reconnecting clears mapping confirmation.
- Confirmed files are normalized using pinned imageio-ffmpeg 0.6.0 into seekable MP4s in `data/live_demos`, with UTC-prefixed unique names. Temporary conversion files are removed on success/failure; only complete validated files enter the library. Saved input survives a failed pipeline. Perception has read-only access, and cleanup preserves captured input.
- Browser camera tests inject deterministic motion using the supplied can texture. They use the actual browser MediaRecorder and the real save/conversion, perception, and simulation services. No physical camera or microphone was accessed. Earlier replay-based recordings were correctly rejected for unreliable tracking and retained as saved inputs; production tracking tolerances were not relaxed.
- Camera acceptance run `64139c15dce64775aa4a2226a404ce36` used `live_demo_20261011T195948460489Z_47c2c613.mp4`, produced 177 tracked frames, and completed with 2.17 mm placement error and verified lift/release. Recorded simulation playback advanced, and desktop/mobile capture/prompt/result screenshots were inspected.
- The full browser suite passed 10 cases, with only the duplicate mobile physics executions skipped. Final focused checks also passed for unsupported recording/permission handling on both viewports and camera-to-physics execution/playback.
- `RUN_INTEGRATION=1 python -m pytest tests -q` passed all 9 root cases in 76.7 seconds when run serially after builds. The supplied human-video pipeline still completed with 2.2 mm error. An earlier build-overlapped run timed out; simulation timeouts now explicitly report unknown execution outcomes instead of a bare exception name. No robot command retries were added.
- Perception regressions passed 10 cases. Orchestrator regressions passed 9 cases in Linux, including invalid/corrupt camera input cleanup and perception-versus-simulation timeout semantics. The temporary test container exited and was removed.
- Updated images built successfully; final web TypeScript/production build, Prettier, Ruff lint/format, Compose validation, dependency consistency, document links, and Git whitespace/ignore checks passed. Web dependency audit reported zero vulnerabilities. The GitHub workflow now includes synthetic-camera tests through the same web test command.
- All four local services are healthy. Generated recordings, run data, and test output remain ignored; only `data/live_demos/.gitkeep` is a new tracked-directory candidate. Original demonstration videos are unchanged. Changes are uncommitted and unstaged; no push or external publication was performed.

Physical camera permissions, browser/device support, and real-scene framing remain operator checks. Live capture does not remove the controlled front-plane mapping and tracking assumptions.

## Build and Git readiness

Reverified on 2026-10-11 after the live-camera addition:

- [x] Review the seven existing documents and resolve their local links. Correct stale commit/hosted-verification wording and keep the active architecture unchanged.
- [x] Keep project text and Git-facing names/messages change-focused, without tool attribution. Existing branch `main`, commit `5a8c960` (First pass), and SSH remote retain ordinary project naming.
- [x] Run `npm ci --prefix apps/web`: clean installation succeeded, with 29 packages audited and zero reported vulnerabilities.
- [x] Run Ruff lint/format, web formatting, TypeScript/production build, Bash syntax checks, and Compose configuration validation. All passed.
- [x] Run `bash build-and-run.sh` through Git Bash. All four production images built and all four recreated services became healthy.
- [x] Run `RUN_INTEGRATION=1 python -m pytest tests -q`: 9 passed in 92.96 seconds, including real execution, failed manipulation, lifecycle, and dependency recovery.
- [x] Run `npm test --prefix apps/web`: 10 passed in 1.3 minutes. Two duplicate mobile physics cases remain intentionally skipped; desktop physics and mobile capture/layout/error paths passed.
- [x] Verify SSH read access: `git ls-remote origin` returned the existing baseline on remote `main`. This read-only check does not prove push authorization.
- [x] Inspect the Git add dry-run, ignore rules, and whitespace. Only intended source/docs/configuration and the live-demo directory marker are included; local environments, recordings, run artifacts, build output, and test traces remain excluded.

These are local equivalents of the workflow's source/build/runtime/end-to-end checks, not a hosted Actions result. Hosted runner setup, artifact upload, and these uncommitted changes still require verification after an authorized commit and push. Physical camera behavior remains an operator check. No staging, commit, push, history rewrite, or external deployment was performed. The local stack remains available at [localhost:5173](http://localhost:5173).
