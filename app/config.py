from typing import Dict, List, Literal
from pydantic import BaseModel


ModelType = Literal['text', 'vlm']


class RuntimeConfig(BaseModel):
	mode: Literal['single', 'duo'] = 'single'
	primary: List[str] = ['qwen2.5-vl:7b-instruct', 'llama3.2-vision:11b-instruct']
	tiebreaker: str = 'qwen2.5-math:7b-instruct'
	force_tiebreaker: bool = False
	keep_alive_primary: str = '0'        # '0' unload asap, or durations like '10m'
	keep_alive_tiebreaker: str = '0'
	model_types: Dict[str, ModelType] = {
		'qwen2.5-vl:7b-instruct': 'vlm',
		'llama3.2-vision:11b-instruct': 'vlm',
		'qwen2.5-math:7b-instruct': 'text',
	}


_config = RuntimeConfig()


def get_config() -> RuntimeConfig:
	return _config


def update_config(new_cfg: Dict) -> RuntimeConfig:
	global _config
	_config = _config.model_copy(update=new_cfg)
	return _config


