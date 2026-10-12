# skill-to-bot

`skill-to-bot` is a robot skill transfer project. The initial goal is to convert one human manipulation demonstration video into a compact skill representation and execute the corresponding pick, move, place, and release behavior in simulation.

Architecture 01 is implemented and locally verified for the supplied controlled front-camera can demonstration. Four isolated Docker services use HTTP REST/JSON between services and WebSockets for browser status snapshots. The [completed build checklist](dev_plans/build-01.md) records validation evidence and scope limits.

## Documentation

- [Documentation index](docs/README.md)
- [Architecture index](docs/architecture/README.md)
- [Initial MVP architecture](docs/architecture/architecture-01.md)
- [Final system roadmap](docs/architecture/architecture-final.md)
- [Development rules](docs/architecture/development-rules.md)
- [Build 01 checklist](dev_plans/build-01.md)
- [Build 02 checklist](dev_plans/build-02.md) - Tier 1 selection, support reasoning, ordered transport and cumulative verification.

## Current build target

Maintain the implemented [Architecture 01](docs/architecture/architecture-01.md) MVP.

Do not implement final-roadmap capabilities unless they are promoted into the existing active architecture document.

## Repository setup

The canonical project and repository name is `skill-to-bot`.
The Git remote is `git@github.com:emranB/skill-to-bot.git`. SSH authentication uses the developer's existing user-level SSH configuration; never store keys in this repository.

Root and service `.env` files contain local, non-secret deployment values and are ignored by Git. Their `.env.example` counterparts provide safe defaults. Docker Compose uses internal service hostnames, while the browser reaches orchestrator through web's `/api` proxy. Lifecycle commands create missing environment files without overwriting local settings.

## Local build

Start Docker Desktop with its Linux engine, then run the root command through Git Bash:

```bash
bash build-and-run.sh
```

The web application is at [localhost:5173](http://localhost:5173). `bash run.sh`, `bash stop.sh`, and `bash clean.sh` manage this Compose project. Cleanup removes runtime containers and networking, preserving demonstrations and recorded run artifacts. Service directories expose the same four commands for their own container.

The controlled MVP uses a stationary-camera video, a rough object hint, and a workspace span. Draw a box or click the object, click the yellow **Confirm Mapping** action, then **Run Demo**. Editing the mapping or choosing another video clears confirmation. Run status shows the current robot phase and inline Logs, Skill, and Observations tabs. The hint is snapped to the object. Lift means separation from the support surface. Grasp and release events are motion estimates; camera depth is not recovered. The simulation verifies physical lift, placement, and release independently.

Build 02 closure adds focused-crop segmentation retries, visible YOLO/GrabCut provenance, refreshed object bounds during source playback, and ordered transport waypoints. Front-plane mapping remains sideways-only. Projected-table mapping is an explicit two-axis image-to-table approximation, not recovered physical depth or perspective-correct motion. The robot checks actual object convergence at each transport waypoint. Physical recording failures and remaining acceptance gates are recorded cumulatively in Build 02; Tier 1 is not frozen.

## Live Camera

For camera capture, select **Live Camera**, allow camera permission, hint the object and set the workspace span, then **Confirm Mapping**. **Start Recording** and **Stop Recording** control capture in the human demonstration view. Stopping opens a Yes/No prompt: **No** discards the unsaved clip and returns to the live feed; **Yes** saves it first, then starts the full pipeline automatically. A saved clip remains available if processing or execution fails.

Camera capture is video-only and needs localhost or HTTPS plus browser camera/MediaRecorder support. Recordings stop automatically at 59 seconds to stay within the 60-second processing limit. Nothing is uploaded before Yes. The orchestrator normalizes WebM/MP4 capture to H.264 MP4, capped at 100 MB, and stores `data/live_demos/live_demo_<UTC timestamp>_<unique suffix>.mp4`. Live demos are local, ignored by Git, and preserved by cleanup. Live capture uses the same perception path as an uploaded video. The camera should stay still. Depth is not reconstructed, and separation is rejected when the view does not provide enough evidence.

## Validation

Camera browser tests inject a synthetic stream and use the real MediaRecorder, save endpoint, perception, and physics. No physical camera is used in automated verification. The supplied human-video pipeline is verified separately.

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check services tests
python -m ruff format --check services tests
RUN_INTEGRATION=1 python -m pytest tests -q
cd apps/web
npm ci
npx playwright install chromium
npm run build
npm test
```

Primary verification uses the real running stack. `npm test` covers real desktop execution, inline run details, mapping changes, mobile media/layout, and readable failures. Root tests cover the pipeline, failed physical manipulation, lifecycle, and dependency recovery. Do not run outage tests during an active manipulation. Small service regressions remain for contract boundaries and unsafe outcomes; run them with `docker compose run --rm --no-deps <service> python -m pytest tests -q` when changing that service.

The [GitHub workflow](.github/workflows/build.yml) builds all four images and runs these end-to-end checks on pushes and pull requests. It uses pinned actions, read-only repository permissions, bounded execution, and failure diagnostics. Equivalent checks run locally; hosted verification of uncommitted changes requires an explicit commit and push. Nothing is published or deployed by CI.

The existing architecture and development documents define the authoritative requirements. The explicitly requested build checklists track execution and verification without overriding those requirements. Build 01 records the verified baseline. Build 02 records the Tier 1 perception extension. Maintain these documents in place; add further documents only when explicitly requested.
