# HELP Parking System — editable diagrams

Proposed design, 27 September 2026. Build locally first; AWS deployment comes later. These diagrams describe the planned system, not completed software.

## Open and edit

Open `HELP_Parking_System_All_Diagrams.drawio` in draw.io Desktop, or open it from your device in diagrams.net. The master file has nine page tabs at the bottom. Every box, AWS icon, label and arrow is editable; these are not flattened pictures.

Double-click text to rename it. Drag a shape to move it. Select an arrow to change its path or label. Save as `.drawio` to keep editing later. Export a PDF or PNG when you need a report image.

The individual files are convenient copies. Changes to them do not automatically update the master file. Pick one version to maintain.

| File | Purpose |
| --- | --- |
| `01_Local_Development_Architecture.drawio` | Website, API, local database, AI reader and simulated gate on your computer. |
| `02_AWS_Network_and_Security_Architecture.drawio` | Two pages: network traffic; security and supporting services. |
| `03_Parking_System_Process_Flow.drawio` | Two pages: entrance with guard-approved guests, and exit. |
| `04_Vehicle_Access_Message_Sequence.drawio` | Three pages: registered entry, guest entry with guard, and vehicle/guest exit. |
| `05_Parking_Database_Entity_Relationship_Diagram.drawio` | Proposed records and how they connect. This is a logical design, not final SQL. |

## Read the AWS pages

The diagrams use draw.io's native AWS architecture shapes. The outer boundary is AWS; the VPC is your private network inside AWS. Subnets divide that network. Arrows show who starts a request; replies return over the connection. Dashed arrows on the support page show permissions rather than picture traffic.

1. The campus connector reads the camera locally and sends selected pictures over HTTPS to EC2. It also asks for decisions and controls the local gate. A camera that supports secure uploads could replace part of this connector later.
2. The Internet gateway provides the VPC Internet route. The EC2 server has a public address and accepts HTTPS on port 443. The website and API share this server.
3. EC2 reads and writes RDS over encrypted MySQL connections on port 3306. RDS has no public address. Its security group accepts database connections only from the application's security group.
4. The RDS subnet group includes private subnets in two availability zones. The pilot has one database instance; the second subnet does not mean a standby is running.
5. EC2 calls AWS services over outbound HTTPS using its IAM instance role. The support page shows the same EC2 server as the network page.

## Services in plain words

| Service or setting | Role in this design |
| --- | --- |
| EC2 | Runs the website, API and AI reader. Choose its size after measuring the model. |
| RDS MySQL | Stores users, vehicles, permits and parking records. |
| VPC, subnets, routes and security groups | Control where services live and which connections are allowed. |
| Secrets Manager | Stores the database login details. The server reads them; the browser and camera never receive them. Rotation needs separate configuration. |
| IAM instance role | Gives EC2 permission to use only the AWS resources it needs, without hardcoded AWS access keys. |
| CloudWatch | Collects configured logs and measurements and sends configured alerts. |
| Systems Manager | Provides authenticated server management without opening inbound SSH. Requires the agent, permissions and service connectivity. |
| RDS backups and encryption | Enable recovery and protect stored data. Set retention and test restoration. |
| KMS | Supplies encryption keys used by the configured services. A separate customer-managed key is optional for this pilot. |
| S3 — optional | Stores approved plate pictures privately. Set a retention period; keep database records as references to images. |
| Domain and trusted TLS certificate | Give the HTTPS endpoint a stable name and a certificate clients can verify. Configure certificate renewal on the EC2 HTTPS server. |

A load balancer with ACM, private application subnets, NAT Gateway or VPC endpoints, and Multi-AZ failover are later options. They are not included in this small pilot. A single EC2 and single RDS instance can have downtime; the diagram does not promise high availability.

## Assumptions to settle before real deployment

- The partner's earlier LAN-only video requirement needs agreement before pictures are sent to AWS. Local development can proceed meanwhile.
- Confirm campus network access, camera protocol, device authentication, gate interface, passage sensors and emergency rules. Internet access does not mean an unauthenticated camera may submit requests.
- Python is proposed for the API; the diagrams do not depend on C#. Confirm the model package and runtime with the partner.
- Opening a gate is not proof that a car entered. Save an entry or exit only after passage is confirmed. Gate safety sensors remain in control.
- The flowcharts cover both entry and exit. Unknown plates wait for the guard to open the gate. After confirmed entry, save the plate as Guest and save the entry time together. Guest status alone does not grant future access. After confirmed exit, save the exit time and close the matching visit; unmatched exits go to review.

## Reference documentation

- [AWS shapes in draw.io](https://www.drawio.com/docs/diagram-types/aws-diagrams/)
- [RDS in a VPC and DB subnet groups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html)
- [RDS network examples](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.Scenarios.html)
- [Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [Secrets Manager private endpoints](https://docs.aws.amazon.com/secretsmanager/latest/userguide/vpc-endpoint-overview.html)
- [Load balancer HTTPS certificates](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/https-listener-certificates.html)

The files were structurally validated and rendered with a local draw.io viewer for visual review. No AWS resources were created.

## Entry and exit update — 27 September 2026

Recognition and guard-action logs may be stored before passage. Parking entry/exit records are stored only after a sensor or guard confirms passage. Repeated passage messages must not create duplicates. If saving fails after passage, retain the passage report locally and retry using its unique ID.

An existing blocked vehicle must not become a new guest to bypass its status. A guard may handle it manually, with the action recorded. Guests are not automatically added to the permanent access list.

The earlier database diagram remains a starting point. Implementation will also need a parking-visit record linking entry and exit, plus guest classification and the approving guard reference.

## Revised exit flow

Exit does not check permits, payments, blocked status or guest approval. Scan the plate, look up its latest open visit, calculate time parked and show it on the exit screen. Open the gate. After confirmed passage, save the exit time and final duration and mark the visit EXITED. The displayed duration uses the current time; the saved duration uses the confirmed exit time.

If no entry is found, show Duration unavailable and still allow exit; save an unmatched EXITED record after passage. If the plate cannot be read or the system is unavailable, the guard assists. Missing entry history must not be treated as a permission failure.
