HelperAI MCQ Ensemble (Local, LAN-accessible)
=============================================

A FastAPI web app that answers multiple-choice questions using multiple local AI models. It supports:

- Text MCQs (English) with 2–12 options
- Image MCQs via OCR + a vision-language model (VLM)
- Majority vote across models with a concise two-line explanation
- Desktop UI and a mobile-friendly upload page over your local network (LAN)
- Optional auto-run after 10 seconds for image inputs

This project runs fully offline after models are downloaded (via Ollama).

Features
--------

- 3-model ensemble:
  - Text route: Qwen2, Llama 3, Mistral (default; can be changed)
  - Image route: two text models + one VLM (LLaVA)
- Majority vote aggregation with two-line explanation
- OCR via PaddleOCR for parsing text from images
- Mobile upload page at `/mobile` and QR shortcut at `/qr`
- JSON APIs for automation
- Freeform mode (no options) via `/api/answer_freeform`
- Runtime configuration endpoints (`/config`, `/status`, `/warm_math`, `/unload_math`)

Models (current defaults)
-------------------------

- Primary duo (Phase 1): `qwen2.5-vl:7b-instruct`, `llama3.2-vision:11b-instruct`
- Tie-breaker (Phase 2): `qwen2.5-math:7b-instruct`

Notes:
- Recommended quantizations (RAM-friendly CPU): Qwen2.5‑VL 7B Q4_K_M (~5 GB), Llama 3.2 Vision 11B Q3_K_M (~5 GB), Qwen2.5‑Math 7B Q4_K_M (~7 GB)
- Peak RAM fits within ~17–18 GB when tie-breaker is warmed; normal steady state ~10 GB (Phase 1 duo loaded)

Requirements
------------

- Windows 10/11 (tested), Python 3.10+
- Ollama installed and running (`http://127.0.0.1:11434`)
- CPU-only works; GPU (if available) will accelerate

Installation
------------

1) Clone and enter the repo
```powershell
cd HelperAI
```

2) Install and pull models (Ollama)
```powershell
ollama pull qwen2:7b
ollama pull llama3:8b
ollama pull mistral:7b
ollama pull llava:7b
```

3) Create a virtual environment and install Python deps
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

Usage
-----

### Desktop UI
- Text MCQ: enter question and options (2–12). Click “Get Answer”.
- Image MCQ: select an image. If you don’t click Upload, the app auto-runs OCR+VLM after 10 seconds.

### Freeform (no options)
- In the desktop UI, use the "Freeform Question (no options)" section to ask a question without options. A local model returns a short answer and two-line explanation.

### Mobile UI
- Visit `/mobile` on your phone (same Wi‑Fi), pick an image, tap Submit. The result shows parsed question/options (if OCR succeeds) and the final result.

### APIs
- Text MCQ
```bash
curl -X POST http://<server-ip>:8000/api/answer_text \
  -H "Content-Type: application/json" \
  -d '{"question":"What is 2+2?","options":["1","2","3","4"]}'
```
Response shape:
```json
{
  "final_answer": "D",
  "explanation": "Two short lines...",
  "votes": {"A":0, "B":0, "C":0, "D":3},
  "per_model": [
    {"model_name":"qwen2:7b","answer":"D","explanation":"...","confidence":0.8},
    {"model_name":"llama3:8b","answer":"D","explanation":"...","confidence":0.7},
    {"model_name":"mistral:7b","answer":"D","explanation":"...","confidence":0.6}
  ]
}
```

- Freeform (no options)
```bash
curl -X POST http://<server-ip>:8000/api/answer_freeform \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the derivative of x^2?"}'
```
Response shape:
```json
{
  "final_answer": "2x",
  "explanation": "Short two-line rationale...",
  "confidence": 0.78,
  "model": "qwen2:7b"
}
```

Runtime configuration
---------------------

- Get current config
```bash
curl http://<server-ip>:8000/config
```
- Update config (examples)
```bash
# Switch to single-model mode (first primary only)
curl -X POST http://<server-ip>:8000/config \
  -H "Content-Type: application/json" \
  -d '{"mode":"single"}'

# Switch back to duo
curl -X POST http://<server-ip>:8000/config \
  -H "Content-Type: application/json" \
  -d '{"mode":"duo"}'

# Swap primary order
curl -s http://<server-ip>:8000/config | jq '.primary | reverse as $p | {primary:$p}' \
| curl -X POST http://<server-ip>:8000/config -H "Content-Type: application/json" -d @-

# Force next call to include tie-breaker (one-off)
curl -X POST http://<server-ip>:8000/config \
  -H "Content-Type: application/json" \
  -d '{"force_tiebreaker": true}'
```

Warm/unload/status
------------------

```bash
# Preload tie-breaker into memory
curl -X POST http://<server-ip>:8000/warm_math

# Hint unload (actual eviction occurs under memory pressure)
curl -X POST http://<server-ip>:8000/unload_math

# Memory + config status
curl http://<server-ip>:8000/status
```

- Image MCQ
```bash
curl -X POST http://<server-ip>:8000/api/answer_image -F image=@/path/to/screenshot.jpg
```
Response shape:
```json
{
  "question": "Parsed question (if OCR succeeds)",
  "options": ["A text","B text","C text","D text"],
  "result": { "final_answer":"B", "explanation":"...", "votes":{...}, "per_model":[...] }
}
```

Notes & Tips
------------

- CPU-only performance is fine for short MCQs. Larger models or images take longer.
- If PaddleOCR install fails on Windows, you can switch to Tesseract:
  - Install Tesseract and `pip install pytesseract`
  - Replace the OCR implementation in `app/ocr.py` accordingly
- To change models, edit model tags in `app/models.py` where defaults are listed, or extend the app to read from a config.

License
-------

Local use with open models; check individual model licenses for redistribution/commercial use.


