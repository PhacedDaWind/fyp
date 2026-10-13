# Architecture diagrams

Editable Mermaid diagrams for the proposed local-first HELP University parking system. See README.md in this folder for assumptions and build order.

## 01-local-development

```mermaid
flowchart LR
  admin[Administrator]
  subgraph pc[Development computer]
    ui[Vue admin frontend]
    api[Backend API\nAuthentication and parking rules]
    db[(Local MySQL)]
    connector[Camera and device connector]
    worker[Recognition worker\nMock first, partner model later]
    store[Local evidence folder\nOptional retained images]
    simulator[Display and barrier simulator]
  end
  source[Sample image or video\nLater: campus RTSP camera]
  admin --> ui
  ui <-->|HTTP JSON via local dev proxy| api
  api <-->|SQL| db
  source -->|Frames| connector
  connector -->|Selected frame and event ID| api
  api -->|Recognition request| worker
  worker -->|Plate candidates and confidence| api
  api -->|Optional image retention| store
  connector -->|Poll decision for event ID| api
  api -->|Allow, deny or review with expiry| connector
  connector -->|Simulated action| simulator
  simulator -->|Acknowledgement| connector
  connector -->|Action result| api
```

## 02-aws-deployment

```mermaid
flowchart LR
  admin[Admin browser]
  subgraph campus[HELP campus network]
    camera[IP camera]
    gateway[Campus connector\nExisting PC or suitable gateway]
    devices[Display and barrier controller\nWith local safety interlocks]
    camera -->|RTSP stream on campus LAN| gateway
    gateway <-->|Device-specific interface| devices
  end
  subgraph aws[AWS VPC - future deployment]
    subgraph public[Public subnet]
      subgraph ec2[EC2 application host]
        proxy[HTTPS reverse proxy\nVue static files and API routing]
        api[Backend API\nAuth, permissions and decisions]
        worker[Recognition worker\nCPU or GPU after benchmarking]
        proxy <-->|Internal HTTP| api
        api <-->|Internal recognition interface| worker
      end
    end
    subgraph private[Private DB subnet group]
      db[(RDS for MySQL\nNot publicly accessible)]
    end
    api <-->|MySQL TLS; DB security group permits app only| db
  end
  evidence[(Optional private S3 evidence storage)]
  admin <-->|HTTPS 443| proxy
  gateway -->|Outbound HTTPS: frame upload and decision polling| proxy
  proxy -->|Responses on connector-initiated requests| gateway
  api -->|Optional images via instance role| evidence
```

## 03-access-sequence

```mermaid
sequenceDiagram
  participant C as Campus connector
  participant A as Backend API
  participant R as Recognition worker
  participant D as MySQL
  participant B as Barrier / display adapter
  C->>A: Submit frame (device identity, unique event ID, capture time)
  A->>D: Create or retrieve event using unique device/event key
  A-->>C: Accepted or existing event reference
  A->>R: Recognise selected frame
  R-->>A: Candidates, confidence, model version, inference time
  A->>D: Save recognition; check vehicle, permit and visitor approval
  Note over A,D: Apply server time in Asia/Kuala_Lumpur; blocked vehicles override permits
  alt No reliable match, missing permission or processing failure
    A->>D: Record DENY or REVIEW with reason
  else Eligible vehicle and sufficiently confident recognition
    A->>D: Record ALLOW with decision ID and short validity period
  end
  C->>A: Poll event decision over outbound HTTPS
  A-->>C: Decision, reason, decision ID and expiry
  alt Decision is fresh, ALLOW and not already executed
    C->>B: Show result and request opening
    Note over C,B: Hardware controller enforces obstacle and safety interlocks
    B-->>C: Acknowledge command or report fault
    C->>A: Acknowledge action with decision ID
    A->>D: Record command outcome
    opt Passage sensor or reliable crossing confirmation available
      C->>A: Report confirmed vehicle passage and direction
      A->>D: Create entry or exit record
    end
  else DENY, REVIEW, expired decision or connection timeout
    Note over C,B: Do not auto-open; use agreed manual fallback
  end
```

## 04-database-erd

```mermaid
erDiagram
  ADMIN_USER ||--o{ AUDIT_LOG : performs
  VEHICLE_OWNER ||--o{ VEHICLE : owns
  VEHICLE ||--o{ PARKING_PERMIT : has
  PARKING_PERMIT ||--o{ PAYMENT_RECORD : records
  VEHICLE ||--o{ VISITOR_REQUEST : requests
  CAMERA ||--o{ RECOGNITION_EVENT : captures
  VEHICLE o|--o{ RECOGNITION_EVENT : matches
  RECOGNITION_EVENT ||--o| ACCESS_DECISION : produces
  ACCESS_DECISION ||--o| PASSAGE_EVENT : may_confirm
  ADMIN_USER {
    bigint id PK
    string email UK
    string password_hash
    string role
    boolean active
  }
  VEHICLE_OWNER {
    bigint id PK
    string name
    string category
    string institutional_id
  }
  VEHICLE {
    bigint id PK
    bigint owner_id FK
    string normalized_plate UK
    string description
    boolean blocked
  }
  PARKING_PERMIT {
    bigint id PK
    bigint vehicle_id FK
    date valid_from
    date valid_to
    string status
  }
  PAYMENT_RECORD {
    bigint id PK
    bigint permit_id FK
    decimal amount_myr
    string reference
    string status
    datetime paid_at
  }
  VISITOR_REQUEST {
    bigint id PK
    bigint vehicle_id FK
    datetime valid_from
    datetime valid_until
    string approval_status
    bigint reviewed_by FK
  }
  CAMERA {
    bigint id PK
    string gate_name
    string direction
    boolean enabled
  }
  RECOGNITION_EVENT {
    string id PK
    bigint camera_id FK
    bigint matched_vehicle_id FK
    string device_event_key UK
    datetime captured_at
    datetime received_at
    string recognized_plate
    decimal confidence
    string model_version
    string processing_status
    string evidence_key
  }
  ACCESS_DECISION {
    string id PK
    string recognition_event_id FK,UK
    string outcome
    string reason
    datetime expires_at
    string command_status
    datetime acknowledged_at
  }
  PASSAGE_EVENT {
    string id PK
    string decision_id FK,UK
    string direction
    datetime passed_at
    string confirmation_source
  }
  AUDIT_LOG {
    bigint id PK
    bigint admin_user_id FK
    string action
    string entity_type
    string entity_id
    datetime created_at
  }
```

