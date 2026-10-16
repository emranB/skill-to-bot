# Drawing Architecture

The active `skill-to-bot` Tier 1 transfers one human drawing demonstration to a simulated Panda. Three services communicate through REST/JSON: web, orchestrator and simulation. No perception service, recognition, broker or database is required.

## Data Flow
Pointer Events -> Drawing Canvas -> immutable raw demonstration JSON -> API -> Stroke Processing -> normalized DRAW skill -> Workflow -> Skill To Robot -> Robot Control -> Drawing Environment -> actual pen-tip trace, progressive ink, metrics and MP4.

Raw demonstrations, skills and measured robot traces are independent artifacts. Raw input uses normalized screen X-right/Y-down, milliseconds and explicit stroke boundaries. Skill uses paper-normalized X-right/Y-up, seconds, source aspect ratio, stroke style and optional non-mouse pressure. It contains no robot/world pose. Skill To Robot fits the drawing uniformly inside paper margins, preserving aspect, then applies paper translation/yaw and compensates the rigid pen offset.

## Ownership
- `src/frontend/src/App.tsx`: Home selection, navigation, one bounded polling loop and shared drawing-session state.
- `src/frontend/src/Library.tsx`: shared run/demo presentation, loading/empty states and confirmed history deletion.
- `src/frontend/src/Reproduction.tsx`: native simulator playback and paper-retargeting controls.
- `src/frontend/src/RunStatus.tsx`: execution stages, readable phases, metrics and on-demand artifact inspection.
- `src/frontend/src/api.ts`: shared same-origin JSON requests and boundary error handling.
- `src/frontend/src/DrawingCanvas.tsx`: pen/touch/mouse capture, coalesced samples and preview.
- `src/backend/orchestrator/src/api/api.py`: validated input, immutable persistence, library, runs and artifact access.
- `src/backend/orchestrator/src/stroke_processing/stroke_processing.py`: deterministic geometry/timing/pressure processing.
- `src/backend/orchestrator/src/workflow/workflow.py`: serialized jobs, persistence, bounded polling and restart failure handling.
- `src/backend/simulation/src/drawing_environment/drawing_environment.py`: robosuite Panda, fixed paper, rigid pen, tip/contact state, bounded measured ink and offscreen rendering; simulation API.
- `src/backend/simulation/src/skill_to_robot/skill_to_robot.py`: strict skill validation, paper transforms and motion phases.
- `src/backend/simulation/src/robot_control/robot_control.py`: absolute OSC goals, continuous speed-bounded strokes, actual trace and evaluation.

## Execution Contract
Stroke color is RGB hex; brush size is full width normalized to canvas height. Both are captured at stroke start and retained unchanged in the skill. Legacy captures without style remain readable using configured defaults. Mouse pressure is omitted; unavailable input uses explicitly labeled constant 0.5 pressure. Provided pen/touch values are retained even when constant; variation metadata does not imply calibrated force. Pen release zeros stay raw but the processed endpoint retains its last drawing pressure. Ink marks record color, radius, effective pressure and input/fallback provenance. Flat visual ink joins consecutive measured contact positions, never separate strokes or contact gaps. The renderer capacity is derived from scene geometry; overflow fails rather than silently dropping later ink.

Fine paths use tighter simplification and Cartesian spacing with bounded lag compensation and tip feedback: advancement pauses if horizontal tracking exceeds tolerance. Acceptance also checks both directions of per-stroke point-to-polyline shape distance, preventing missing loops from passing on average tracking error alone. Default limits are 1 mm mean tracking, 2 mm maximum tracking and 0.8 mm maximum shape error, with at least 95% bounded geometric contact coverage. This is numerical path acceptance, not handwriting recognition or a claim of perfect reproduction.

The robosuite scene's per-step reward and success hooks are unused by this hand-coded controller. Final task acceptance comes from Robot Control's measured execution metrics; those hooks do not imply an unfinished learned-policy evaluation.

MP4 frames are actual MuJoCo camera renders sampled during physics execution. `trace.json` records frame simulation time/sample/ink counts, and `simulator-final.png` stores the final render independently for encoded-video comparison. The robot parks clear of the close-up camera; final segmentation verifies the visible paper region and ink before success. Playback speed affects only the browser player. This MVP records the simulator feed; it does not expose a live video stream. Compact history summaries avoid repeatedly sending every saved skill during UI polling; selected run details remain inspectable.

Approach, descend, draw, lift and transit preserve disconnected strokes. Pressure changes ink radius, not physical force or tilt. Ink is deposited only at measured pen positions during draw and bounded paper contact; never from desired waypoints. Small geometric contact tolerance is documented alongside actual MuJoCo contact. A partial drawing fails quantitative acceptance. Paper pose is a robot-run parameter, not part of the skill; a modest second pose exercises retargeting.

Only one execution is active. Request IDs are idempotent and reject conflicting reuse. Communication uncertainty/restart never triggers automatic robot command replay. A failed run retains raw data, skill and any partial trace/video. Local run/demonstration data is ignored and preserved by lifecycle cleanup.

Home opens first and presents up to three completed `human_capture` reproductions with native previews, keeping only the newest eligible run per demonstration. Synthetic, failed, active and preview-less runs do not fill the showcase. Selection uses the newest-first history summary, not hardcoded demo IDs, copied media or a recognition algorithm. With no eligible human recordings it shows an empty state. Public evidence is a separate approved bundle, never an automatic Home seed. History still exposes other non-deleted runs.

Home's introduction explains simulated drawing without claiming real hardware or perfect reproduction. Watch a run opens the first featured recording with available video through the existing run-loading path; it issues no execution request. Navigation uses one desktop row and a compact two-row mobile layout. Entrance/hover transitions are CSS-only, do not hide initial content, and respect reduced-motion preferences. Native previews remain unobscured; activity counts sit below the handwriting gallery.

DELETE `/runs/{run_id}` removes a finished run from history by persisting `deleted_at` in its existing record. It is idempotent, rejects running runs, and never deletes demonstrations or execution evidence. Lists omit deleted records; direct artifact access, skill reuse and request-ID deduplication retain them. No new datastore or simulation command is involved.

The web polls history and selected runs with `summary=true`; selected summaries retain progress/logs/results and indicate skill availability without retransmitting geometry. Raw, skill and trace tabs load their independent artifacts on demand.

Preview-image availability is independent of video availability and refreshed from saved files at startup and run completion. Older runs without native PNGs show an icon, never a fabricated preview or broken image.

Normal runs extract a new skill from unchanged raw input using current processing settings. Shifted-paper runs explicitly reuse the exact saved skill and change only the run's paper pose.

Trajectory spacing uses the pinned runtime's actual whole-substep interval, not nominal control Hz. Trace/ink timestamps and simulated duration use MuJoCo time; video sampling follows that clock. Wall duration is reported separately. Non-mouse pressure values are retained even when constant; variation metadata remains separate. Mixed mouse strokes never acquire fabricated pressure. Read-only status polling may retry bounded connection resets; execution POST is never retried automatically.

## Dependencies and Evidence
Keep robosuite 1.4.1 and MuJoCo 2.3.7. Use React/TypeScript/Vite, FastAPI/httpx/jsonschema, NumPy and imageio/FFmpeg. There is no active video perception or LIBERO. The pinned robosuite distribution itself declares OpenCV/SciPy as transitive requirements; these are not project drawing algorithms.

Six generated fixtures validate generic drawing, not word/shape recognition: block BOT, cursive hello, star, house, double cursive hello, fine loops. Real Panda physics, measured color/width/pressure, encoded-video equivalence and a second paper pose are automated gates. Local personal captures can be replayed separately without changing immutable raw data. Physical Surface Pen acceptance remains a manual gate in [Build 03](../../dev_plans/build-03.md).

## Layout
Build 04 adds a curated `evidence/` bundle containing only the three human captures explicitly approved for public submission, their provenance/checksums, measured results and representative native simulator media. Other runtime data remains private and ignored. `src/scripts/evaluate.py` runs inside the existing service images: preparation reuses Stroke Processing; evaluation reuses Drawing Environment, Skill To Robot and Robot Control. It introduces no service, controller or network API. One-off containers write isolated exports, never app history. The fixed three-pose comparison disables only lead/integral compensation in the baseline; OSC and advancement feedback remain enabled. Neither method is learned.

Runtime code lives under `src/`: `frontend` (web), `backend/orchestrator`, `backend/simulation`, and `scripts` (shared lifecycle). Contracts, fixtures, and cross-service tests stay at the repository root. Follow [Development Rules](development-rules.md).
