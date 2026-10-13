# HELP University parking system architecture

Proposed design, 26 September 2026. Develop and validate locally first; deploy to AWS later. These diagrams describe planned components, not features already implemented. Implementation update, 28 September 2026: the Vue frontend now uses a FastAPI backend, MySQL and Liquibase, with admin/guard authentication and simulated entry/exit workflows. Real AI and hardware integration remain pending. See ../local-development.md for the running implementation.

## Diagrams

**Editable draw.io versions:** see [the diagram pack and editing guide](drawio/README.md). Open [the master file](drawio/HELP_Parking_System_All_Diagrams.drawio) for all nine pages, including expanded AWS network/security diagrams and a parking process flowchart. The expanded draw.io pack is the latest presentation version; the Mermaid files below remain the earlier compact overview.

Each `.mmd` file is editable Mermaid source. Paste its contents into the Mermaid Live Editor or use a Mermaid-capable Markdown editor. This document's companion `diagrams.md` contains the same diagrams in Markdown fences for convenient viewing.

1. `01-local-development.mmd`: all application components on the development computer.
2. `02-aws-deployment.mmd`: future EC2/RDS deployment with a campus camera/device connector.
3. `03-access-sequence.mmd`: capture, recognition, permission checks and gate action.
4. `04-database-erd.mmd`: initial logical data model, before SQL migrations.

## Main decisions

| Area | Proposed decision | Reason / confirmation needed |
| --- | --- | --- |
| Frontend | Keep the existing Vue admin interface | Replace browser storage with API calls once the backend is ready. |
| Backend | Python API proposed; C# remains an alternative | Python fits the team's stated familiarity. Confirm the stack change with the supervisor and partner before implementation. Diagram boundaries work with either language. |
| Local database | MySQL on the development computer | Match the intended RDS database engine. No AWS account or cloud database is needed for local development. |
| Recognition | Separate worker process with a stable input/output contract | Begin with a mock; replace it with the confirmed partner model. Do not load the model for every HTTP request or run expensive inference on the API event loop. |
| Local startup | Direct processes initially; optionally Docker Compose later | Avoid making Docker installation a prerequisite. Containerisation can follow the initial working API. |
| Future hosting | One EC2 host for web/API/worker plus private RDS MySQL | A manageable FYP deployment; one EC2 host is a single point of failure, not a high-availability design. |
| Camera integration | Campus connector reads RTSP locally and sends selected frames | Direct camera-to-cloud upload depends on camera capabilities and campus networking. The connector can also return decisions to local devices. |
| Evidence | Local files first; optional private S3 later | Keep image bytes out of ordinary relational records; store an object key only if retention is approved. |
| Payments | Administrative payment-status records initially | Live online payment processing is a separate scope decision; do not collect card details. |

## Local development first

Run the Vue dev server, API, MySQL and recognition worker on the same computer. Use a development proxy for browser API requests. Bind the database and private worker interface to loopback; keep credentials in environment variables outside source control. Set a compatible MySQL version before creating migrations.

Start with uploaded images or recorded video and simulated display/barrier outputs. A real camera can be added on the LAN without changing the admin interface or permission rules. A mock recogniser returns an explicitly marked simulated plate result and must not feed a real barrier. The selected inference adapter must be visible in configuration.

## AWS deployment later

The diagram shows a small, single-host deployment: HTTPS terminates at the EC2 reverse proxy, which serves the built Vue app and routes API requests internally. The database resides in a private RDS DB subnet group spanning the required availability zones; that subnet arrangement does not itself mean the database uses Multi-AZ failover. RDS is not publicly accessible. Permit database traffic only from the application security group. The browser and campus devices never connect directly to RDS.

Expose only the intended HTTPS endpoint; keep the API implementation port and recognition worker private to the host. Use TLS for database connections, an instance role for AWS service access, secure secret management and backups. Choose EC2 CPU/GPU capacity after model benchmarking. Training is a separate workflow and need not run on the always-on application host.

The campus connector initiates outbound HTTPS connections. It uploads selected frames and polls the resulting event for a decision; responses travel over those requests. This design needs no inbound Internet connection to the barrier. Continuous video uploads are not assumed. If continuous cloud video processing becomes necessary, assess a supported producer/streaming service, bandwidth and costs separately.

The partner's development document explicitly keeps camera video on the campus LAN. Moving inference to AWS is therefore a proposed change requiring agreement. A fallback compatible with that original plan is to move the recognition worker beside the campus connector and send only recognition results to the cloud API. That still needs connectivity for cloud permission decisions unless a separate offline authorisation design is implemented.

## Recognition and access are separate

The model supplies candidate text and confidence; it does not decide who may enter. The API applies blocked status, valid permit or visitor approval, configured payment rules and gate policies. Store dates/timestamps consistently: timestamps in UTC, permit-day boundaries evaluated in Asia/Kuala_Lumpur. Confidence thresholds require validation; a returned confidence value is not proof of accuracy.

Each device submission has a unique event key. Retried uploads return the same event; repeated decision retrieval must not trigger repeated opening. Commands include a decision ID and short expiry, and the local connector records executed IDs. A decision that timed out is not replayed automatically on reconnect. If a command outcome is uncertain, report it for review instead of assuming success. Barrier safety sensors and interlocks remain under the hardware controller.

An ALLOW decision, successful barrier command and actual vehicle passage are different events. Record entry/exit only when a passage sensor or agreed crossing-confirmation method supports it. Otherwise label the record as an access attempt, not a confirmed journey. Uncertain recognition and network failure lead to review/manual handling, not automatic opening; emergency access/egress policy must be agreed with campus staff.

## Initial backend contracts

These are design contracts, not implemented routes. All admin mutations require an authenticated administrator and role checks. Device endpoints use separate scoped device identities.

| Route | Purpose |
| --- | --- |
| `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` | Admin session lifecycle; password hashes only, secure session cookies in deployment. |
| `GET /api/vehicles`, `POST /api/vehicles`, `PATCH /api/vehicles/{id}` | Search and manage owners/plates; unique normalized plate enforced by the database. |
| `POST /api/vehicles/{id}/archive` | Retire a vehicle without deleting historic access records. |
| `POST /api/permits`, `PATCH /api/permits/{id}` | Permit dates and status, with server-side validation. |
| `POST /api/visitors`, `PATCH /api/visitors/{id}` | Visitor requests and approval decisions. |
| `POST /api/payments`, `GET /api/payments` | Record and review payment status, if included in scope. |
| `POST /api/device-events` | Authenticated device submits image, camera ID, unique event key and capture timestamp. |
| `GET /api/device-events/{id}` | The submitting device polls processing state and its access decision. |
| `POST /api/device-events/{id}/ack` | Idempotent report of display/barrier command outcome. |
| `POST /api/device-events/{id}/passage` | Report actual passage with confirmation source; deduplicate retries. |
| `GET /api/access-events`, `GET /api/audit-log` | Review access attempts, confirmed passages and administrator changes. |

A recognition result should contain `event_id`, `plate_candidates`, `confidence`, `model_version`, `inference_ms` and `error_code` where applicable. A permission response should contain `decision_id`, `outcome` (`ALLOW`, `DENY`, `REVIEW`), `reason` and `expires_at`. Apply image size/type limits, device-to-camera ownership checks and bounded polling/processing timeouts. Keep admin-session and device authentication separate.

## Data model notes

The ERD is a logical starting point. Before migrations, add created/updated timestamps, indexes, constraints and archival fields. `matched_vehicle_id` is nullable for unknown plates; never create a registered vehicle automatically from an untrusted recognition result. Payment rows are records, not a payment processor. `reviewed_by` references an admin user and is nullable until review. The unique device event key is scoped to a provisioned device; introduce a device-credential table during authentication design. Preserve event/decision/passages when a vehicle is archived. Avoid storing raw camera credentials in admin-facing records.

## Build order

1. Confirm backend language; establish API skeleton, local MySQL migrations and environment configuration.
2. Add admin login, roles and server-side validation.
3. Connect the existing vehicle registry to the API; add owners, permits and visitor approval. Offer explicit import of local sample/user data rather than silently importing it.
4. Build a simulated recognition-event flow that exercises actual database permission rules, duplicate handling, timeouts and the admin event screen.
5. Add recorded-video and RTSP input to the connector, retaining simulated hardware outputs.
6. Replace the mock recogniser with the agreed model once the files are available; benchmark the full workflow and validate thresholds.
7. Add real display/barrier adapters after the hardware interface and safety procedure are confirmed.
8. Package and test locally, then provision EC2/RDS, migrate a test dataset and run cloud connectivity and latency trials.

The first four steps can progress without training the AI or renting AWS infrastructure. A useful first acceptance test is: register a vehicle, assign a valid permit, submit a simulated plate event, see ALLOW, block the vehicle, submit a new event and see DENY. Neither step should operate real hardware.

## Items to confirm

- Backend language and which partner components must be reused.
- Camera model, RTSP/snapshot support, resolution, night performance and campus network access.
- Whether cloud image processing is acceptable given the partner's LAN-only video design.
- Barrier/display interfaces, acknowledgement behaviour and available passage/safety sensors.
- Data collection permission, image retention period, visitor workflow and payment rules.
- AWS account ownership, region, budget and whether one-host downtime is acceptable for the FYP pilot.

## References

- User-supplied project proposal, partner development document and discussion through 26 September 2026.
- [AWS: RDS access scenarios in a VPC](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.Scenarios.html).
- [AWS: Working with RDS in a VPC](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html).
- [AWS: RTSP producer example for Kinesis Video Streams](https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/examples-rtsp.html). This illustrates a producer-based streaming option; Kinesis is not required by this design.
