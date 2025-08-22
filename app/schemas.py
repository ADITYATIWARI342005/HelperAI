from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class MCQRequest(BaseModel):
	question: str = Field(..., description="Question text")
	options: List[str] = Field(
		..., min_length=2, max_length=12, description="List of answer options in order (A, B, C, ...)."
	)


class FreeformRequest(BaseModel):
	question: str = Field(..., description="Question text without options")


class ModelResponse(BaseModel):
	model_name: str
	answer: str
	explanation: str
	confidence: float = 0.5
	raw_text: Optional[str] = None
	thought_process: Optional[str] = None  # For freeform questions

	# Allow field names starting with 'model_' (e.g., model_name)
	model_config = {
		"protected_namespaces": ()
	}


class MCQResponse(BaseModel):
	final_answer: str
	explanation: str
	confidence: float
	model: str
	per_model: List[ModelResponse]


class FreeformResponse(BaseModel):
	final_answer: str
	explanation: str
	thought_process: str
	confidence: float
	model: str

