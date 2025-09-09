# FastAPI OpenRouter Proxy & LLM Benchmark

**Примеры и тесты: https://docs.google.com/document/d/1Up_bVBHPZvmjmNTlRokCh74ZPS67OOv7VQPPjypkW-Q/edit?usp=sharing**

Лёгкий прокси к OpenRouter с простыми API для генерации текста и бенчмарка моделей (серии запросов с сохранением результатов в CSV и опциональной визуализацией в HTML).



## Краткое описание

Проект предоставляет HTTP API на FastAPI, которое отправляет запросы в OpenRouter, собирает метрики (латентность, количество токенов, длину ответа) и умеет выполнять пакетные измерения (benchmark). Результаты сохраняются в `benchmark_results.csv`. Логи сервера пишутся в `server_logs.txt`.

Ключевые файлы:
- `main.py` — точка входа (uvicorn)
- `app/routes.py` — маршруты FastAPI (`/`, `/models`, `/generate`, `/benchmark`)
- `app/openrouter.py` — логика запросов к OpenRouter, повторы и стриминг
- `app/config.py` — конфигурация и список доступных моделей
- `app/utils.py` — сохранение CSV и генерация HTML таблицы

## Требования

- Python 3.12+
- Зависимости описаны в `pyproject.toml` (проект использует Poetry). Основные: `fastapi`, `requests`, `python-dotenv`, `pydantic`.

## Установка

Рекомендуемый способ — через Poetry:

```powershell
poetry install
```

Если не используете Poetry, создайте виртуальное окружение и установите зависимости вручную по `pyproject.toml` или добавьте их в `requirements.txt` по необходимости.

## Переменные окружения

Создайте файл `.env` в корне проекта и задайте:

```
OPENROUTER_API_KEY=ваш_openrouter_api_key
```

Функция получения ключа находится в `app/config.py` и выбросит ошибку, если ключ не задан.

## Запуск

Запуск в режиме разработки (перезагрузка при изменениях):

```powershell
py -m uvicorn main:app_openrouter --reload --host 0.0.0.0 --port 8000
```

Или через Poetry:

```powershell
poetry run uvicorn main:app_openrouter --reload --host 0.0.0.0 --port 8000
```

API будет доступен по умолчанию на `http://127.0.0.1:8000`.

## Основные эндпоинты

- GET `/` — простая проверка сервиса, возвращает сообщение и версию.
- GET `/models` — возвращает список поддерживаемых моделей (см. `AVAILABLE_MODELS` в `app/config.py`).
- POST `/generate` — генерация текста
  - Тело (JSON): `{ "prompt": "...", "model": "<model>", "max_tokens": 512, "stream": false }`
  - Возвращает: `response` (строка), `tokens_used`, `latency_seconds`.
- POST `/benchmark` — провести бенчмарк по CSV-файлу с промптами
  - Параметры формы (multipart/form-data):
    - `prompt_file` — файл с промптами (каждая строка — отдельный промпт)
    - `model` — модель (по умолчанию `deepseek/deepseek-chat-v3.1:free`)
    - `runs` — сколько прогонов (default 5)
    - `visualize` — если true, вернёт HTML таблицу вместо JSON
  - Результаты сохраняются в `benchmark_results.csv`.

Схемы запросов/ответов описаны в `app/models.py`.

## Примеры использования

Пример запроса на генерацию (Python + requests):

```python
import requests

url = 'http://127.0.0.1:8000/generate'
payload = {
    'prompt': 'Напиши краткое приветствие на русском',
    'model': 'deepseek/deepseek-chat-v3.1:free',
    'max_tokens': 128,
    'stream': False,
}

resp = requests.post(url, json=payload)
print(resp.json())
```

Пример запуска бенчмарка (PowerShell, curl):

```powershell
# prompts.txt — файл с промптами по одной строке
curl -X POST 'http://127.0.0.1:8000/benchmark' -F "prompt_file=@prompts.txt" -F "model=deepseek/deepseek-chat-v3.1:free" -F "runs=3" -F "visualize=false"
```

Если `visualize=true`, API вернёт HTML-страницу с таблицей результатов.

## Выходные файлы

- `benchmark_results.csv` — CSV с детальными результатами (run_id, prompt_id, prompt, model, latency_seconds, tokens_used, response_length, timestamp)
- `server_logs.txt` — файл логов (WARNING и выше)