import time
import json
import asyncio
from typing import AsyncGenerator, Tuple
import requests
from fastapi import HTTPException

from .config import setup_logging, get_openrouter_api_key

logger = setup_logging()


async def make_openrouter_request_with_retry(
    prompt: str, model: str, max_tokens: int = 256, stream: bool = False
) -> Tuple[requests.Response, float]:
    """Отправка запроса в OpenRouter с повторными попытками при ошибках."""
    key = get_openrouter_api_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "FastAPI OpenRouter Proxy",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": stream,
    }

    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries + 1):
        start_time = time.time()

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
                stream=stream,
            )

            end_time = time.time()
            latency = end_time - start_time

            if response.status_code == 200:
                return response, latency

            if response.status_code == 429:
                if attempt < max_retries:
                    delay = base_delay * (2**attempt)
                    logger.warning(f"Rate limit (429). Retry after {delay}s")
                    await asyncio.sleep(delay)
                    continue
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded after {max_retries+1} attempts.",
                )

            if 500 <= response.status_code <= 599 and attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(f"Server error {response.status_code}, retry")
                await asyncio.sleep(delay)
                continue

            raise HTTPException(status_code=response.status_code, detail=response.text)

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning("Timeout, retry")
                await asyncio.sleep(delay)
                continue
            logger.error("Timeout after retries", exc_info=True)
            raise HTTPException(status_code=408, detail="Request timeout after retries")

        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(f"Network error, retry: {str(e)}")
                await asyncio.sleep(delay)
                continue
            logger.error("Network error after retries", exc_info=True)
            raise HTTPException(status_code=503, detail="Network error after retries")

    raise HTTPException(status_code=500, detail="Unexpected error in retry logic")


async def stream_generator(response) -> AsyncGenerator[str, None]:
    try:
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield f"data: {json.dumps({'content': content})}\n\n"
                    except json.JSONDecodeError:
                        continue

        yield f"data: {json.dumps({'done': True})}\n\n"
    except Exception as e:
        logger.error(f"stream_generator error: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
