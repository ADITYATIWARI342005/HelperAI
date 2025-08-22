import asyncio
import base64
import json
import re
from typing import List, Optional

import httpx

from app.schemas import ModelResponse, MCQResponse, FreeformResponse
from app.config import get_config


OLLAMA_URL = "http://127.0.0.1:11434"


OLLAMA_GEN_OPTIONS = {
	"temperature": 0.2,
	"top_p": 0.9,
	"top_k": 40,
	"repeat_penalty": 1.1,
	"num_predict": 160,
}


def _build_mcq_prompt(question: str, options: List[str]) -> str:
	letters = [chr(ord("A") + i) for i in range(len(options))]
	options_block = "\n".join(f"{letters[i]}. {opt}" for i, opt in enumerate(options))
	return (
		"You are an expert MCQ solver for mathematics, programming, and complex reasoning."
		" Solve carefully and provide a clear explanation.\n\n"
		"Rules:\n"
		"- Consider each option and eliminate clearly wrong ones.\n"
		"- Use definitions, formulas, and quick calculations when needed.\n"
		"- Choose ONLY from the provided options by letter; do not invent options.\n"
		"- Provide a 2-line explanation above your answer.\n"
		"- Below the explanation, show all the steps you took to reach your conclusion.\n\n"
		f"Question: {question}\n\nOptions:\n{options_block}\n\n"
		"Format your response as:\n"
		"EXPLANATION: [2-line explanation]\n"
		"ANSWER: [single letter A, B, C, or D]\n"
		"STEPS: [detailed steps taken to reach conclusion]"
	)


def _build_freeform_prompt(question: str) -> str:
	return (
		"You are an expert problem-solver for mathematics and programming."
		" Think carefully and show your complete thought process.\n\n"
		"Format your response as:\n"
		"EXPLANATION: [2-line explanation]\n"
		"ANSWER: [your final answer]\n"
		"THOUGHT PROCESS: [detailed step-by-step reasoning]"
	)


def _parse_mcq_response(text: str) -> dict:
	"""Parse the structured response from the model"""
	result = {
		"answer": "A",
		"explanation": "",
		"steps": "",
		"confidence": 0.5
	}
	
	# Extract explanation
	expl_match = re.search(r"EXPLANATION:\s*(.+?)(?=\n|$)", text, re.IGNORECASE | re.DOTALL)
	if expl_match:
		result["explanation"] = expl_match.group(1).strip()
	
	# Extract answer
	ans_match = re.search(r"ANSWER:\s*([A-D])", text, re.IGNORECASE)
	if ans_match:
		result["answer"] = ans_match.group(1).upper()
	
	# Extract steps
	steps_match = re.search(r"STEPS:\s*(.+?)(?=\n|$)", text, re.IGNORECASE | re.DOTALL)
	if steps_match:
		result["steps"] = steps_match.group(1).strip()
	
	return result


def _parse_freeform_response(text: str) -> dict:
	"""Parse the structured response from the model for freeform questions"""
	result = {
		"answer": "",
		"explanation": "",
		"thought_process": "",
		"confidence": 0.5
	}
	
	# Extract explanation
	expl_match = re.search(r"EXPLANATION:\s*(.+?)(?=\n|$)", text, re.IGNORECASE | re.DOTALL)
	if expl_match:
		result["explanation"] = expl_match.group(1).strip()
	
	# Extract answer
	ans_match = re.search(r"ANSWER:\s*(.+?)(?=\n|$)", text, re.IGNORECASE | re.DOTALL)
	if ans_match:
		result["answer"] = ans_match.group(1).strip()
	
	# Extract thought process
	thought_match = re.search(r"THOUGHT PROCESS:\s*(.+?)(?=\n|$)", text, re.IGNORECASE | re.DOTALL)
	if thought_match:
		result["thought_process"] = thought_match.group(1).strip()
	
	return result


async def run_mcq_model(question: str, options: List[str], timeout_seconds: float = 30.0) -> ModelResponse:
	"""Run the deepseek-r1:70b-llama-distill-q4_K_M model for MCQ questions"""
	cfg = get_config()
	prompt = _build_mcq_prompt(question, options)
	
	payload = {
		"model": cfg.model, 
		"prompt": prompt, 
		"stream": False, 
		"options": OLLAMA_GEN_OPTIONS, 
		"keep_alive": cfg.keep_alive
	}
	
	async with httpx.AsyncClient(timeout=timeout_seconds) as client:
		resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
		resp.raise_for_status()
		data = resp.json()
		text = data.get("response", "").strip()
		
		parsed = _parse_mcq_response(text)
		
		return ModelResponse(
			model_name=cfg.model,
			answer=parsed["answer"],
			explanation=parsed["explanation"],
			confidence=parsed["confidence"],
			raw_text=text,
		)


async def run_freeform_model(question: str, timeout_seconds: float = 30.0) -> ModelResponse:
	"""Run the deepseek-r1:70b-llama-distill-q4_K_M model for freeform questions"""
	cfg = get_config()
	prompt = _build_freeform_prompt(question)
	
	payload = {
		"model": cfg.model, 
		"prompt": prompt, 
		"stream": False, 
		"options": OLLAMA_GEN_OPTIONS, 
		"keep_alive": cfg.keep_alive
	}
	
	async with httpx.AsyncClient(timeout=timeout_seconds) as client:
		resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
		resp.raise_for_status()
		data = resp.json()
		text = data.get("response", "").strip()
		
		parsed = _parse_freeform_response(text)
		
		return ModelResponse(
			model_name=cfg.model,
			answer=parsed["answer"],
			explanation=parsed["explanation"],
			confidence=parsed["confidence"],
			raw_text=text,
			thought_process=parsed["thought_process"],
		)


async def run_mcq_with_ocr(question: Optional[str], options: Optional[List[str]], timeout_seconds: float = 30.0) -> ModelResponse:
	"""Run MCQ model with OCR-extracted text"""
	# If no question/options from OCR, use defaults
	q = question or "Answer the question from the provided information."
	opts = options or ["Option A", "Option B", "Option C", "Option D"]
	
	return await run_mcq_model(q, opts, timeout_seconds)


