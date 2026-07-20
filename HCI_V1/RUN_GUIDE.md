# HCI_2.1 Web UI — Official Run Guide

Operations guide for the **HCI_2.1** Floor Plan Model Trainer on a brand-new machine.

HCI_2.1 supports **two entry points** that share the same core (`generate_labels` → `generate_full_ifc`):

| Workflow | Who uses it | Replaces the other? |
|----------|-------------|---------------------|
| **1 — Google Drive / Web UI** | Operators in the browser | No |
| **2 — Node.js webhook** | External Node frontend | No — **additive only** |

> **Related:** `DEPLOY.md`, `requirements.txt`, `.gitignore`.

---

# 1. Project Overview

**HCI_2.1** is a FastAPI app for floor-plan ML and BIM export: upload/auto-label/correct/train, scale/metadata, and IFC4 generation. A Node frontend can also submit a single image and receive an IFC via callback without using the browser UI.

## Capabilities

| Feature | What it does |
|---------|----------------|
| **Web UI** | `web/index.html` on port **8000** |
| **Auto Label** | YOLO-seg on `images_raw` → labels + marked overlays |
| **Correct Labels** | Edit polygons; save / revert; fine-tune |
| **Training** | Scratch / fine-tune / merge / promote to `best_hci21.pt` |
| **IFC (UI)** | From corrected labels → `gdrive_dataset/output/` |
| **IFC (webhook)** | From Node upload → job-local IFC → `callback_url` |
| **Scale / Metadata** | UI calibration and property JSON |

## Architecture (shared core)

```text
         Google Drive Flow                 Node Webhook Flow
                │                                  │
                ▼                                  ▼
         Existing UI routes              POST /api/generate-ifc-webhook
                │                                  │
                └──────────────┬───────────────────┘
                               ▼
                        HCI_2.1 core
                   generate_labels()
                           │
                   generate_full_ifc()
```

### Backward compatibility

- Google Drive workflow — **unchanged**
- Auto Label UI — **unchanged**
- Training / Corrections — **unchanged**
- UI IFC generation — **unchanged**
- Node webhook — **additive only**

---

# 2. Folder Structure

`PROJECT_ROOT` = **parent of `HCI_2.1`**.

```text
PROJECT_ROOT/
├── HCI_2.1/
│   ├── web/                 # server.py (UI + webhook)
│   ├── logic/
│   ├── config/
│   ├── scripts/
│   ├── auto_label.py
│   ├── DEPLOY.md
│   ├── RUN_GUIDE.md
│   └── requirements.txt
├── gdrive_dataset/
│   ├── images_raw/          # Workflow 1
│   ├── images/train/
│   ├── labels/train/
│   ├── marked/
│   ├── metadata/
│   ├── output/              # UI IFCs
│   ├── runs/
│   └── webhook_uploads/     # Workflow 2
│       └── {job_id}/
│           ├── input/
│           ├── labels/
│           ├── output/      # webhook IFC (before callback)
│           └── work/
├── cubicasa_hqa_500/.../best.pt
├── yolov8n-seg.pt
├── best_hci21.pt
└── best_gdrive.pt
```

### Created automatically on startup

`images_raw`, `images/train`, `labels/train`, `metadata`, `marked`, `output`, `runs`, **`webhook_uploads`**.

Per-job `input/labels/output/work` are created when a webhook request is accepted.

---

# 3. System Requirements

| Item | Requirement |
|------|-------------|
| Python | **3.11** |
| Conda env | `improved_model_train` |
| Packages | `pip install -r requirements.txt` (includes **`requests`** for webhook callbacks + Drive tooling) |
| Port | **8000** |

Optional: `gdown` (Drive download), `cairosvg` (SVG thumbs).

---

# 4. Clone From Git

```bash
mkdir -p /opt/hci && cd /opt/hci
git clone <YOUR_REMOTE_URL> HCI_2.1
# PROJECT_ROOT = /opt/hci
```

---

# 5. Create Environment

```bash
conda create -n improved_model_train python=3.11 -y
conda activate improved_model_train
cd PROJECT_ROOT/HCI_2.1
pip install -r requirements.txt
```

Ensure `ifcopenshell` and `requests` are installed (both listed in `requirements.txt`).

---

# 6. Models

Same model for UI Auto Label and webhook YOLO via `resolve_hci21_model()`.

```bash
export HCI21_MODEL_PATH=/absolute/path/to/best.pt
```

| Model | Required for |
|-------|----------------|
| CubiCasa `best.pt` or env | Auto Label + webhook |
| `yolov8n-seg.pt` | UI training |
| `best_hci21.pt` | Optional promote/fallback |
| `best_gdrive.pt` | Optional UI compare only |

---

# 7. Runtime Dataset

| Path | Workflow |
|------|----------|
| `images_raw` … `runs`, shared `output/` | **1 — Drive / UI** |
| `webhook_uploads/{job_id}/…` | **2 — Node** (isolated; no training pollution) |

---

# 8. Environment Variables

| Variable | Purpose |
|----------|---------|
| `HCI21_MODEL_PATH` | YOLO weights (UI + webhook) |
| `HCI_MODEL_PATH` | Legacy alias |
| `HCI21_ALLOW_ANY_PYTHON` | Bypass interpreter gate |

---

# 9. Starting the Server

```bash
conda activate improved_model_train
cd PROJECT_ROOT/HCI_2.1/web
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

- UI: `http://localhost:8000/`
- Webhook: `http://localhost:8000/api/generate-ifc-webhook`

Startup creates dataset folders (including `webhook_uploads/`) and enforces the conda env name unless overridden.

---

# 10. Workflow 1 — Google Drive / Web UI

```text
Google Drive (or Upload)
      ↓
Download / images_raw
      ↓
Auto Label
      ↓
Corrections
      ↓
Training (optional)
      ↓
Scale / Metadata (optional)
      ↓
Generate IFC
      ↓
gdrive_dataset/output/{basename}.ifc
```

### How to test the existing UI

1. Start the server (§9).
2. Open `http://localhost:8000/`.
3. Upload or Drive-download → Auto Label → Correct Labels → Generate IFC → Download IFC.
4. Confirm IFC under `gdrive_dataset/output/`.

---

# 11. Workflow 2 — Node.js webhook

```text
Node Frontend
      ↓
POST multipart image + callback_url
      ↓
POST /api/generate-ifc-webhook
      ↓
Immediate { accepted, job_id, status: processing }
      ↓
BackgroundTasks: generate_labels() → generate_full_ifc()
      ↓
POST IFC (or error) to callback_url
```

### Endpoint

`POST /api/generate-ifc-webhook`

| Field | Type | Required |
|-------|------|----------|
| `image` | file | Yes |
| `callback_url` | form (`http://` or `https://`) | Yes |
| `meters_per_pixel` | form float | No (default `0.01`) |

### Immediate response

```json
{
  "accepted": true,
  "job_id": "a1b2c3…",
  "status": "processing"
}
```

YOLO and IFC run **in the background** (FastAPI `BackgroundTasks`). They are **not** awaited in this response.

### Example webhook request

```bash
# Terminal A: tiny callback receiver (example)
python -c "
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n)
        print('CALLBACK bytes', len(body))
        open('callback_dump.bin','wb').write(body)
        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
HTTPServer(('0.0.0.0', 9000), H).serve_forever()
"

# Terminal B: submit a floor-plan image
curl -X POST "http://127.0.0.1:8000/api/generate-ifc-webhook" \
  -F "image=@/path/to/plan.png" \
  -F "callback_url=http://127.0.0.1:9000/hci/callback" \
  -F "meters_per_pixel=0.01"
```

### Expected callback behaviour

HCI → Node, **multipart/form-data**:

| Result | Form fields |
|--------|-------------|
| Success | `success=true`, `job_id`, **`ifc_file`** = generated `.ifc` |
| Failure | `success=false`, `job_id`, `error` = message |

Watch stderr for `[hci21.webhook]` stage logs: accepted → Image saved → Running YOLO → YOLO complete → Generating IFC → IFC generated → Posting callback → Callback success/failed.

### Folder locations (webhook)

```text
gdrive_dataset/webhook_uploads/{job_id}/
  input/     # uploaded image
  labels/    # YOLO .txt
  output/    # {stem}.ifc  ← generated IFC before / for callback
  work/      # optional IFC debug JSON
```

Webhook does **not** write to `images_raw`, `images/train`, `labels/train`, `marked`, `runs`, or shared `output/`.

### Cleanup behaviour

Jobs are **retained** on disk after callback (no automatic TTL delete in the current implementation). Operators may manually delete old `webhook_uploads/{job_id}/` folders when disk space is needed. Future releases may add TTL cleanup (see `DEPLOY.md` Phase notes historically).

### Network note

HCI must be able to **reach** `callback_url` (outbound). If Node runs on another host, use that host’s reachable URL, not `localhost` on the Node machine from HCI’s perspective unless they share the same OS network namespace.

---

# 12. Training Workflow (UI only)

Unchanged: Train tab / Update Model → scratch, fine-tune, merge; promote to **`best_hci21.pt` only** (never `best_gdrive.pt`). Checkpoints under `gdrive_dataset/runs/`.

---

# 13. IFC Workflow (UI vs webhook)

| | UI | Webhook |
|--|----|---------|
| Labels | `labels/train` (after Auto Label / correct) | Job-local `webhook_uploads/.../labels/` |
| Core call | `generate_full_ifc` | Same `generate_full_ifc` |
| Output | `gdrive_dataset/output/{basename}.ifc` | `webhook_uploads/{job_id}/output/` then callback |

---

# 14. Deployment on a New Server

1. Clone under `PROJECT_ROOT`
2. Conda env + `pip install -r requirements.txt`
3. Models / `HCI21_MODEL_PATH`
4. Open port **8000** inbound; allow **outbound** to Node callbacks
5. Start uvicorn
6. Verify UI **and** (if used) webhook accept + callback

---

# 15. Troubleshooting

| Issue | Fix |
|-------|-----|
| Model not found | Set `HCI21_MODEL_PATH` |
| Wrong Python | Activate `improved_model_train` |
| ifcopenshell missing | `pip install ifcopenshell` |
| No images (UI) | Upload / Drive download first |
| Webhook 400 on callback_url | Must be absolute `http://` or `https://` |
| Accept OK, no IFC at Node | Check `[hci21.webhook]` logs; firewall egress; Node URL reachable from HCI |
| Port in use | Change `--port` or free 8000 |
| Training sees webhook images | Should not happen — webhook is isolated; if it does, check you did not copy files into `images/train` manually |

---

# 16. Verification Checklist

### Workflow 1 (UI)

- [ ] Server starts
- [ ] Upload / Drive works
- [ ] Auto Label works
- [ ] Correct Labels / Save / Revert work
- [ ] Training works (optional)
- [ ] Scale / Metadata work
- [ ] UI IFC generate + download work

### Workflow 2 (Node)

- [ ] `POST /api/generate-ifc-webhook` returns `accepted` + `job_id`
- [ ] Job folder appears under `webhook_uploads/{job_id}/`
- [ ] Callback receives `success=true` + `ifc_file` (or clear `error`)
- [ ] UI dataset folders unchanged by the webhook job
- [ ] `[hci21.webhook]` logs show stages without crashing uvicorn

---

# 17. Notes for Developers

- Do not commit `gdrive_dataset/` contents (including **`webhook_uploads/`**).
- Do not commit `*.ifc`, `*.pt`, or `runs/`.
- Prefer `HCI21_MODEL_PATH` in production.
- Keep `PROJECT_ROOT/HCI_2.1` layout.
- Do not call `_autolabel_worker` from new adapters — reuse `generate_labels` + `generate_full_ifc`.
- Nested `hci-3d-model/` / `IMPROVED_MODEL_*` are not the live runtime.

---

## Quick reference

```bash
conda activate improved_model_train
export HCI21_MODEL_PATH=/absolute/path/to/best.pt
cd PROJECT_ROOT/HCI_2.1/web
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

| Surface | URL |
|---------|-----|
| UI | `http://localhost:8000/` |
| Webhook | `POST http://localhost:8000/api/generate-ifc-webhook` |
