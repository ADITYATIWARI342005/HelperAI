import asyncio
import base64
import json
import re
from typing import List, Optional

import httpx

from .schemas import ModelResponse
from .config import get_config, update_config


OLLAMA_URL = "http://127.0.0.1:11434"


OLLAMA_GEN_OPTIONS = {
	"temperature": 0.2,
	"top_p": 0.9,
	"top_k": 40,
	"repeat_penalty": 1.1,
	"num_predict": 160,
}


def _build_text_prompt(question: str, options: List[str], allow_multi: bool = False) -> str:
	letters = [chr(ord("A") + i) for i in range(len(options))]
	options_block = "\n".join(f"{letters[i]}. {opt}" for i, opt in enumerate(options))
	selection_rule = (
		"If multiple answers are correct, return all correct letters joined by '+' (e.g., 'A+C'); otherwise return a single letter."
		if allow_multi
		else "Return exactly one letter."
	)
	return (
		"You are an expert MCQ solver for mathematics, programming, and complex reasoning."
		" Solve carefully but reply ONLY with a strict JSON object. Reason internally and do not reveal steps.\n"
		f"{selection_rule}\n"
		"Rules:\n"
		"- Consider each option and eliminate clearly wrong ones.\n"
		"- Use definitions, formulas, and quick calculations when needed.\n"
		"- Choose ONLY from the provided options by letter; do not invent options.\n"
		"- Calibrate confidence between 0 and 1 (higher = more certain).\n\n"
		f"Question: {question}\n\nOptions:\n{options_block}\n\n"
		"Return exactly one line of JSON with keys: answer, explanation, confidence."
	)


def _build_vlm_prompt(question: Optional[str], options: Optional[List[str]], allow_multi: bool = False) -> str:
	selection_rule = (
		"If multiple answers are correct, return all correct letters joined by '+' (e.g., 'A+C'); otherwise return a single letter."
		if allow_multi
		else "Return exactly one letter."
	)
	base = (
		"You are a vision-language expert for MCQs. Reply ONLY with a strict JSON object."
		" Reason internally; do not reveal steps.\n"
		"Ignore logos/watermarks; focus on dark, high-contrast text and highlighted areas.\n"
		f"{selection_rule}\n"
		"Return keys: answer, explanation (2 short lines), confidence (0-1)."
	)
	if question and options:
		letters = [chr(ord("A") + i) for i in range(len(options))]
		options_block = "\n".join(f"{letters[i]}. {opt}" for i, opt in enumerate(options))
		return (
			base
			+ "\nIf the text below conflicts with the image, prefer the image.\n"
			+ f"Question (if visible): {question}\nOptions:\n{options_block}\n"
			+ "Choose ONLY from the provided options by letter."
		)
	return base + " If options are visible in the image, choose by letter."


def _parse_json_from_text(text: str) -> Optional[dict]:
	try:
		# Try direct JSON first
		return json.loads(text)
	except Exception:
		pass
	# Fallback: extract the first JSON object-like segment
	match = re.search(r"\{[\s\S]*\}", text)
	if match:
		segment = match.group(0)
		try:
			return json.loads(segment)
		except Exception:
			return None
	return None


def _normalize_answer_letter(letter: str, num_options: int) -> str:
	if not letter:
		return "A"
	letter = str(letter).strip().upper()
	# Accept forms like "(A)", "A.", "A)"
	letter = re.sub(r"[^A-Z]", "", letter)
	if not letter:
		return "A"
	letter = letter[0]
	max_letter = chr(ord("A") + max(0, num_options - 1))
	if letter > max_letter:
		return "A"
	return letter


def _normalize_answer_multi_string(value, num_options: int) -> str:
	# Accept list or string with separators, return canonical 'A+C+E' (sorted unique)
	if isinstance(value, list):
		candidates = [str(v) for v in value]
	else:
		candidates = re.split(r"[,+/\\| ]+", str(value))
	letters: List[str] = []
	for v in candidates:
		v = v.strip()
		if not v:
			continue
		letters.append(_normalize_answer_letter(v, num_options))
	uniq_sorted = sorted(set(letters))
	return "+".join(uniq_sorted) if uniq_sorted else "A"


async def run_text_model(
	model: str,
	question: str,
	options: List[str],
	allow_multi: bool = False,
	timeout_seconds: float = 30.0,
) -> ModelResponse:
	prompt = _build_text_prompt(question, options, allow_multi=allow_multi)
	payload = {"model": model, "prompt": prompt, "stream": False, "options": OLLAMA_GEN_OPTIONS}
	async with httpx.AsyncClient(timeout=timeout_seconds) as client:
		resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
		resp.raise_for_status()
		data = resp.json()
		text = data.get("response", "").strip()
		parsed = _parse_json_from_text(text) or {}
		if allow_multi:
			answer = _normalize_answer_multi_string(parsed.get("answer", ""), len(options))
		else:
			answer = _normalize_answer_letter(parsed.get("answer", ""), len(options))
		explanation = str(parsed.get("explanation", "")).strip() or text[:400]
		try:
			confidence = float(parsed.get("confidence", 0.5))
		except Exception:
			confidence = 0.5
		confidence = max(0.0, min(1.0, confidence))
		return ModelResponse(
			model_name=model,
			answer=answer,
			explanation=explanation,
			confidence=confidence,
			raw_text=text,
		)


async def run_freeform_text(
	model: str,
	question: str,
	timeout_seconds: float = 30.0,
) -> ModelResponse:
	prompt = (
		"You are an expert problem-solver for mathematics and programming."
		" Think carefully but reply ONLY with a strict JSON object.\n"
		"Return keys: answer (short text), explanation (2 short lines), confidence (0-1).\n\n"
		f"Question: {question}\n"
	)
	payload = {"model": model, "prompt": prompt, "stream": False, "options": OLLAMA_GEN_OPTIONS}
	async with httpx.AsyncClient(timeout=timeout_seconds) as client:
		resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
		resp.raise_for_status()
		data = resp.json()
		text = data.get("response", "").strip()
		parsed = _parse_json_from_text(text) or {}
		answer = str(parsed.get("answer", "")).strip() or text[:200]
		explanation = str(parsed.get("explanation", "")).strip() or text[:400]
		try:
			confidence = float(parsed.get("confidence", 0.5))
		except Exception:
			confidence = 0.5
		confidence = max(0.0, min(1.0, confidence))
		return ModelResponse(
			model_name=model,
			answer=answer,
			explanation=explanation,
			confidence=confidence,
			raw_text=text,
		)


async def run_vlm_model(
	model: str,
	image_base64: str,
	question: Optional[str],
	options: Optional[List[str]],
	allow_multi: bool = False,
	timeout_seconds: float = 45.0,
) -> ModelResponse:
	prompt = _build_vlm_prompt(question, options, allow_multi=allow_multi)
	payload = {
		"model": model,
		"prompt": prompt,
		"images": [image_base64],
		"stream": False,
		"options": OLLAMA_GEN_OPTIONS,
	}
	async with httpx.AsyncClient(timeout=timeout_seconds) as client:
		resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
		resp.raise_for_status()
		data = resp.json()
		text = data.get("response", "").strip()
		parsed = _parse_json_from_text(text) or {}
		num_opts = len(options) if options else 4
		if allow_multi:
			answer = _normalize_answer_multi_string(parsed.get("answer", ""), num_opts)
		else:
			answer = _normalize_answer_letter(parsed.get("answer", ""), num_opts)
		explanation = str(parsed.get("explanation", "")).strip() or text[:400]
		try:
			confidence = float(parsed.get("confidence", 0.5))
		except Exception:
			confidence = 0.5
		confidence = max(0.0, min(1.0, confidence))
		return ModelResponse(
			model_name=model,
			answer=answer,
			explanation=explanation,
			confidence=confidence,
			raw_text=text,
		)


async def run_three_models_for_text(question: str, options: List[str]) -> List[ModelResponse]:
	models = ["qwen2:7b", "llama3:8b", "mistral:7b"]
	tasks = [run_text_model(m, question, options) for m in models]
	results = await asyncio.gather(*tasks, return_exceptions=True)
	out: List[ModelResponse] = []
	for i, r in enumerate(results):
		if isinstance(r, Exception):
			out.append(
				ModelResponse(
					model_name=models[i],
					answer="A",
					explanation=f"Model error: {type(r).__name__}",
					confidence=0.33,
					raw_text=str(r),
				)
			)
		else:
			out.append(r)
	return out


async def run_two_text_plus_vlm(
	image_base64: str,
	question: Optional[str],
	options: Optional[List[str]],
) -> List[ModelResponse]:
	text_models = ["qwen2:7b", "llama3:8b"]
	vlm_model = "llava:latest"
	text_tasks = []
	if question and options:
		for m in text_models:
			text_tasks.append(run_text_model(m, question, options))
	else:
		# If OCR fails, still run text models with generic options to keep 3 votes
		fallback_options = ["Option A", "Option B", "Option C", "Option D"]
		for m in text_models:
			text_tasks.append(run_text_model(m, "Answer the question in the image.", fallback_options))
	vlm_task = run_vlm_model(vlm_model, image_base64, question, options)
	results = await asyncio.gather(*text_tasks, vlm_task, return_exceptions=True)
	out: List[ModelResponse] = []
	for i, r in enumerate(results):
		if isinstance(r, Exception):
			name = text_models[i] if i < len(text_models) else vlm_model
			out.append(
				ModelResponse(
					model_name=name,
					answer="A",
					explanation=f"Model error: {type(r).__name__}",
					confidence=0.33,
					raw_text=str(r),
				)
			)
		else:
			out.append(r)
	return out


async def _run_primary_model(tag: str, question: Optional[str], options: Optional[List[str]], image_base64: Optional[str], allow_multi: bool) -> ModelResponse:
	cfg = get_config()
	is_vlm = cfg.model_types.get(tag, 'text') == 'vlm'
	if is_vlm and image_base64 is not None:
		return await run_vlm_model(tag, image_base64, question, options, allow_multi=allow_multi)
	# Fallback to text prompt
	q = question or "Answer the question from the provided information."
	opts = options or ["Option A", "Option B", "Option C", "Option D"]
	return await run_text_model(tag, q, opts, allow_multi=allow_multi)


async def run_two_phase(
	question: Optional[str],
	options: Optional[List[str]],
	image_base64: Optional[str] = None,
	allow_multi: bool = False,
) -> List[ModelResponse]:
	"""Run primary duo (or single) first; if they disagree or force flag set, run tie-breaker."""
	cfg = get_config()
	# Optimization: if no image is provided (text-only path), use the math/text model as primary
	if image_base64 is None:
		selected = [cfg.tiebreaker]
	else:
		selected = cfg.primary[:1] if cfg.mode == 'single' else cfg.primary[:2]
	results: List[ModelResponse] = []
	# Run primary in parallel
	primary_tasks = [
		_run_primary_model(tag, question, options, image_base64, allow_multi) for tag in selected
	]
	primary_results = await asyncio.gather(*primary_tasks, return_exceptions=True)
	for i, r in enumerate(primary_results):
		if isinstance(r, Exception):
			results.append(
				ModelResponse(
					model_name=selected[i],
					answer="A",
					explanation=f"Model error: {type(r).__name__}",
					confidence=0.33,
					raw_text=str(r),
				)
			)
		else:
			results.append(r)

	# Decide if tiebreaker needed
	need_tiebreak = False
	if cfg.mode == 'duo' and len(results) >= 2:
		need_tiebreak = results[0].answer != results[1].answer
	if cfg.mode == 'single':
		need_tiebreak = False
	# Force override (one-off)
	if getattr(cfg, 'force_tiebreaker', False):
		need_tiebreak = True
		try:
			update_config({"force_tiebreaker": False})
		except Exception:
			pass

	if need_tiebreak:
		q = question or "Answer the question from the provided information."
		opts = options or ["Option A", "Option B", "Option C", "Option D"]
		try:
			breaker_res = await run_text_model(cfg.tiebreaker, q, opts, allow_multi=allow_multi)
			results.append(breaker_res)
		except Exception as e:
			results.append(
				ModelResponse(
					model_name=cfg.tiebreaker,
					answer="A",
					explanation=f"Model error: {type(e).__name__}",
					confidence=0.33,
					raw_text=str(e),
				)
			)

	return results


