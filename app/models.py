from pydantic import BaseModel
from typing import Optional


class GenerateRequest(BaseModel):
    prompt: str
    model: str
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Расскажи краткую историю про кота",
                "model": "deepseek/deepseek-chat-v3.1:free",
                "max_tokens": 512,
                "stream": False,
            }
        }


class GenerateResponse(BaseModel):
    response: str
    tokens_used: int = 0
    latency_seconds: float


class BenchmarkResponse(BaseModel):
    model: str
    runs: int
    total_prompts: int
    latency_stats: dict
    tokens_stats: dict
    results_file: str
    html_table: Optional[str] = None
