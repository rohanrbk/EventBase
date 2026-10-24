# EventBase

EventBase is an event operations and attendee experience prototype with separate manager and participant journeys.

## Local preview

Run `python eventbase_server.py` in this folder, then open `http://127.0.0.1:8000`. The server creates a local SQLite database in `data/` on first run.

Demo manager: `manager@eventbase.demo` / `eventbase-demo`  
Demo participant: enter any email and event code `FUTURE25`.

## Deployable service

The `production/` folder contains the Django and PostgreSQL service, Docker configuration, migrations, and demo seed command. See [production/README.md](production/README.md) for local Docker and hosted deployment instructions. The production UI is served from the existing EventBase interface with same-origin authentication and APIs.

## Scope

The demo persists event workspaces, participant access, check-ins, submission metadata, support requests, feedback, and operations state. File bytes, email and social delivery, live streams, staffed notifications, and real AI integrations are not connected yet; those interface elements are marked or behave as simulations.
