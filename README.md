# RAILCODE · Automatic Block Planning

RAILCODE is a full-stack prototype for coordinating maintenance blocks across Engineering, Traction Distribution and S&T, while presenting corridor availability and train-impact estimates to divisional operations teams.

> **Prototype only:** all trains, maintenance records, forecasts, availability values and system connectors in this repository are illustrative. The application does not connect to Indian Railways TMS, SMMS, TDMS, BDMS or COA, and its planning output is not operational advice or authority to take a block. Every proposed block requires validation against live train operations, local safety rules and approval by authorized control-office staff.

## Live demo simulation

The Docker demo runs a synthetic railway scenario automatically on startup. Its bounded random-walk simulator updates overall and critical-asset availability, four sample corridor health scores, train counts, chart history, and scenario workload counts every two seconds. Use the Overview page's **Pause demo / Resume demo** control to pause or resume the scenario. Simulation telemetry is broadcast to open dashboards over WebSockets; restarting the backend starts a fresh demo session. Simulated KPI counts are scenario indicators, not live operational task or block counts.

The **NO LIVE RAILWAY DATA** banner is intentional: the simulated TMS, SMMS, TDMS and COA feeds are not real connections, and changing the simulation does not modify train operations or create an approved possession.

## Unified command-center workflows

- **Command dashboard:** simulated current and projected uptime, block-utilization gauge, safety alert feed, per-department pending-work donut, and corridor health.
- **Traffic + maintenance Gantt:** switch between 7-day tactical and 30-day strategic views. Passenger and goods-traffic bands are illustrative. Drag a proposed block to a different time and date to save a what-if override and see a clearly simulated train-delay/conflict estimate.
- **AI-assisted backlog:** search and filter illustrative TMS/SMMS/TDMS work by department, division, asset type and overdue status. Criticality scores are recalculated from sample priority, due date and corridor health; same-corridor tasks are clustering suggestions, not a geographic calculation.
- **Emergency blocks:** simulated critical alerts can create proposed emergency windows. This action does not contact operations or grant a possession.
- **Coordination hub:** add primary/secondary departments and same-corridor tasks to a persisted joint-block requisition; track whether participating teams have confirmed resources. Every request stays a proposal requiring review.
- **Divisional controller edits:** edit maintenance-task details/status/criticality and block schedule, departments, resource readiness, status, forecast figures and notes. Changes are stored in SQLite, immediately refreshed in the submitting dashboard and broadcast to all connected dashboards over WebSockets. Block edits surface same-corridor overlaps; any changed block remains subject to required authorized approval.
- **System health:** monitor WebSocket/API connectivity separately from simulated external-feed status. TMS, SMMS, TDMS, COA and BDMS are explicitly shown as *not connected*, with timestamped synthetic ingestion events.
- **Focused workspaces:** Overview, Block planner, Corridors, Analytics, System health, Maintenance and Coordination hub each have a dedicated page to keep unrelated work out of the way.
- **Appearance:** switch between light and dark mode from the header; the selected theme is remembered on that browser.

## Features

- RAILCODE React operations dashboard with dedicated operational pages, corridor availability, a filtered maintenance task queue and schedule export.
- FastAPI API with persistent SQLite tasks and proposed block schedules.
- Background demo simulator with bounded, changing network availability, corridor status, sample train counts, departmental pending/overdue workloads and rolling chart history.
- Dashboard controls to pause, resume, change simulation speed (1×/2×/4×) and reset the demo; telemetry is pushed every two seconds.
- Explainable urgency-weighted planner: ranks tasks using criticality, priority and due status, then groups compatible work by corridor and department into nominal overnight windows.
- Weekly and monthly planning horizon selection, coordinated task-window suggestions and approval-required schedule output.
- WebSocket notifications so task and schedule changes appear across connected dashboards.
- Responsive, focused workspaces for overview, block planning, maintenance, corridors, coordination, analytics and system health.
- Docker Compose setup with persistent data volume and a health-checked backend.

## Run with Docker

From this directory:

```sh
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). The API health endpoint is at [http://localhost:8080/api/health](http://localhost:8080/api/health). SQLite data is stored in the `railplan-data` Docker volume.

## Run locally

Requirements: Node.js 20+, npm, Python 3.12+.

Terminal 1 — API:

```sh
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — UI:

```sh
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies API and WebSocket requests to the local backend. The backend creates `data/railplan.db` on first start; set `DATABASE_PATH` to choose another SQLite path.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service health and demo-mode indicator |
| `GET` | `/api/demo/status` | Current synthetic telemetry, chart history and simulator state |
| `POST` | `/api/demo/control` | Pause, resume, reset or set simulation speed |
| `GET` | `/api/command` | Unified simulated command-center metrics, alerts, enriched task backlog, clusters, integrations and joint requests |
| `POST` | `/api/alerts/{alert_id}/emergency-block` | Create a sample emergency proposal from an active simulated alert |
| `GET` | `/api/tasks` | List maintenance tasks, priority-ranked |
| `POST` | `/api/tasks` | Validate and add a maintenance task |
| `PATCH` | `/api/tasks/{task_id}` | Save controller changes to a task and broadcast a refresh |
| `GET` | `/api/blocks` | List proposed or seeded block windows |
| `PATCH` | `/api/blocks/{block_id}` | Save controller changes to a block, report overlaps and broadcast a refresh |
| `POST` | `/api/plan/generate` | Generate a weekly or monthly coordinated schedule |
| `POST` | `/api/blocks/{block_id}/what-if` | Override a proposed block date/time and calculate sample overlap impact |
| `POST` | `/api/blocks/{block_id}/joint-request` | Persist a cross-department requisition and resource readiness state |
| `WS` | `/ws/updates` | Receive simulated telemetry and task or schedule refresh events |

`POST /api/plan/generate` accepts `{"horizon":"This week"}` or `{"horizon":"This month"}`. The response includes task coverage, the planning method and `approval_required: true`.

`POST /api/demo/control` accepts `{"action":"pause"}`, `{"action":"resume"}`, `{"action":"reset"}`, or `{"action":"set_speed","speed":2}`. Supported speeds are 1, 2 and 4. The simulator is in-memory and starts automatically with the API; its sample values do not overwrite maintenance-task records.

The what-if API accepts `{"start_time":"02:00","date_iso":"2026-09-30"}`. Controller task/block edits require the full editable record and are validated before persistence. Joint requests accept department and task ID arrays with a `resources_confirmed` flag. A successful response records a proposal for review, not a granted block. Controller edits are demo data; they do not update railway source systems or grant a real possession.

## Planner behavior and limitations

The current planner is a deterministic, explainable heuristic—not a trained ML model or railway-approved optimization engine. It combines a weighted criticality/priority/due-date ranking with greedy same-corridor grouping, subject to a nominal four-hour overnight window and a maximum of three tasks per window. It uses illustrative corridor train counts, does not consume a timetable, goods forecast, interlocking constraints, engineering safety rules, resource rosters or real corridor possession feeds, and does not calculate safety-validated headway/conflict constraints. Manual what-if conflict and train-delay estimates are synthetic illustrations, not timetable validation. Same-corridor cluster suggestions do not use surveyed geographic coordinates. All generated windows and emergency blocks are proposals only; pending resource readiness is surfaced and no API grants possessions. Dashboard availability, corridor status, train counts, utilization, alerts, projected uptime, and workload KPIs are simulated values for demonstration, not forecasts or live measurements.

Before operational use, replace the sample seed data with authorized, authenticated and audited TMS/SMMS/TDMS/COA/BDMS integrations; validate timetable and freight forecasts; encode applicable engineering and protection rules; add role-based approval, audit history, secure deployment, monitoring and operational testing with railway domain experts. Do not use the demo planner to authorize real work or affect train movements.

## Tests

```sh
cd backend
python -m unittest discover -s tests -v
```

```sh
npm run build
```
