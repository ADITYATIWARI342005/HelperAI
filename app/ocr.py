from typing import Optional, Tuple, List
import base64
import io

import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
import cv2


_ocr_singleton: Optional[PaddleOCR] = None


def get_ocr() -> PaddleOCR:
	global _ocr_singleton
	if _ocr_singleton is None:
		_ocr_singleton = PaddleOCR(lang='en', use_angle_cls=True, show_log=False)
	return _ocr_singleton


def decode_base64_image(image_base64: str) -> Image.Image:
	data = base64.b64decode(image_base64)
	return Image.open(io.BytesIO(data)).convert('RGB')


def image_to_text_lines(image_base64: str) -> List[str]:
	image = decode_base64_image(image_base64)
	img = np.array(image)
	ocr = get_ocr()
	result = ocr.ocr(img, cls=True)
	lines: List[str] = []
	for page in result:
		for _box, (text, _conf) in page:
			lines.append(text)
	return lines


def preprocess_remove_watermark(image_base64: str) -> str:
	"""Produce a cleaned image emphasizing dark text and suppressing gray watermarks.

	Returns base64-encoded PNG of a 3-channel image suitable for OCR/VLM.
	"""
	image = decode_base64_image(image_base64)
	rgb = np.array(image)
	gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
	# Illumination normalization
	bg = cv2.GaussianBlur(gray, (41, 41), 0)
	norm = (gray.astype(np.float32) / (bg.astype(np.float32) + 1e-3)) * 128.0
	norm = np.clip(norm, 0, 255).astype(np.uint8)
	# High-pass and edges to emphasize text strokes
	hp = cv2.subtract(norm, cv2.GaussianBlur(norm, (11, 11), 0))
	sx = cv2.Sobel(norm, cv2.CV_32F, 1, 0, ksize=3)
	sy = cv2.Sobel(norm, cv2.CV_32F, 0, 1, ksize=3)
	edges = (sx * sx + sy * sy)
	thr_edge = np.percentile(edges, 75)
	edges_mask = (edges > max(thr_edge, 1.0)).astype(np.uint8) * 255
	# Adaptive threshold favoring dark text
	thr = cv2.adaptiveThreshold(255 - norm, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
								cv2.THRESH_BINARY, 35, 10)
	text_mask = cv2.bitwise_and(thr, edges_mask)
	# Morph cleanup
	k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
	text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_OPEN, k, iterations=1)
	text_mask = cv2.morphologyEx(text_mask, cv2.MORPH_CLOSE, k, iterations=1)
	# Convert to black text on white background
	clean = 255 - text_mask
	clean_rgb = cv2.cvtColor(clean, cv2.COLOR_GRAY2RGB)
	# Encode to base64 PNG
	buf = io.BytesIO()
	Image.fromarray(clean_rgb).save(buf, format='PNG')
	return base64.b64encode(buf.getvalue()).decode('utf-8')


def ocr_quality_score(lines: List[str]) -> int:
	"""Heuristic quality score: favors more lines and longer alphanumeric content."""
	if not lines:
		return 0
	length_sum = sum(len(''.join(ch for ch in ln if ch.isalnum() or ch.isspace())) for ln in lines)
	return len(lines) * 2 + min(length_sum, 2000)


def parse_mcq_from_lines(lines: List[str]) -> Tuple[Optional[str], Optional[List[str]]]:
	if not lines:
		return None, None
	text = " ".join(lines)
	text = " ".join(text.split())

	# Heuristics: split question and options by detecting A./B./C./D. patterns
	# We collect options in order; fallback if fewer than 2 found.
	import re
	pattern = r"\b([A-H])[\).\-:]\s+"
	indices = [(m.group(1), m.start()) for m in re.finditer(pattern, text)]
	if len(indices) < 2:
		return text[:300], None
	# Question is everything before first option marker
	question = text[: indices[0][1]].strip()
	# Extract option spans between markers
	options: List[str] = []
	letters = [idx[0] for idx in indices]
	positions = [idx[1] for idx in indices] + [len(text)]
	for i in range(len(indices)):
		span = text[positions[i]:positions[i+1]].strip()
		# remove leading marker like "A) " if present
		span = re.sub(pattern, "", span, count=1).strip()
		options.append(span)
	# Ensure order by letter
	sorted_pairs = sorted(zip(letters, options), key=lambda x: x[0])
	options = [opt for _ltr, opt in sorted_pairs]
	return question, options


