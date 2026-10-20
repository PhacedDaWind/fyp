# Run HELP Park locally

The implemented stack is Vue 3, Python FastAPI, MySQL 8.4 and Liquibase. No AWS account is required. Gate movement and plate scans are simulated. Photo uploads use a YOLOv9-t640 detector and CCT-S v2 global OCR through ONNX Runtime on CPU.

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

Campus RTSP camera ingestion, partner-model inference, physical gate/display adapters, offline passage queues, payment administration, password recovery and production operations remain future work. `backend/recognition.py` runs the public YOLOv9/CCT global photo reader; the simulator still uses explicitly reviewed plate text. The replacement read all three user-supplied photos of the same Malaysian two-line plate correctly. That is a smoke test, not a measured Malaysian accuracy rate; the photo test displays processing time per request.

The older diagrams describe the broader proposed system. This implementation is its first local database-backed milestone.

## Password and permit settings

Use **Change password** in the top navigation. Enter your current password and the new password twice (at least 12 characters). All sessions are signed out after success. Sign in again with the new password; `.env` remains the initial setup record, not your current password. Both guards and administrators can change their own password.

For a new registration, paste up to 100 plates separated by commas, semicolons or new lines. They share the owner, vehicle description and permit settings shown in the form. Use separate registrations for different owners. The server saves the batch in one transaction; duplicates or invalid records reject the whole batch. Editing an existing vehicle still edits only that vehicle.

New permits default to three calendar months from the start date. Select 1–24 months, or Custom dates. The calculated expiry is inclusive and uses the last day of shorter months when necessary (31 January + 1 month = 28 February, or 29 in a leap year). Existing permits keep their dates until you change them.


## Global plate model photo testing

The photo upload runs FastALPR 0.4.0, a YOLOv9-t640 plate detector (open-image-models 0.6.0), and CCT-S v2 global plate OCR (fast-plate-ocr 1.1.0), using ONNX Runtime 1.23.2 on CPU. These public models replace the HyperLPR3 Chinese-plate baseline. They are separate from the pending partner model.

Rebuild the API image (`docker compose up -d --build api`) to install it. The detector, OCR and YAML config are downloaded over HTTPS during the build, with pinned SHA-256 checksums. Upload requests use explicit local model paths and never download weights. The first photo initializes the cached models and includes that loading time; later requests reuse them.

Open **Parking simulator & visits**, upload a JPEG/PNG/WebP (up to 8 MB and 20 megapixels), and select **Read number plate**. The preview overlays numbered detection boxes; table numbers identify the same regions. It shows every detection, including unreadable or incorrect ones, with separate detection and recognition scores and a predicted country. These are model outputs, not verified identities or measured accuracy. An unreadable crop is distinguished from no detection. Photos and predictions are not saved by this endpoint.

Choose the actual plate's result or type a correction before scanning. Multiple detections are possible: this detector also flagged a yellow ground parking-space marking in one supplied photo. No prediction is automatically copied into the simulator, opens a gate or saves a visit. Non-ASCII predictions remain visible instead of being stripped into plausible plate numbers.

All three supplied photos (front, closer front, night rear) returned the correct plate with this model pair. They show the same car and plate, and the closer front is a crop of the first photo. They demonstrate an improvement on those examples, not accuracy on unseen Malaysian vehicles. Collect an independent set of vehicles, fonts, one/two-line layouts, camera positions, day/night and weather conditions before evaluating accuracy.

For independent inference without Docker/MySQL, use Python 3.12 in a virtual environment:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
.venv/Scripts/python backend/download_models.py
.venv/Scripts/python -m pytest backend/test_recognition.py backend/test_photo_api.py backend/test_reset_admin.py -q
```

Models are cached in ignored `backend/models/global-plates/`. `PLATE_MODEL_DIR` changes that directory. `backend/model_config.py` declares the exact source URLs and checksums. The older HyperLPR3 cache is unused and can remain in place.

No training was performed to produce these results. For future Malaysian adaptation, a useful annotated dataset pairs each full image with a plate bounding box, the exact plate text, and a grouping identifier for its vehicle or capture session. The box trains detection; cropped plate plus text trains OCR. Keep every crop/near-duplicate/visit of the same vehicle in the same train, validation or test group to avoid inflated scores. The three supplied images alone cannot establish a useful independent training/evaluation split. A separate annotation and fine-tuning workflow can build on the upstream OCR training tools when a broader dataset is available.

Official sources: [FastALPR](https://github.com/ankandrew/fast-alpr), [detector models](https://github.com/ankandrew/open-image-models), [global OCR and fine-tuning](https://github.com/ankandrew/fast-plate-ocr), [ONNX Runtime](https://onnxruntime.ai/docs/).

## Recover a forgotten administrator password or missing .env

Start Docker Desktop successfully first. If it displays a WSL error, resolve that before recovery; the database cannot be accessed while Docker's Linux engine is unavailable. Preserve the existing Docker data/volumes.

From the project directory:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/recover-admin.ps1
# If more than one administrator exists:
powershell -ExecutionPolicy Bypass -File scripts/recover-admin.ps1 -Email your-admin@example.com
```

The recovery command identifies the existing containers for this checkout, reconstructs `.env` using their original database secrets, and generates a new random password for one existing administrator. Read `ADMIN_EMAIL` and `ADMIN_PASSWORD` in the ignored `.env` to sign in, then change the password in the app. It revokes that administrator's sessions and records the reset in activity history. It does not erase vehicles or visits, create a public password-reset endpoint, or reset guards.

Do not run `setup.ps1` to recover a lost `.env` for an existing database: newly generated database secrets will not match the existing volume. If the original containers have been removed too, this recovery command cannot retrieve their old configuration; separate database credential recovery is required.


## Phone live camera

See [phone camera setup](phone-camera.md) for local HTTPS, one-time phone certificate trust, live capture and repeated frame detection. The existing photo picker continues to work on HTTP.
