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

The controlled MVP uses a fixed front-camera video and an operator-selected object rectangle plus workspace span. Check these inputs, click the yellow **Confirm Mapping** action, then **Run Demo**. Editing the mapping or choosing another video clears confirmation. Run status shows the current robot phase and inline Logs, Skill, and Observations tabs. Grasp and release events are motion estimates; camera depth is not recovered. The simulation verifies physical lift, placement, and release independently.

## Validation

```bash
python -m pip install -r requirements-dev.txt
RUN_INTEGRATION=1 python -m pytest tests -q
cd apps/web
npm ci
npx playwright install chromium
npm run build
npm test
```

Primary verification uses the real running stack. `npm test` covers real desktop execution, inline run details, mapping changes, mobile media/layout, and readable failures. Root tests cover the pipeline, failed physical manipulation, lifecycle, and dependency recovery. Do not run outage tests during an active manipulation. Small service regressions remain for contract boundaries and unsafe outcomes; run them with `docker compose run --rm --no-deps <service> python -m pytest tests -q` when changing that service.

The [GitHub workflow](.github/workflows/build.yml) builds all four images and runs these end-to-end checks on pushes and pull requests. It uses pinned actions, read-only repository permissions, bounded execution, and failure diagnostics. Its equivalent checks run locally; the first hosted run requires an explicit commit and push. Nothing is published or deployed by CI.

The existing architecture and development documents define the authoritative requirements. The explicitly requested `dev_plans/build-01.md` tracks execution and verification without overriding those requirements. Maintain these documents in place; add further documents only when explicitly requested.
