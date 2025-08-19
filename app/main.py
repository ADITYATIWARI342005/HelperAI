import asyncio
import base64
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
import socket
import qrcode
import psutil

from .schemas import MCQRequest, FreeformRequest
from .models import run_three_models_for_text, run_two_text_plus_vlm, run_freeform_text, run_two_phase
from .aggregator import aggregate_majority
from .config import get_config, update_config
from .ocr import image_to_text_lines, parse_mcq_from_lines, preprocess_remove_watermark, ocr_quality_score


app = FastAPI(title="HelperAI Ensemble MCQ")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>HelperAI MCQ Ensemble</title>
  <style>
    body { font-family: system-ui, Arial, sans-serif; margin: 32px; color: #222; }
    .container { max-width: 920px; margin: 0 auto; }
    h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
    h2 { font-size: 1.1rem; margin-top: 1.5rem; }
    textarea, input[type=text] { width: 100%; padding: 10px; font-size: 1rem; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; }
    .btn { background: #0d6efd; border: none; color: white; padding: 10px 14px; border-radius: 6px; cursor: pointer; }
    .btn:disabled { background: #8fb5ff; }
    .muted { color: #666; font-size: 0.9rem; }
    .result { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-top: 12px; }
  </style>
  <script>
    let ocrTimer = null;
    async function submitText(event) {
      event.preventDefault();
      const q = document.getElementById('question').value;
      const opts = Array.from(document.querySelectorAll('.opt')).map(i => i.value).filter(x => x.trim().length);
      const resBox = document.getElementById('result');
      resBox.textContent = 'Running...';
      const resp = await fetch('/api/answer_text', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question: q, options: opts})});
      const data = await resp.json();
      resBox.textContent = JSON.stringify(data, null, 2);
    }

    async function uploadImage(event) {
      event.preventDefault();
      const file = document.getElementById('image').files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('image', file);
      const resBox = document.getElementById('result');
      resBox.textContent = 'Uploading and running OCR/VLM...';
      const resp = await fetch('/api/answer_image', {method:'POST', body: fd});
      const data = await resp.json();
      resBox.textContent = JSON.stringify(data, null, 2);
    }

    function scheduleOcr() {
      const file = document.getElementById('image').files[0];
      if (!file) return;
      if (ocrTimer) clearTimeout(ocrTimer);
      ocrTimer = setTimeout(() => {
        const fd = new FormData();
        fd.append('image', file);
        fetch('/api/answer_image', {method:'POST', body: fd}).then(r => r.json()).then(data => {
          document.getElementById('result').textContent = JSON.stringify(data, null, 2);
        });
      }, 10000); // 10s delay per requirement
    }

    async function submitFreeform(event) {
      event.preventDefault();
      const q = document.getElementById('freeq').value;
      const out = document.getElementById('freeout');
      out.textContent = 'Running...';
      const resp = await fetch('/api/answer_freeform', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question: q})});
      out.textContent = JSON.stringify(await resp.json(), null, 2);
    }
  </script>
</head>
<body>
  <div class="container">
    <h1>HelperAI MCQ Ensemble</h1>
    <p class="muted">Runs three local models (two text, one VLM) via Ollama. Text input aggregates by majority vote with a two-line explanation. Image input runs OCR + VLM.</p>

    <div class="row">
      <div class="card">
        <h2>Text Input</h2>
        <form onsubmit="submitText(event)">
          <label>Question</label>
          <textarea id="question" rows="4" placeholder="Enter your question..."></textarea>
          <label>Options</label>
          <input class="opt" type="text" placeholder="Option A"/>
          <input class="opt" type="text" placeholder="Option B"/>
          <input class="opt" type="text" placeholder="Option C"/>
          <input class="opt" type="text" placeholder="Option D"/>
          <div style="margin-top:10px;"><button class="btn" type="submit">Get Answer</button></div>
        </form>
      </div>

      <div class="card">
        <h2>Image Input (OCR + VLM)</h2>
        <form onsubmit="uploadImage(event)">
          <input id="image" name="image" type="file" accept="image/*" onchange="scheduleOcr()"/>
          <div style="margin-top:10px;"><button class="btn" type="submit">Upload Now</button></div>
          <p class="muted">If you don't click Upload, we'll auto-run OCR/VLM 10s after selecting an image.</p>
        </form>
      </div>
    </div>

    <div class="card">
      <h2>Result</h2>
      <pre id="result" class="result"></pre>
    </div>
    <div class="card">
      <h2>Freeform Question (no options)</h2>
      <form onsubmit="submitFreeform(event)">
        <textarea id="freeq" rows="3" placeholder="Type your question..."></textarea>
        <div style="margin-top:10px;"><button class="btn" type="submit">Ask</button></div>
      </form>
      <pre id="freeout" class="result"></pre>
    </div>
  </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
	return INDEX_HTML


@app.post("/api/answer_text")
async def answer_text(req: MCQRequest):
	responses = await run_two_phase(req.question, req.options, None)
	agg = aggregate_majority(responses)
	return JSONResponse(agg.dict())


@app.post("/api/answer_image")
async def answer_image(image: UploadFile = File(...), multi: Optional[bool] = Form(False), remove_watermark: Optional[bool] = Form(False), text_first: Optional[bool] = Form(False)):
	data = await image.read()
	image_b64 = base64.b64encode(data).decode("utf-8")
	if remove_watermark:
		try:
			image_b64 = preprocess_remove_watermark(image_b64)
		except Exception:
			pass
	lines = image_to_text_lines(image_b64)
	question, options = parse_mcq_from_lines(lines)
	# Text-first path for clean text screenshots
	if text_first:
		quality = ocr_quality_score(lines)
		enough_options = bool(options and len(options) >= 2)
		if quality >= 40 and enough_options:
			responses = await run_two_phase(question, options, None, allow_multi=bool(multi))
		else:
			responses = await run_two_phase(question, options, image_b64, allow_multi=bool(multi))
	else:
		responses = await run_two_phase(question, options, image_b64, allow_multi=bool(multi))
	from .aggregator import aggregate_majority_multi
	agg = aggregate_majority_multi(responses) if multi else aggregate_majority(responses)
	return JSONResponse({
		"question": question,
		"options": options,
		"result": agg.dict(),
	})


@app.post("/api/answer_freeform")
async def answer_freeform(req: FreeformRequest):
	# Use a single preloaded local model (qwen2:7b by default)
	resp = await run_freeform_text("qwen2:7b", req.question)
	return JSONResponse({
		"final_answer": resp.answer,
		"explanation": resp.explanation,
		"confidence": resp.confidence,
		"model": resp.model_name,
	})


@app.get("/config")
async def get_runtime_config():
	cfg = get_config()
	return JSONResponse(cfg.model_dump())


@app.post("/config")
async def update_runtime_config(body: dict = Body(...)):
	cfg = update_config(body)
	return JSONResponse(cfg.model_dump())


@app.get("/status")
async def status():
	vm = psutil.virtual_memory()
	return JSONResponse({
		"memory": {
			"total_gb": round(vm.total / (1024**3), 2),
			"used_gb": round(vm.used / (1024**3), 2),
			"available_gb": round(vm.available / (1024**3), 2),
			"percent": vm.percent,
		},
		"config": get_config().model_dump(),
	})


@app.post("/warm_math")
async def warm_math():
	# Do a tiny prompt to ensure model is loaded into memory
	try:
		from .models import run_text_model
		_ = await run_text_model(get_config().tiebreaker, "Warmup: choose A", ["A","B"])  # ignore result
		return JSONResponse({"status": "ok", "message": "math warmed"})
	except Exception as e:
		return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/unload_math")
async def unload_math():
	# Ollama has no explicit unload; hint GC by switching context. We return ack.
	return JSONResponse({"status": "ok", "message": "request acknowledged (llama.cpp will evict on memory pressure)"})


MOBILE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\"/>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
  <title>HelperAI Mobile Upload</title>
  <style>
    body { font-family: system-ui, Arial, sans-serif; margin: 20px; color: #222; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 14px; }
    .btn { background: #0d6efd; color: white; border: none; padding: 10px 14px; border-radius: 8px; }
    pre { background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; }
    .row { display:flex; gap:10px; align-items:center; }
    .opts { margin-top: 10px; }
    .opt { padding: 8px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom:6px; }
    .opt.correct { background: #e6ffe6; border-color: #22c55e; }
    .muted { color:#666; font-size: 0.9rem; }
  </style>
  <script>
    let lastFile = null;
    let refreshTimer = null;

    function letters(n){ return Array.from({length:n}, (_,i)=>String.fromCharCode(65+i)); }

    function renderParsed(q, opts){
      document.getElementById('parsedq').textContent = q || '';
      const cont = document.getElementById('opts');
      cont.innerHTML = '';
      if (!opts || !opts.length) return;
      const ls = letters(opts.length);
      opts.forEach((t, i)=>{
        const div = document.createElement('div');
        div.className = 'opt';
        div.id = 'opt_'+ls[i];
        div.textContent = ls[i]+'. '+t;
        cont.appendChild(div);
      });
    }

    function markCorrect(finalCombo){
      const parts = String(finalCombo||'').replace(/\s+/g,'').split('+').filter(Boolean);
      document.querySelectorAll('.opt').forEach(el=>el.classList.remove('correct'));
      parts.forEach(p=>{
        const el = document.getElementById('opt_'+p);
        if (el) el.classList.add('correct');
      });
    }

    async function sendImage(evt) {
      if (evt) evt.preventDefault();
      const file = document.getElementById('img').files[0] || lastFile;
      if (!file) { alert('Pick an image'); return; }
      lastFile = file;
      const fd = new FormData();
      fd.append('image', file);
      const multi = document.getElementById('multi').checked;
      const rmwm = document.getElementById('rmwm') ? document.getElementById('rmwm').checked : false;
      const txtfirst = document.getElementById('txtfirst') ? document.getElementById('txtfirst').checked : false;
      fd.append('multi', multi ? 'true' : 'false');
      fd.append('remove_watermark', rmwm ? 'true' : 'false');
      fd.append('text_first', txtfirst ? 'true' : 'false');
      const out = document.getElementById('out');
      const explain = document.getElementById('explain');
      out.textContent = 'Thinking...';
      explain.textContent = '';
      const resp = await fetch('/api/answer_image', { method: 'POST', body: fd });
      const data = await resp.json();
      // Autofill parsed
      renderParsed(data.question, data.options);
      // Mark correct
      const result = data.result || {};
      markCorrect(result.final_answer || '');
      // Show explanation
      explain.textContent = result.explanation || '';
      out.textContent = JSON.stringify(data, null, 2);
    }

    function startAutoRefresh(){
      if (refreshTimer) clearInterval(refreshTimer);
      refreshTimer = setInterval(()=>{
        if (lastFile) {
          sendImage(null);
        }
      }, 15000);
    }
  </script>
</head>
<body>
  <div class=\"card\">
    <h2>Upload MCQ Screenshot</h2>
    <div class=\"row\">
      <input id=\"img\" type=\"file\" accept=\"image/*\" capture=\"environment\" />
      <label class=\"row\"><input id=\"multi\" type=\"checkbox\"/> Multiple correct</label>
      <label class=\"row\"><input id=\"rmwm\" type=\"checkbox\"/> Remove watermark</label>
      <label class=\"row\"><input id=\"txtfirst\" type=\"checkbox\"/> Text-first</label>
      <button class=\"btn\" onclick=\"sendImage(event)\">Submit</button>
      <button class=\"btn\" onclick=\"startAutoRefresh()\">Auto-refresh 15s</button>
    </div>
    <div class=\"muted\">Parsed question (from OCR):</div>
    <div id=\"parsedq\" class=\"opt\"></div>
    <div class=\"muted\" style=\"margin-top:8px;\">Options:</div>
    <div id=\"opts\" class=\"opts\"></div>
    <div class=\"muted\" style=\"margin-top:8px;\">Explanation:</div>
    <div id=\"explain\" class=\"opt\"></div>
    <h3>Raw Result</h3>
    <pre id=\"out\"></pre>
  </div>
</body>
</html>
"""


def _get_local_ip() -> str:
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.connect(("8.8.8.8", 80))
		ip = s.getsockname()[0]
	except Exception:
		ip = "127.0.0.1"
	finally:
		s.close()
	return ip


@app.get("/mobile", response_class=HTMLResponse)
async def mobile() -> str:
	return MOBILE_HTML


@app.get("/qr")
async def qr() -> Response:
	ip = _get_local_ip()
	url = f"http://{ip}:8000/mobile"
	img = qrcode.make(url)
	import io
	buf = io.BytesIO()
	img.save(buf, format='PNG')
	return Response(buf.getvalue(), media_type='image/png')


