HelperAI MCQ Ensemble (Local + Offline, LAN-accessible)
======================================================

A FastAPI web app to answer multiple-choice questions using local AI models via Ollama. It is optimized for single-correct MCQs (4 options), supports image-based questions, runs fully offline after setup, and is controllable from your phone over LAN.

Key capabilities
----------------

- Phase-based ensemble (configurable 2+1):
  - Phase 1 (primaries for image path): `qwen2.5-vl:7b-instruct`, `llama3.2-vision:11b-instruct`
  - Default mode is `single`, which runs only the first primary for image questions; switch to `duo` to use both.
  - Phase 2 (on-demand tie-breaker): `qwen2.5-math:7b-instruct` (text model) runs only when needed.
  - Text MCQ path uses only the tie-breaker model by design (fast, decisive).
  - Freeform (no options) uses the same text model by default: `qwen2.5-math:7b-instruct`.
- Image pipeline with text-first optimization:
  - Optional watermark removal (OpenCV) emphasizing dark text, suppressing gray watermarks
  - OCR (PaddleOCR) parses question/options
  - Text-first switch: if OCR is good and options are detected, answer with the text tie-breaker only; otherwise include the image and use VLMs
- Single-correct and multi-answer support:
  - Single-correct is default and fastest
  - Multi-answer toggle on mobile for questions that require multiple letters (e.g., "A+C")
- Freeform Q&A (no options)
- Mobile UI with toggles:
  - Multiple correct, Remove watermark, Text-first, 15 s auto-refresh
  - Parsed question/options auto-filled from OCR; correct options highlighted in green
- Runtime controls & LAN access:
  - `/config`, `/status`, `/warm_math`, `/unload_math`
  - Mobile page at `/mobile` and QR shortcut at `/qr`

Tech stack
----------

- Backend: FastAPI, Uvicorn, Pydantic
- Inference: Ollama (local) for VLMs and text models
- OCR: PaddleOCR (PaddlePaddle)
- Preprocessing: OpenCV (opencv-python-headless), NumPy, Pillow
- Client: Vanilla HTML/JS (mobile-friendly), no external CDNs

Hardware target & models
------------------------

- Laptop: i9 CPU, 32 GB RAM, Intel Iris Xe (no dGPU)
- RAM plan: ~10 GB steady (Phase 1 duo), peak ~17 GB when tie-breaker runs
- Recommended quantizations:
  - Qwen2.5‑VL 7B Q4_K_M (~5 GB)
  - Llama 3.2 Vision 11B Q3_K_M (~5 GB)
  - Qwen2.5‑Math 7B Q4_K_M (~7 GB)

Installation
------------

1. Clone and enter the repo

```powershell
cd HelperAI
```

1. Install and pull models (Ollama)

```powershell
ollama pull qwen2.5-vl:7b-instruct
ollama pull llama3.2-vision:11b-instruct
ollama pull qwen2.5-math:7b-instruct
```

1. Create a virtual environment and install Python deps

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# PaddleOCR needs PaddlePaddle on Windows CPU
pip install paddlepaddle==2.6.1
```

Run
---

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Desktop UI: `http://localhost:8000/`
- Mobile UI: `http://<your-lan-ip>:8000/mobile`
- QR for mobile: `http://<your-lan-ip>:8000/qr` (or `http://localhost:8000/qr` on PC)

If Windows Firewall prompts, allow access so your phone can connect.

Usage (Desktop)
---------------

- Text MCQ: enter question and options (2–12). Click “Get Answer”.
- Freeform: use the "Freeform Question (no options)" section for a short answer + two-line explanation.

Usage (Mobile)
--------------

- Visit `/mobile` on your phone (same Wi‑Fi), pick an image, set toggles, tap Submit.
- Toggles:
  - Multiple correct: enable when the question expects multiple answers
  - Remove watermark: cleans gray backgrounds/watermarks before OCR (adds ~150–350 ms)
  - Text-first: for screenshots with mostly text (faster, often more accurate for single-correct)
- UI behavior:
  - Parsed question/options auto-fill from OCR
  - Correct options are highlighted in green on result
  - "Thinking…" appears while tie-breaker runs; optional 15 s auto-refresh updates results

APIs
----

- Text MCQ

```bash
curl -X POST http://<server-ip>:8000/api/answer_text \
  -H "Content-Type: application/json" \
  -d '{"question":"What is 2+2?","options":["1","2","3","4"]}'
```

- Image MCQ (with toggles)

```bash
curl -X POST http://<server-ip>:8000/api/answer_image \
  -F image=@/path/to/screenshot.jpg \
  -F multi=false \
  -F remove_watermark=true \
  -F text_first=true
```

- Freeform (no options)

```bash
curl -X POST http://<server-ip>:8000/api/answer_freeform \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the derivative of x^2?"}'
```

By default, this endpoint uses the local text model `qwen2.5-math:7b-instruct`.

Runtime configuration
---------------------

- Get config

```bash
curl http://<server-ip>:8000/config
```

- Update config (examples)

```bash
# Switch to single-model mode
curl -X POST http://<server-ip>:8000/config -H "Content-Type: application/json" -d '{"mode":"single"}'
# Switch back to duo
curl -X POST http://<server-ip>:8000/config -H "Content-Type: application/json" -d '{"mode":"duo"}'
# Force next call to include tie-breaker (one-off)
curl -X POST http://<server-ip>:8000/config -H "Content-Type: application/json" -d '{"force_tiebreaker": true}'
```

Notes:

- Text MCQ requests always use the tie-breaker model only (mode does not affect text path).
- Image MCQ requests use primaries per `mode` (`single` runs the first primary; `duo` runs both). If primaries disagree in `duo`, the tie-breaker runs once.

Warm/unload/status
------------------

```bash
# Preload tie-breaker into memory
curl -X POST http://<server-ip>:8000/warm_math
# Hint unload (eviction happens under memory pressure)
curl -X POST http://<server-ip>:8000/unload_math
# Memory + config status
curl http://<server-ip>:8000/status
```

Performance notes
-----------------

- Actual latency depends on hardware, model quantization, and whether `single` or `duo` primaries are used for images.
- Watermark removal adds preprocessing time but can improve OCR and overall accuracy.
- Text-first (images) can be faster when OCR quality is good, since it uses only the text tie-breaker.

Low-RAM setup (16–18 GB)
------------------------

- Keep mode as single to load only one VLM for images.
- Use only `qwen2.5-vl:7b-instruct` as the primary; avoid `llama3.2-vision:11b-instruct`.
- Keep the tie-breaker `qwen2.5-math:7b-instruct` on-demand (default behavior).
- Set keep-alive to `"0"` so models unload ASAP after calls.
- Prefer Text-first on images when OCR is good to skip VLM in many cases.
- Use lower-ram quantizations (e.g., Q3_K_M or Q4_K_M) for both VLM and math models.

Quick config (while server is running):

```bash
# single-model mode
curl -X POST http://localhost:8000/config -H "Content-Type: application/json" -d '{"mode":"single"}'

# use only qwen2.5-vl as the primary VLM
curl -X POST http://localhost:8000/config -H "Content-Type: application/json" -d '{"primary":["qwen2.5-vl:7b-instruct"]}'

# keep models from lingering in RAM
curl -X POST http://localhost:8000/config -H "Content-Type: application/json" -d '{"keep_alive_primary":"0","keep_alive_tiebreaker":"0"}'
```

Expected usage:

- Image question: ~6.5–9 GB (one VLM) with brief spikes.
- If tie-breaker runs: +~5.5–7 GB momentarily; with light quantization and short contexts this generally stays within 16–18 GB.
- Text questions: only the math model loads (~5.5–7 GB).

Troubleshooting
---------------

- PaddleOCR install: if issues, try `pip install paddlepaddle==2.6.1` (CPU) or switch to Tesseract (edit `app/ocr.py`).
- Ollama models: ensure tags exist locally (`ollama list`). If tags differ, update `app/config.py` accordingly.
- LAN access: allow Uvicorn through Windows Firewall; use your local IP for the phone.

License
-------

Local use with open models; check individual model licenses for redistribution/commercial use.
