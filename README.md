# skill-to-bot

One-shot drawing skill retargeting: draw once with pen, touch or mouse, then a simulated Panda reproduces the strokes on paper with a rigid attached pen.

Human capture uses numeric browser Pointer Events data, not a recognized word. Raw input remains independent of the processed, robot-independent DRAW skill. The robot adapter maps that skill into a paper pose. Output ink comes from the Panda's **actual simulated pen-tip motion** during drawing/contact, never from rendering desired paths as the result.

## Run
Start Docker Desktop with Linux containers, then use Bash (Git Bash on Windows):

```bash
bash build-and-run.sh
```

Open [localhost:5173](http://localhost:5173). **Home** shows completed human handwriting and saved demos. It selects the latest native preview per human demonstration, up to three, without hardcoded IDs or synthetic substitutes. A fresh installation shows an empty state until a human drawing completes. Choose **New drawing** or **Workspace**, pick a color and brush size in Human Drawing, then **Save & Run**. Tool changes affect new strokes. Undo removes the last stroke; Clear resets the drawing. Results show the actual simulator recording, paper proximity, physical contact, tracking/shape error and inline Logs, Raw Input, Skill and Trace. Playback offers 1x, 2x, 5x and 10x without changing physics. Run history reopens a saved demonstration. Its trash button confirms removal from history, preserving the demonstration and execution files; active runs cannot be deleted. Normal runs reprocess immutable raw input with current settings; **Run on shifted paper** reuses the exact saved skill at a modest second pose.

Home introduces the drawing-to-robot workflow in plain language, with real human results rather than promotional substitutes. **Watch a run** opens an existing native recording; it never starts a robot command. The compact navigation, hover/focus feedback and short entrance transitions share the light interface. Reduced-motion preferences disable decorative motion, and results remain visible from the first frame.

`bash run.sh`, `bash stop.sh` and `bash clean.sh` manage only this project. Cleanup preserves personal demonstrations and run artifacts. Each service has equivalent scoped scripts. Environment examples hold safe deployment defaults; existing local environment files are never overwritten. The Git remote uses SSH; keys stay outside the repository. No automatic commit or push occurs.

## Data and Architecture
Three services: React/TypeScript/Vite web, FastAPI orchestrator and robosuite 1.4.1 / MuJoCo 2.3.7 simulation. REST/JSON suffices; no active vision service, broker, database, recognition or LIBERO task.

- Raw demonstrations: `data/demonstrations/<id>.json`, stored unchanged and reusable.
- Skill: normalized paper X-right/Y-up, ordered strokes, color, normalized brush width, relative time, source aspect and provided non-mouse pressure; no Panda/world pose.
- Runs: `data/runs/<id>/run.json`, `skill.json`, `robot-plan.json`, `trace.json`, `simulation-result.json`, `simulation.mp4`, `simulator-final.png`.
- Robot trace: independently measured simulator tip/contact/ink state in paper-local meters.

Drawing preserves aspect and fits inside reachable paper margins. The Panda approaches, descends, follows a continuous speed-bounded trajectory, lifts and travels between strokes. Drawing ink uses a bounded visual geometry pool. Actual MuJoCo contact is reported; a bounded 1.5 mm geometric tip-to-paper tolerance also gates deposition to handle numerical contact jitter. No ink is deposited during travel or lifting.

Mouse capture omits pressure. Pen/touch pressure is saved and reproduced when provided, including constant input values. `pressure_observed` reports non-mouse variation, not a claim of calibrated force. Missing input uses configured constant pressure (0.5), labeled as fallback rather than a measurement. Release-event zeros remain in immutable raw input but do not erase the processed stroke endpoint. Brush size is full width as a fraction of canvas height, preserving scale on retargeting. Simulated ink radius is half the mapped brush width times `(0.5 + effective_pressure)`; preview uses the same rule. Color and width remain fixed within captured strokes. Neither pressure nor brush width implies physical force control. Tilt/twist are saved when exposed but not physically reproduced.

Video frames come directly from the MuJoCo offscreen camera while Panda physics runs. The closer camera makes paper detail visible. Frame times, measured sample counts and ink counts are recorded in `trace.json`; the final independent simulator PNG is compared against the decoded MP4 in end-to-end tests. This is a recorded simulator feed, not a live streaming endpoint or an input-canvas reconstruction.

## Verification
```bash
python -m pip install -r requirements-dev.txt
python -m ruff check src/backend tests
python -m ruff format --check src/backend tests
npm ci --prefix src/frontend
npm run format:check --prefix src/frontend
npm run build --prefix src/frontend
npm audit --omit=dev --audit-level=high --prefix src/frontend
docker compose config --quiet
docker compose run --rm --no-deps orchestrator python -m pytest tests -q
docker compose run --rm --no-deps simulation python -m pytest tests -q
RUN_INTEGRATION=1 python -m pytest tests -q -s
cd src/frontend
npx playwright install chromium
npm test
```

Run service physics, root outage/physics and browser execution serially. Six deterministic fixtures cover block BOT, cursive hello, star, house, double cursive hello and fine loops. Generate them with `python tests/fixtures/generate_drawings.py`. They are explicitly `synthetic_fixture`, **not personally collected challenge evidence**. Browser automation also cannot validate physical Surface Pen pressure. Set `DRAWING_DEMONSTRATIONS` to comma-separated local demonstration IDs to include immutable personal capture replays.

The [build workflow](.github/workflows/build.yml) checks source, builds the three images and runs service, real physics and browser tests. Local checks do not establish hosted CI success. Current results and manual hardware gates are in [Build 03](dev_plans/build-03.md).

CI caches pinned installation inputs, rejects unused TypeScript code, checks dependency consistency, bounds each verification stage and allows cleanup time in the overall job budget. Physics tests stop at the first failure; service, root and browser physics run serially. Failure diagnostics are retained and project containers are cleaned up. Production nginx applies same-origin content restrictions and security headers, caches hashed assets and revalidates the application document. Compose binds services to localhost. Remote deployment requires the server/provider identity, deployment directory, authentication and TLS setup; no destination or credentials are guessed.

## Scope and History
Tier 1 supports bounded multi-stroke 2D paths on a small fixed horizontal paper plane and modest reachable pose shifts. It does not include pen pickup, handwriting recognition, real robot hardware, physical tilt/force reproduction or arbitrary paper poses. Excessive data, unreachable poses, contact failures, deadlines and quantitative partial failures are reported rather than silently accepted.

Physical Surface Pen acceptance remains pending until an operator tests the device. Personal mouse captures are available for replay but do not establish stylus validation. Synthetic and simulated success must not be described as physical hardware acceptance.

The active tree is `src/frontend`, `src/backend/orchestrator`, `src/backend/simulation`, and `src/scripts`. The old video pick-and-place archive is not part of this repository. Local ignored recordings, if any remain, stay under `data/deprecated/` and are not built or tested.

Authoritative docs: [Drawing Architecture](docs/architecture/architecture.md), [Development Rules](docs/architecture/development-rules.md), [Build 03](dev_plans/build-03.md).
