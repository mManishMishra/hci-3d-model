# HCI_2.1 — Production Deployment Guide

Deploy the HCI_2.1 FastAPI backend so it supports **both** entry points:

1. **Google Drive / Web UI workflow** (original — unchanged)
2. **Node.js webhook workflow** (additive — `POST /api/generate-ifc-webhook`)

The Node integration is an **additional doorway** into the same HCI_2.1 core. It does **not** replace Drive download, Auto Label UI, corrections, training, or UI IFC generation.

**Scope:** application under `HCI_2.1/` plus sibling runtime data/models under `PROJECT_ROOT`.

> **Also see:** `RUN_GUIDE.md` (operator runbook), `requirements.txt`, `.gitignore`.

---

## Dual-workflow architecture

```text
Google Drive / Browser UI                Node.js Frontend
        │                                        │
        ▼                                        ▼
 Existing routes                     POST /api/generate-ifc-webhook
 (/api/download, /api/autolabel,              │
  /api/ifc/generate/…)                        │
        │                                        │
        └──────────────┬─────────────────────────┘
                       ▼
              Shared HCI_2.1 core
         generate_labels()  →  generate_full_ifc()
         (resolve_hci21_model / YOLO)
```

| Workflow | Entry | Dataset paths | IFC destination |
|----------|-------|---------------|-----------------|
| **Drive / UI** | Browser + `/api/*` | `images_raw`, `images/train`, `labels/train`, … | `gdrive_dataset/output/{basename}.ifc` |
| **Node webhook** | `POST /api/generate-ifc-webhook` | Isolated `webhook_uploads/{job_id}/` only | `webhook_uploads/{job_id}/output/` then callback |

### Backward compatibility

- Existing Google Drive workflow — **unchanged**
- Existing Auto Label UI — **unchanged**
- Existing Corrections / Save / Revert — **unchanged**
- Existing Training / Fine-tuning / Model management — **unchanged**
- Existing UI IFC generation — **unchanged**
- Node integration — **additive only**

---

## 1. Repository layout

```text
<PROJECT_ROOT>/
    HCI_2.1/
        web/                          # FastAPI + UI + webhook route
        logic/
        config/
        scripts/
        auto_label.py
        requirements.txt
        DEPLOY.md
        RUN_GUIDE.md
        START_HCI_2.1.bat
    gdrive_dataset/                   # runtime (not in Git)
        images_raw/                   # Drive / UI uploads
        images/train/
        labels/train/
        marked/
        metadata/
        output/                       # UI-generated IFCs
        runs/
        webhook_uploads/              # Node jobs (auto-created)
            {job_id}/
                input/
                labels/
                output/
                work/                 # IFC debug sidecars
    cubicasa_hqa_500/
        runs/hqa500_offline/weights/best.pt
    yolov8n-seg.pt
    best_hci21.pt                     # optional
    best_gdrive.pt                    # optional (UI compare only)
```

### Why `PROJECT_ROOT` must be the parent of `HCI_2.1`

`web/server.py` and `logic/yolo_inference.py` set `PROJECT_ROOT` to the **parent** of `HCI_2.1`, then:

```text
DATASET_DIR = PROJECT_ROOT / "gdrive_dataset"
```

Keep:

```text
<PROJECT_ROOT>/HCI_2.1/...
<PROJECT_ROOT>/gdrive_dataset/...
```

---

## 2. Python

**Required:** Python **3.11** (64-bit).

```bash
conda create -n improved_model_train python=3.11
conda activate improved_model_train
```

The server refuses to start unless the interpreter path contains `improved_model_train`, unless `HCI21_ALLOW_ANY_PYTHON=1`.

---

## 3. Install dependencies

```bash
cd <PROJECT_ROOT>/HCI_2.1
pip install -r requirements.txt
```

### Required packages (from `requirements.txt`)

| Area | Packages |
|------|----------|
| Web | `fastapi`, `uvicorn[standard]`, `python-multipart` |
| Vision / ML | `numpy`, `opencv-python`, `pillow`, `ultralytics`, `torch`, `PyYAML`, `tqdm`, `packaging`, `typing-extensions` |
| IFC | `ifcopenshell` |
| HTTP (Drive + **webhook callbacks**) | **`requests`** |
| Optional UI | `gdown`, `cairosvg` |

**No new package was added solely for the webhook.** Callbacks use **`requests`**, already listed in `requirements.txt` (also used elsewhere in the stack). Do **not** require `httpx` unless you choose to add it later.

### Torch (CPU vs CUDA)

Install the correct torch wheel from [pytorch.org](https://pytorch.org) for the machine, then `pip install -r requirements.txt`.

### IFC

```bash
pip install ifcopenshell   # if missing after requirements install
```

---

## 4. Required models

Same resolver for **UI Auto Label** and **webhook** (`generate_labels` → `resolve_hci21_model()`).

| Priority | Source |
|----------|--------|
| 1 | `HCI21_MODEL_PATH` |
| 2 | `HCI_MODEL_PATH` (legacy) |
| 3 | `cubicasa_hqa_500/runs/hqa500_offline/weights/best.pt` |
| 4 | `best_hci21.pt` |
| 5 | smoke10 fallback |
| — | **Never** defaults to `best_gdrive.pt` |

| File | Role |
|------|------|
| CubiCasa `best.pt` or env path | Auto Label + webhook YOLO |
| `yolov8n-seg.pt` | Train from scratch (UI only) |
| `best_hci21.pt` | Promote target / fallback |
| `best_gdrive.pt` | UI compare only |

---

## 5. Runtime folders

Created automatically on server start (including webhook root):

- `images_raw`, `images/train`, `labels/train`, `metadata`, `marked`, `output`, `runs`
- **`webhook_uploads`**

Per-job folders (`input/`, `labels/`, `output/`, `work/`) are created when a webhook request is accepted.

| Folder | Used by |
|--------|---------|
| `images_raw` … `runs` | Drive / UI only |
| `webhook_uploads/{job_id}/…` | Node webhook only |

Webhook jobs **must not** write into `images_raw`, `images/train`, `labels/train`, `marked`, `runs`, or shared `output/`.

---

## 6. Environment variables

| Variable | Purpose |
|----------|---------|
| **`HCI21_MODEL_PATH`** | YOLO weights for UI Auto Label **and** webhook |
| **`HCI_MODEL_PATH`** | Legacy alias |
| **`HCI21_ALLOW_ANY_PYTHON`** | Bypass interpreter gate |

---

## 7. Running the server

```bash
conda activate improved_model_train
cd <PROJECT_ROOT>/HCI_2.1/web
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

| Item | Value |
|------|-------|
| **Port** | **8000** (UI + all APIs including webhook) |
| **Host** | `0.0.0.0` for remote clients; firewall / reverse proxy in production |
| **UI** | `http://<server>:8000/` |
| **Webhook** | `http://<server>:8000/api/generate-ifc-webhook` |

### BackgroundTasks behaviour

- Webhook accepts the upload, saves the image under `webhook_uploads/{job_id}/input/`, schedules work with FastAPI **`BackgroundTasks`**, and returns immediately:
  ```json
  { "accepted": true, "job_id": "...", "status": "processing" }
  ```
- YOLO + IFC run **after** the HTTP response.
- Results are delivered asynchronously via **`callback_url`** (not in the accept response).

### Callback behaviour

HCI posts **multipart/form-data** to the Node `callback_url`:

| Outcome | Fields |
|---------|--------|
| Success | `success=true`, `job_id`, file field **`ifc_file`** |
| Failure | `success=false`, `job_id`, `error=<message>` |

Logs use logger **`hci21.webhook`** (separate from UI SSE `_push`).

---

## 8. Production notes (Node + network)

### Firewall / network

- **Inbound:** clients (browser and/or Node) must reach HCI on port **8000** (or the proxied HTTPS port).
- **Outbound:** the HCI server must be able to **POST back** to Node’s `callback_url` (often another host/port). Open egress to that URL; private Docker/K8s networks need explicit routing.

If Node is on `https://node.example.com/hci/callback`, HCI must resolve and reach that host. Localhost callbacks only work when Node runs on the **same** machine as HCI.

### Reverse proxy (recommended)

Place nginx/Caddy/Traefik in front of uvicorn:

- Proxy `/` and `/api/` to `http://127.0.0.1:8000`
- Raise **proxy read/write timeouts** (YOLO+IFC can take minutes; webhook accept is fast, but UI IFC and large uploads need headroom)
- Prefer **HTTPS** termination at the proxy
- Optionally restrict `/api/generate-ifc-webhook` by IP allowlist or auth at the proxy (app-level auth can be added later)

Example nginx sketch:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    client_max_body_size 50m;
}
```

### Port requirements

| Port | Role |
|------|------|
| **8000** | HCI FastAPI (UI + Drive APIs + webhook) |
| Node callback port | Whatever Node listens on (HCI must reach it) |

---

## 9. Deployment checklist

- [ ] Clone so layout is `<PROJECT_ROOT>/HCI_2.1/...`
- [ ] Create conda env `improved_model_train` (Python 3.11)
- [ ] `pip install -r requirements.txt` (correct torch; ensure `requests`, `ifcopenshell`)
- [ ] Copy models / set `HCI21_MODEL_PATH`
- [ ] Confirm `gdrive_dataset/` (auto-created on start, including `webhook_uploads/`)
- [ ] Open firewall: inbound 8000 (or proxy); **outbound** to Node callback URLs
- [ ] Start uvicorn on `0.0.0.0:8000`
- [ ] Verify UI: `http://<server>:8000/`
- [ ] Verify webhook: accept response + callback receives IFC (see `RUN_GUIDE.md`)

---

## 10. Troubleshooting

| Issue | Fix |
|-------|-----|
| Missing `ifcopenshell` | `pip install ifcopenshell` |
| Model not found (UI or webhook) | Set `HCI21_MODEL_PATH` or place CubiCasa `best.pt` |
| Webhook accept OK, no callback | Check HCI egress to `callback_url`; Node must be reachable; inspect `[hci21.webhook]` logs |
| Wrong Python | `conda activate improved_model_train` |
| Wrong `PROJECT_ROOT` | Keep `HCI_2.1` as subdirectory of deploy root |
| Torch / `c10.dll` | Reinstall matching CPU/CUDA torch |

---

## Related files

| File | Role |
|------|------|
| `RUN_GUIDE.md` | How to run and test both workflows |
| `requirements.txt` | Pip deps (includes `requests`) |
| `.gitignore` | Ignores datasets, `webhook_uploads/`, `*.pt`, `*.ifc` |
