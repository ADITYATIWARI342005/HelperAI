from typing import Optional, Tuple, List
import base64
import io

import numpy as np
from PIL import Image
from paddleocr import PaddleOCR


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


