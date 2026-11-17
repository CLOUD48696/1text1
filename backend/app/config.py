from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    app_mode: Literal['demo', 'live'] = 'demo'
    database_url: str = f"sqlite:///{(ROOT / 'panel.db').as_posix()}"
    llm_api_key: str = Field(default='', repr=False)
    llm_base_url: str = 'https://api.deepseek.com'
    llm_model: str = 'deepseek-v4-pro'
    llm_timeout: float = Field(default=45, gt=0)
    llm_concurrency: int = Field(default=4, ge=1, le=16)
    llm_json_mode: bool = True
    llm_thinking: bool = False
    llm_max_tokens: int = Field(default=4096, ge=256, le=16384)
    max_turns: int = Field(default=8, ge=2, le=30)
    max_duration: float = Field(default=600, gt=0)
    max_calls: int = Field(default=180, ge=20)
    demo_delay: float = Field(default=1.3, ge=0, le=10)
    seed_on_start: bool = True

    @model_validator(mode='after')
    def live_config(self):
        if self.app_mode == 'live' and (not self.llm_api_key or not self.llm_model):
            raise ValueError('live 模式需要后端 LLM_API_KEY 和 LLM_MODEL')
        return self
