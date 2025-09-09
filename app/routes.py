from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from datetime import datetime
import statistics

from .config import setup_logging, AVAILABLE_MODELS
from .models import GenerateRequest, GenerateResponse, BenchmarkResponse
from .openrouter import make_openrouter_request_with_retry, stream_generator
from .utils import create_benchmark_html_table, save_results_csv

logger = setup_logging()

app_openrouter = FastAPI(title="OpenRouter API Proxy", version="1.0.0")


@app_openrouter.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработчик непойманных исключений — логирует ошибку и возвращает 500."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app_openrouter.get("/models")
async def get_models():
    """Возвращает список доступных моделей."""
    return {"models": AVAILABLE_MODELS}


@app_openrouter.post("/generate")
async def generate_text(request: GenerateRequest):
    """Генерация ответа: проксирует запрос в OpenRouter и возвращает результат."""
    if request.model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail="Model not supported")

    response, latency = await make_openrouter_request_with_retry(
        request.prompt, request.model, request.max_tokens, request.stream
    )

    if request.stream:
        return StreamingResponse(
            stream_generator(response), media_type="text/event-stream"
        )

    data = response.json()
    if "choices" not in data or not data["choices"]:
        raise HTTPException(status_code=500, detail="Invalid response from OpenRouter")

    generated_text = data["choices"][0]["message"]["content"]
    tokens_used = data.get("usage", {}).get("total_tokens", 0)

    return GenerateResponse(
        response=generated_text,
        tokens_used=tokens_used,
        latency_seconds=round(latency, 3),
    )


@app_openrouter.post("/benchmark")
async def benchmark_model(
    prompt_file: UploadFile = File(...),
    model: str = Form("deepseek/deepseek-chat-v3.1:free"),
    runs: int = Form(5),
    visualize: bool = Form(False),
):
    """Проводит бенчмарк модели по файлу промптов; сохраняет CSV и опционально возвращает HTML."""
    if model not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail="Model not supported")

    content = await prompt_file.read()
    try:
        prompts_text = content.decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="File must be UTF-8")

    prompts = [l.strip() for l in prompts_text.split("\n") if l.strip()]
    if not prompts:
        raise HTTPException(status_code=400, detail="No prompts provided")

    all_results = []
    latencies = []
    token_counts = []

    for run_id in range(runs):
        for prompt_id, prompt in enumerate(prompts):
            try:
                response, latency = await make_openrouter_request_with_retry(
                    prompt, model
                )
                data = response.json()
                generated_text = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)

                r = {
                    "run_id": run_id + 1,
                    "prompt_id": prompt_id + 1,
                    "prompt": prompt[:100] + ("..." if len(prompt) > 100 else ""),
                    "response": generated_text[:100]
                    + ("..." if len(generated_text) > 100 else ""),
                    "model": model,
                    "latency_seconds": round(latency, 3),
                    "tokens_used": tokens_used,
                    "response_length": len(generated_text),
                    "timestamp": datetime.now().isoformat(),
                }
                all_results.append(r)
                latencies.append(latency)
                token_counts.append(tokens_used)
            except Exception as e:
                logger.error(f"Error during benchmark request: {e}", exc_info=True)
                continue

    if not latencies:
        raise HTTPException(status_code=500, detail="No successful requests")

    latency_stats = {
        "avg": round(statistics.mean(latencies), 3),
        "min": round(min(latencies), 3),
        "max": round(max(latencies), 3),
        "std_dev": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 3),
        "total": round(sum(latencies), 3),
    }
    tokens_stats = {
        "avg": round(statistics.mean(token_counts), 1),
        "min": min(token_counts),
        "max": max(token_counts),
        "std_dev": round(
            statistics.stdev(token_counts) if len(token_counts) > 1 else 0, 1
        ),
    }

    csv_filename = "benchmark_results.csv"
    save_results_csv(all_results, csv_filename)

    html_table = None
    if visualize:
        html_table = create_benchmark_html_table(
            all_results, latency_stats, tokens_stats, model, runs
        )
        return HTMLResponse(content=html_table)

    return BenchmarkResponse(
        model=model,
        runs=runs,
        total_prompts=len(prompts),
        latency_stats=latency_stats,
        tokens_stats=tokens_stats,
        results_file=csv_filename,
        html_table=html_table,
    )


@app_openrouter.get("/")
async def root():
    return {"message": "FastAPI OpenRouter Proxy is working", "version": "1.0.0"}
