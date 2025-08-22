from typing import Dict, List, Literal
from pydantic import BaseModel


class RuntimeConfig(BaseModel):
	# Single model configuration - deepseek-r1:70b-llama-distill-q4_K_M only
	model: str = 'deepseek-r1:70b-llama-distill-q4_K_M'
	keep_alive: str = '0'  # '0' unload asap, or durations like '10m'
	
	# Allow field names starting with 'model_' (e.g., model_name)
	model_config = {
		"protected_namespaces": ()
	}


_config = RuntimeConfig()


def get_config() -> RuntimeConfig:
	return _config


def update_config(new_cfg: Dict) -> RuntimeConfig:
	global _config
	_config = _config.model_copy(update=new_cfg)
	return _config


