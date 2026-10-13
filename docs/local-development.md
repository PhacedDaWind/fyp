# Run HELP Park locally

The implemented stack is Vue 3, Python FastAPI, MySQL 8.4 and Liquibase. No AWS account is required. Plate recognition and gate movement are simulated.

## Start

Start Docker Desktop. From the project directory in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
docker compose up -d --build
npm install
npm run dev
```

Open the Vite URL, normally http://127.0.0.1:5173. Find the initial administrator email and random password in `.env`. Do not share or commit that file. Setup keeps existing settings. The initial account is created once; changing `.env` does not change an existing account's password.

The API listens on localhost port 8000. Vite proxies `/api` to it. MySQL has no host/public port. Its named Docker volume keeps records across restarts. `docker compose stop` stops the services without deleting data. `docker compose down -v` erases the database volume, so do not use it for routine shutdown.

Earlier browser-only records are not automatically imported or erased. The database starts empty. Register fictional vehicles for testing.

## Available workflows

- Admin/guard sign-in; expiring HttpOnly cookie sessions and hashed passwords.
- Administrators manage vehicles and permits, block/unblock vehicles, export CSV and create accounts.
- Guards can use the simulator and visit history but cannot modify the vehicle registry or create accounts.
- A valid registered entry opens the simulated gate. Entry is saved only after **Confirm vehicle passed**.
- An unknown plate waits for **Guard: manually open gate**. After passage, the guest plate and entry are saved together in parking visits. Guest history does not become permanent entry permission.
- Exit scans look up entry time, show duration and open the simulated gate without permit/payment/blocked-status checks. Passage saves the exit time and marks the visit EXITED.
- Missing entry displays **Duration unavailable** and saves an unmatched exit after passage.
- Unique scan IDs, transactional writes and a unique open-visit plate prevent duplicate entry/passage records.
- Visit history includes guest type, entry/exit, final duration and approving guard. Latest 1,000 visits are loaded; the inside count refers to that loaded set.

Times are stored in UTC and displayed in Malaysia time. Entry permission uses Malaysia's calendar date. Duration shown at exit is calculated at scan time; the saved duration uses the actual confirmation time. Scan attempts expire after five minutes.

To correct a mistyped plate, scan again with the corrected plate before opening. Blocked/expired known vehicles are denied entry; the guest opening button applies only to unknown plates.

## Liquibase migrations

Liquibase is the sole schema owner; SQLAlchemy reflects the migrated tables and does not create them. `db/changelog/001-initial.sql` contains the initial changeset. The custom Liquibase Docker image includes the MySQL JDBC driver. Compose waits for a successful migration before starting the API.

Add a new changeset for each future change. Do not edit an applied changeset. For larger projects, introduce an include-based root changelog while preserving existing changeset identities and paths.

```powershell
docker compose run --rm migrate --changelog-file=changelog/001-initial.sql validate
docker compose run --rm migrate --changelog-file=changelog/001-initial.sql update-sql
docker compose run --rm migrate --changelog-file=changelog/001-initial.sql update
docker compose restart api
```

Review generated SQL before applying changes. The initial rollback drops tables and is only for disposable databases. Migration and app use the same development account for now; separate their privileges before cloud deployment. Local Docker-network MySQL is unencrypted; RDS deployment must use verified TLS.

Liquibase fits the team's existing familiarity and does not require the application itself to use Java. [Official MySQL integration documentation](https://docs.liquibase.com/community/integration-guide-5-0/connect-liquibase-with-mysql-server).

## Verify

```powershell
npm test
npm run build
docker compose exec -T api pytest -q
```

The API tests use real local MySQL and remove only their own uniquely prefixed records. They cover authentication, roles, validation, duplicate plates, guest approval, save-after-passage behavior, expiry, unrestricted exits and duplicate reports.

API documentation: http://127.0.0.1:8000/docs. Mutating requests need `X-Parking-Client: admin`; the Vue client supplies it. Sessions use same-origin cookies. Local HTTP cookies are intentionally not Secure; enable HTTPS and Secure cookies before remote hosting. No permissive cross-origin policy is configured.

## Not connected yet

Real camera ingestion, partner-model inference, physical gate/display adapters, offline passage queues, payment administration, password recovery and production operations remain future work. `backend/recognition.py` defines the future image-reader interface; the simulator supplies plate text explicitly. No model accuracy or inference timing has been measured.

The older diagrams describe the broader proposed system. This implementation is its first local database-backed milestone.

## Password and permit settings

Use **Change password** in the top navigation. Enter your current password and the new password twice (at least 12 characters). All sessions are signed out after success. Sign in again with the new password; `.env` remains the initial setup record, not your current password. Both guards and administrators can change their own password.

For a new registration, paste up to 100 plates separated by commas, semicolons or new lines. They share the owner, vehicle description and permit settings shown in the form. Use separate registrations for different owners. The server saves the batch in one transaction; duplicates or invalid records reject the whole batch. Editing an existing vehicle still edits only that vehicle.

New permits default to three calendar months from the start date. Select 1–24 months, or Custom dates. The calculated expiry is inclusive and uses the last day of shorter months when necessary (31 January + 1 month = 28 February, or 29 in a leap year). Existing permits keep their dates until you change them.
