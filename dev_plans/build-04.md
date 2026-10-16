# Build 04: Reproducible Human Drawing Evaluation

## Scope
Complete the hand-coded challenge submission, not a new learning project. Personally captured pointer trajectories must drive actual Panda physics. Do not claim a learned policy, egocentric perception, RL, world modelling, multi-robot transfer or inference acceleration. No public deployment, commit or push is authorized.

## Checklist
- [x] Audit current code, rules, CI and saved human evidence.
- [x] Obtain approval to publish the three remaining human captures; exclude the removed demo.
- [x] Package byte-identical approved captures with SHA-256, collection provenance and clear synthetic/physical limitations.
- [x] Add one reproducible, container-based evaluation using existing processing and robot-control modules.
- [x] Freeze three reachable paper poses and compare compensated execution with lead/integral compensation disabled, retaining OSC and path advancement feedback.
- [x] Execute all 18 human capture/method/pose cases serially; retain failures and verify source/skill immutability, measured ink and native video.
- [x] Publish concise measured results and representative native examples; distinguish geometric proximity from physical contact.
- [x] Restore bounded service, full-pipeline and browser CI verification, failure diagnostics and cleanup.
- [x] Run formatting, builds, service tests, complete physics workflows, browser tests and evidence integrity checks.
- [x] Verify the public-data replay path from an isolated clean source snapshot without private runtime data.
- [x] Update README, architecture and development rules; remove stale claims and keep implementation concise.
- [x] Explain personal input, paper-pose reuse and measured simulator output naturally in README and Home, without framing the product around submission requirements.
- [x] Review final diff, data scope, runtime health and Git readiness.

## Experiment Contract
Three independently captured drawings, no training split or learned generalization claim. Each immutable DRAW skill is extracted once and reused at all poses and under both methods. Default paper pose, +15/-10 mm with +0.12 rad yaw, and -15/+10 mm with -0.12 rad yaw are fixed before evaluation. Both methods use the same robot, OSC gains, pen geometry, speeds, feedback-based advancement, contact model and acceptance thresholds. Only lead and integral tracking compensation change. A baseline failure is a result, not permission to loosen limits.

Outputs must record input/skill/code hashes, processing and simulation settings, runtime versions, per-case metrics/errors and artifact hashes. Independent checks link ink to measured tip samples and compare encoded video with native simulator frames. Keep bulky traces and every recording in ignored local exports; publish the small report and representative unmodified native media with the approved captures.

## Evidence
The initial attempt reproduced the mouse capture's compensated result (0.346 mm mean tracking, 0.476 mm maximum shape error) but was stopped during the slower baseline while the evaluator's partial-recording checks were corrected. Its local export is preliminary, not acceptance evidence. The final run fixed BLAS/OpenMP threads at one for both methods and recorded those limits. Historical results in Build 03 are not reruns of this experiment.

The first final comparison pair passed under both methods, taking 58.2 versus 341.8 simulated seconds. Because this matrix is substantially slower than normal regression checks, push/PR CI retains full service/physics/browser coverage and published-evidence integrity checks; manual workflow dispatch additionally runs all 18 human cases. Simulated task duration is not policy-inference latency, and wall timing is machine/load dependent.

Final experiment: all 18 cases completed their evaluation in 100 minutes 24 seconds. Compensated execution passed 9/9; baseline passed 3/9 and six attempts exceeded the unchanged 540-second wall deadline. All failures retain partial traces/video; incomplete stroke geometry is not scored as a completed drawing. Deadline failures are pipeline-budget outcomes on this host, not proof that a pose is geometrically unreachable.

Compensated per-run mean tracking was 0.346-0.351 mm, worst tracking 0.687 mm and worst completed-stroke shape error 0.535 mm. All nine had 100% geometric proximity, but only 34.7-41.7% actual physical contact. Successful baseline cases had 76.7-82.7% physical contact: faster execution is not better force/contact control. The public `evidence/results.json` preserves all outcomes, exact settings, versions, input/skill/code/artifact hashes and recording checks. The 12.2 MB evidence bundle contains only the three approved raw captures, report and byte-identical default-pose native examples. Full traces and other pose recordings remain in ignored exports.

Fresh evidence/preparation and lifecycle verification: 6 passed in 3.39 seconds. Checks reject changed inputs, stale source/report hashes, altered skills/plans, incomplete matrices and mismatched published media. The final full-suite evidence follows.

Clean Git source snapshot: all three images built successfully, with no private recordings in the snapshot. Evidence/lifecycle checks passed 6/6 in 8.26 seconds. Container preparation reproduced all three published skill hashes. An independent public `touch-02` physics replay passed with the same 0.351 mm mean tracking and 0.486 mm shape error; its 701 encoded frames matched native rendering (final-frame mean absolute RGB difference 1.000/255). Original app history was not used as input or modified by this replay. Simulation service regressions passed 21/21 in 87.56 seconds; orchestrator regressions passed 28/28 in 28.36 seconds.

Root verification passed 13 tests with one optional private-replay skip in 1,072.77 seconds: all six fixtures, exact-skill paper reuse, measured ink/native video and dependency recovery. The first browser pass exposed two test-targeting errors: an unscoped History locator matched both navigation and Home, and mobile scrolling put a coordinate gesture beneath the sticky header. Navigation was scoped explicitly, the canvas centered before coordinate gestures and a new-stroke assertion added. No assertion, controller setting or deadline was weakened.

The corrected complete browser rerun passed 3 tests with one intentional duplicate mobile-physics skip in 47.2 seconds. Capture, colors/width/pressure, actual Panda execution, playback, artifact tabs, history deletion, mobile controls and Home provenance all passed. Final service/root/browser suites total 65 passed and 2 intentional skips. Subsequent browser changes affected test targeting only; runtime and benchmark code remain byte-identical to the measured report.

Ruff lint/format, Prettier, TypeScript/Vite, production npm audit (zero vulnerabilities), dependency consistency, Compose and actionlint passed. Only approved captures and representative native outputs are publishable; full exports, app history, private recordings, settings and credentials remain excluded. No runtime dependency, service or learned-policy abstraction was added. Hosted CI remains unverified until an authorized push.

Final evidence/lifecycle recheck: 6 passed in 3.04 seconds. All documentation links resolve, the three raw Git blobs match their original bytes, the active human library still contains exactly three captures and no execution remains active. All three runtime services are healthy. The scoped 30-file change is staged; private/generated-data and credential-pattern checks found nothing publishable outside the approved bundle, and Git whitespace checks passed. No commit or push was performed.

Final presentation pass: README and Home now explain the original handwriting, same-skill paper reuse and actual measured simulator output in ordinary product language. No feature, controller or dependency changed. README also makes long-drawing execution deadlines explicit. An initial browser attempt overlapped an existing active drawing and correctly found New drawing disabled; no user data was changed or execution interrupted. The complete idle rerun passed 3 browser tests with one intentional duplicate mobile-physics skip in 52.1 seconds, including actual Panda execution. Evidence/lifecycle checks passed 6/6 in 3.24 seconds. Production build, web container rebuild, npm audit (zero vulnerabilities), Ruff, Prettier, dependency consistency, Compose, actionlint and whitespace checks passed. Home screenshots at 320, 390, 768 and 1440 px had no horizontal overflow and retained the gallery below the introduction. All services are healthy with no active run. These are follow-up presentation checks, not a new full-suite or 18-case benchmark run. No commit, push or public deployment was performed.

## External Gates
- [ ] Hosted CI after an authorized push.
- [x] Confirm the existing repository is publicly accessible without authentication.
- [ ] Authorized commit/push and application submission before the organizer's deadline.

Physical Surface Pen acceptance and public app deployment are not claimed or required for this simulation submission. They remain separate future work, not checked-off hardware/deployment results.
