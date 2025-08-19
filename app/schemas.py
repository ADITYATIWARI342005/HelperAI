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


class EnsembleResponse(BaseModel):
	final_answer: str
	explanation: str
	votes: Dict[str, int]
	per_model: List[ModelResponse]

