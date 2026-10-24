# EventBase — deployable service

This folder packages the EventBase interface with a Django application, PostgreSQL persistence, role-specific server sessions, and Docker deployment files. The included EventBase screens support the manager and participant demo journeys.

## Run the judging demo locally

Prerequisites: Docker Desktop with Docker Compose.

1. Copy `.env.example` to `.env`.
2. Replace `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` with unique random values. In PowerShell, create a value with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
3. Run `docker compose up --build` from this folder.
4. Open `http://localhost:8000`.

The demo starts with fictional sample events and accounts:

- Manager: `manager@eventbase.demo` / `eventbase-demo`
- Participant: enter any email and event code `FUTURE25`

The sample credentials are intentionally public for judges. Use only fictional data in this demo, and do not reuse the demo password for a real account.

## Publish it for judges

Deploy this folder as a Docker service on a host you control, attach a persistent PostgreSQL database, and configure the environment variables below in the host dashboard. The application listens on the `PORT` environment variable and serves the UI, API, and static assets from one origin.

Required configuration:

- `DJANGO_SECRET_KEY`: a unique random secret stored in the host's secret manager.
- `DATABASE_URL`: PostgreSQL connection string for the persistent database.
- `ALLOWED_HOSTS`: the public hostname, without a scheme.
- `CSRF_TRUSTED_ORIGINS`: public origin including `https://`, for example `https://events.example.com`.
- `COOKIE_SECURE=true` on an HTTPS site.
- `DEBUG=false`.
- `DEMO_MODE=true` and `SEED_DEMO=true` if judges should use the shared demo sign-in shown above.
- `SECURE_SSL_REDIRECT`: enable only when the host's reverse proxy forwards the original HTTPS scheme correctly.

On startup, the container applies Django migrations, gathers static files, seeds the fictional demo data when enabled, and runs Gunicorn. For a private organizer deployment, disable `DEMO_MODE` and `SEED_DEMO`, then create a manager account with `python manage.py create_manager --email manager@example.com --password 'a-long-unique-secret' --organization 'Your organization'`. Set up database backups and a monitored deployment before inviting real users.

## Data and scope

Persistent records cover organizations, events, event membership, check-ins, submission metadata, support requests, feedback, and manager operations state. Participant accounts are created when someone joins with an event access code; manager accounts are created by an operator. Passwords are stored using Django's password hashing, browser sessions are HttpOnly and SameSite, state-changing requests use CSRF protection, and manager queries are scoped to their organization.

This is a judges-ready service foundation, not a claim that every product integration is complete. File selection currently saves filenames only; file bytes are not uploaded. Email/text/social delivery, live keynote streaming, external API integrations, staffed support notifications, and real AI responses are not connected; those areas remain clearly simulated in the interface. Add those providers, operational monitoring, a backup/restore drill, and organization onboarding before using the service for real event operations.

## Operations

- Health endpoint: `/api/health`
- Django admin: `/admin/` (superuser only)
- Local demo database: PostgreSQL in the `eventbase_pgdata` Docker volume.
- Stop the local stack: `docker compose down`. This keeps the database volume.
- Remove the local demo database: `docker compose down -v` (permanent deletion of local demo data).
