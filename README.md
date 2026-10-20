# HELP Park

Local parking system for HELP University: Vue frontend, Python FastAPI backend, MySQL and Liquibase migrations.

## Run locally

Start Docker Desktop, then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
docker compose up -d --build
npm install
npm run dev
```

Open the Vite URL (normally http://127.0.0.1:5173). Your initial admin credentials are in the ignored `.env` file.

To test using a phone, connect it to the same Wi-Fi as the computer and open `http://COMPUTER_LAN_IP:5173` (find the computer's IPv4 address with `ipconfig`). Sign in, open **Parking simulator & visits**, take a close photo of a plate, then tap **Read plate**. Review or correct the suggested text before **Scan plate**. If the phone cannot connect, allow the Vite/Node development server through the computer's firewall. Mobile camera capture uses the browser's photo picker; live preview and repeated frame detection are now available through the [phone camera HTTPS setup](docs/phone-camera.md). The photo test uses a public YOLOv9-t640 detector and CCT-S v2 global plate OCR through ONNX Runtime on CPU; the partner model is still pending. It displays numbered detection boxes, raw predictions, confidence scores, predicted country and processing time for review. It does not save photos or open a gate.

See [the local development guide](docs/local-development.md) for login, migrations, tests, data persistence and workflow instructions.

Implemented: admin/guard authentication, vehicle management, server activity history, guest entry with manual guard approval, simulated entry/exit, duration display and database-backed parking visits. Records are saved after confirmed passage. Exit does not check permit or blocked status.

The partner AI model, continuous camera feed and physical gate are not connected. A phone photo can be uploaded for temporary OCR testing. Previous localStorage data is left untouched; the new registry uses MySQL.

## Tests

```powershell
npm test
npm run build
docker compose exec -T api pytest -q
```

## Architecture

[Architecture plan](docs/architecture/README.md) and [editable draw.io diagrams](docs/architecture/drawio/README.md). These describe the wider proposed system; AWS deployment comes later.
