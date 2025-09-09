#!/usr/bin/env python3
"""
Комплексное тестирование FastAPI OpenRouter сервера
10 тестов: 5 для /generate + 5 для /benchmark
"""

import requests
import json
import time
import statistics
import csv
from datetime import datetime
import os

BASE_URL = "http://localhost:8000"

# Тестовые данные
TEST_PROMPTS = [
    "Кратко, что такое искусственный интеллект?",
    "Напиши короткое стихотворение о весне.",
    "Рассскажи короткий анекдот про программистов.",
]

MODELS = [
    "deepseek/deepseek-chat-v3.1:free",
    "z-ai/glm-4.5-air:free",
    "moonshotai/kimi-k2:free",
]


def measure_request_time(func):
    """Декоратор для измерения времени выполнения"""

    def wrapper(*args, **kwargs):
        start = time.time()

        result = func(*args, **kwargs)
        end = time.time()
        return result, end - start

    return wrapper


@measure_request_time
def test_generate_normal(prompt, model, max_tokens=256):
    """Тест обычной генерации"""
    data = {"prompt": prompt, "model": model, "max_tokens": max_tokens, "stream": False}

    response = requests.post(
        f"{BASE_URL}/generate",
        json=data,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )

    return {
        "status_code": response.status_code,
        "success": response.status_code == 200,
        "response_data": response.json() if response.status_code == 200 else None,
        "error": response.text if response.status_code != 200 else None,
    }


@measure_request_time
def test_generate_stream(prompt, model, max_tokens=256):
    """Тест SSE стриминга"""
    data = {"prompt": prompt, "model": model, "max_tokens": max_tokens, "stream": True}

    response = requests.post(
        f"{BASE_URL}/generate",
        json=data,
        headers={"Content-Type": "application/json"},
        timeout=60,
        stream=True,
    )

    # Собираем весь стрим
    chunks = []
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    try:
                        data_obj = json.loads(line_str[6:])
                        if "content" in data_obj:
                            chunks.append(data_obj["content"])
                        elif data_obj.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    return {
        "status_code": response.status_code,
        "success": response.status_code == 200,
        "chunks_received": len(chunks),
        "total_content": "".join(chunks) if chunks else "",
        "error": response.text if response.status_code != 200 else None,
    }


@measure_request_time
def test_benchmark_normal(model, runs, prompts_file):
    """Тест обычного бенчмарка"""
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts_content = f.read()

    files = {"prompt_file": ("test_prompts.txt", prompts_content, "text/plain")}
    data = {"model": model, "runs": str(runs), "visualize": "false"}

    response = requests.post(
        f"{BASE_URL}/benchmark", files=files, data=data, timeout=300
    )

    return {
        "status_code": response.status_code,
        "success": response.status_code == 200,
        "response_data": response.json() if response.status_code == 200 else None,
        "error": response.text if response.status_code != 200 else None,
    }


@measure_request_time
def test_benchmark_visualized(model, runs, prompts_file):
    """Тест бенчмарка с HTML визуализацией"""
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts_content = f.read()

    files = {"prompt_file": ("test_prompts.txt", prompts_content, "text/plain")}
    data = {"model": model, "runs": str(runs), "visualize": "true"}

    response = requests.post(
        f"{BASE_URL}/benchmark", files=files, data=data, timeout=300
    )

    return {
        "status_code": response.status_code,
        "success": response.status_code == 200,
        "html_length": len(response.text) if response.status_code == 200 else 0,
        "is_html": response.headers.get("content-type", "").startswith("text/html"),
        "error": response.text[:500] if response.status_code != 200 else None,
    }


def create_test_prompts_file():
    """Создает файл с тестовыми промптами"""
    filename = "test_prompts.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(TEST_PROMPTS))
    return filename


def run_generate_tests():
    """Запуск 5 тестов для /generate"""
    print("=" * 60)
    print("ТЕСТЫ /generate (5 тестов)")
    print("=" * 60)

    results = []

    # Тест 1: Обычная генерация с первой моделью
    print("\n1. Тест обычной генерации (deepseek)")
    result, latency = test_generate_normal(TEST_PROMPTS[0], MODELS[0])
    results.append(
        {
            "test_name": "generate_normal_deepseek",
            "model": MODELS[0],
            "latency": latency,
            "success": result["success"],
            "tokens_used": (
                result["response_data"]["tokens_used"] if result["success"] else 0
            ),
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    print(f"  Ошибка: {result['error']}" if not result["success"] else "")
    if result["success"]:
        print(f"  Токены: {result['response_data']['tokens_used']}")
        print(f"  Длина ответа: {len(result['response_data']['response'])}")

    # Тест 2: SSE стриминг с первой моделью
    print("\n2. Тест SSE стриминга (deepseek)")
    result, latency = test_generate_stream(TEST_PROMPTS[0], MODELS[0])
    results.append(
        {
            "test_name": "generate_stream_deepseek",
            "model": MODELS[0],
            "latency": latency,
            "success": result["success"],
            "chunks_received": result["chunks_received"] if result["success"] else 0,
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        print(f"  Чанков получено: {result['chunks_received']}")
        print(f"  Длина контента: {len(result['total_content'])}")

    # Тест 3: Обычная генерация со второй моделью
    print("\n3. Тест обычной генерации (glm-4.5)")
    result, latency = test_generate_normal(TEST_PROMPTS[0], MODELS[1])
    results.append(
        {
            "test_name": "generate_normal_glm",
            "model": MODELS[1],
            "latency": latency,
            "success": result["success"],
            "tokens_used": (
                result["response_data"]["tokens_used"] if result["success"] else 0
            ),
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        print(f"  Токены: {result['response_data']['tokens_used']}")

    # Тест 4: SSE стриминг со второй моделью
    print("\n4. Тест SSE стриминга (glm-4.5)")
    result, latency = test_generate_stream(TEST_PROMPTS[0], MODELS[1])
    results.append(
        {
            "test_name": "generate_stream_glm",
            "model": MODELS[1],
            "latency": latency,
            "success": result["success"],
            "chunks_received": result["chunks_received"] if result["success"] else 0,
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        print(f"  Чанков получено: {result['chunks_received']}")

    # Тест 5: Обычная генерация с третьей моделью
    print("\n5. Тест обычной генерации(kimi)")
    result, latency = test_generate_normal(TEST_PROMPTS[0], MODELS[2])
    results.append(
        {
            "test_name": "generate_normal_kimi_512",
            "model": MODELS[2],
            "latency": latency,
            "success": result["success"],
            "tokens_used": (
                result["response_data"]["tokens_used"] if result["success"] else 0
            ),
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        print(f"  Токены: {result['response_data']['tokens_used']}")

    return results


def run_benchmark_tests():
    """Запуск 5 тестов для /benchmark"""
    print("\n" + "=" * 60)
    print("ТЕСТЫ /benchmark (5 тестов)")
    print("=" * 60)

    results = []
    prompts_file = create_test_prompts_file()

    # Тест 1: Бенчмарк deepseek, 1 прогон
    print("\n1. Бенчмарк deepseek (runs=1)")
    result, latency = test_benchmark_normal(MODELS[0], 1, prompts_file)
    results.append(
        {
            "test_name": "benchmark_deepseek_2runs",
            "model": MODELS[0],
            "latency": latency,
            "success": result["success"],
            "runs": 2,
            "total_prompts": (
                result["response_data"]["total_prompts"] if result["success"] else 0
            ),
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        data = result["response_data"]
        print(f"  Промптов: {data['total_prompts']}")
        print(f"  Средняя задержка: {data['latency_stats']['avg']}s")
        print(f"  CSV файл: {data['results_file']}")

    # Тест 2: Бенчмарк glm-4.5, 2 прогона
    print("\n2. Бенчмарк glm-4.5 (runs=2)")
    result, latency = test_benchmark_normal(MODELS[1], 2, prompts_file)
    results.append(
        {
            "test_name": "benchmark_glm_3runs",
            "model": MODELS[1],
            "latency": latency,
            "success": result["success"],
            "runs": 3,
            "total_prompts": (
                result["response_data"]["total_prompts"] if result["success"] else 0
            ),
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        data = result["response_data"]
        print(f"  Промптов: {data['total_prompts']}")
        print(f"  Средняя задержка: {data['latency_stats']['avg']}s")

    # Тест 3: Бенчмарк kimi, 2 прогона с HTML визуализацией
    print("\n3. Бенчмарк kimi с HTML визуализацией (runs=1)")
    result, latency = test_benchmark_visualized(MODELS[2], 1, prompts_file)
    results.append(
        {
            "test_name": "benchmark_kimi_html",
            "model": MODELS[2],
            "latency": latency,
            "success": result["success"],
            "runs": 2,
            "html_generated": result["is_html"] if result["success"] else False,
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        print(f"  HTML размер: {result['html_length']} символов")
        print(f"  Это HTML: {result['is_html']}")

    # Тест 4: Большой бенчмарк deepseek, 3 прогона
    print("\n4. Большой бенчмарк deepseek (runs=3)")
    result, latency = test_benchmark_normal(MODELS[0], 3, prompts_file)
    results.append(
        {
            "test_name": "benchmark_deepseek_4runs",
            "model": MODELS[0],
            "latency": latency,
            "success": result["success"],
            "runs": 4,
            "total_prompts": (
                result["response_data"]["total_prompts"] if result["success"] else 0
            ),
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        data = result["response_data"]
        print(f"  Всего запросов: {data['total_prompts'] * data['runs']}")
        print(f"  Стандартное отклонение: {data['latency_stats']['std_dev']}s")

    # Тест 5: Бенчмарк glm-4.5 с HTML визуализацией, 2 прогона
    print("\n5. Бенчмарк glm-4.5 с HTML (runs=2)")
    result, latency = test_benchmark_visualized(MODELS[1], 2, prompts_file)
    results.append(
        {
            "test_name": "benchmark_glm_3runs_html",
            "model": MODELS[1],
            "latency": latency,
            "success": result["success"],
            "runs": 3,
            "html_generated": result["is_html"] if result["success"] else False,
        }
    )
    print(f"  Успех: {result['success']}")
    print(f"  Время: {latency:.3f}s")
    if result["success"]:
        print(f"  HTML размер: {result['html_length']} символов")

    return results


def create_comparison_table(generate_results, benchmark_results):
    """Создает сравнительную таблицу моделей"""
    print("\n" + "=" * 80)
    print("СРАВНИТЕЛЬНАЯ ТАБЛИЦА МОДЕЛЕЙ")
    print("=" * 80)

    # Группируем результаты по моделям
    model_stats = {}

    # Обрабатываем результаты генерации
    for result in generate_results:
        model = result["model"]
        if model not in model_stats:
            model_stats[model] = {"generate_latencies": [], "benchmark_latencies": []}
        if result["success"]:
            model_stats[model]["generate_latencies"].append(result["latency"])

    # Обрабатываем результаты бенчмарков
    for result in benchmark_results:
        model = result["model"]
        if model not in model_stats:
            model_stats[model] = {"generate_latencies": [], "benchmark_latencies": []}
        if result["success"]:
            model_stats[model]["benchmark_latencies"].append(result["latency"])

    # Создаем таблицу
    print(
        f"{'Модель':<30} {'Generate Avg':<15} {'Generate StdDev':<15} {'Benchmark Avg':<15} {'Benchmark StdDev':<15}"
    )
    print("-" * 90)

    comparison_data = []

    for model, stats in model_stats.items():
        gen_latencies = stats["generate_latencies"]
        bench_latencies = stats["benchmark_latencies"]

        gen_avg = statistics.mean(gen_latencies) if gen_latencies else 0
        gen_std = statistics.stdev(gen_latencies) if len(gen_latencies) > 1 else 0

        bench_avg = statistics.mean(bench_latencies) if bench_latencies else 0
        bench_std = statistics.stdev(bench_latencies) if len(bench_latencies) > 1 else 0

        model_short = model.split("/")[-1]  # Убираем префикс для читабельности

        print(
            f"{model_short:<30} {gen_avg:<15.3f} {gen_std:<15.3f} {bench_avg:<15.3f} {bench_std:<15.3f}"
        )

        comparison_data.append(
            {
                "model": model,
                "generate_avg_latency": round(gen_avg, 3),
                "generate_std_dev": round(gen_std, 3),
                "benchmark_avg_latency": round(bench_avg, 3),
                "benchmark_std_dev": round(bench_std, 3),
                "generate_tests": len(gen_latencies),
                "benchmark_tests": len(bench_latencies),
            }
        )

    return comparison_data


def save_results_to_csv(generate_results, benchmark_results, comparison_data):
    """Сохраняет все результаты в CSV файлы"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Детальные результаты генерации
    with open(
        f"test_results_generate_{timestamp}.csv", "w", newline="", encoding="utf-8"
    ) as f:
        if generate_results:
            # Build ordered union of all keys across all result dicts to avoid missing/extra fields
            fieldnames = []
            for row in generate_results:
                for k in row.keys():
                    if k not in fieldnames:
                        fieldnames.append(k)
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(generate_results)

    # Детальные результаты бенчмарка
    with open(
        f"test_results_benchmark_{timestamp}.csv", "w", newline="", encoding="utf-8"
    ) as f:
        if benchmark_results:
            # Build ordered union of all keys across all result dicts
            fieldnames = []
            for row in benchmark_results:
                for k in row.keys():
                    if k not in fieldnames:
                        fieldnames.append(k)
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(benchmark_results)

    # Сравнительная таблица
    with open(
        f"model_comparison_{timestamp}.csv", "w", newline="", encoding="utf-8"
    ) as f:
        if comparison_data:
            # Build ordered union of all keys across all comparison rows
            fieldnames = []
            for row in comparison_data:
                for k in row.keys():
                    if k not in fieldnames:
                        fieldnames.append(k)
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(comparison_data)

    print(f"\n📊 Результаты сохранены:")
    print(f"  - test_results_generate_{timestamp}.csv")
    print(f"  - test_results_benchmark_{timestamp}.csv")
    print(f"  - model_comparison_{timestamp}.csv")


def main():
    """Главная функция тестирования"""
    print("🚀 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ API")
    print("=" * 80)

    start_time = time.time()

    # Запускаем тесты
    generate_results = run_generate_tests()
    benchmark_results = run_benchmark_tests()

    # Создаем сравнительную таблицу
    comparison_data = create_comparison_table(generate_results, benchmark_results)

    # Сохраняем результаты
    save_results_to_csv(generate_results, benchmark_results, comparison_data)

    total_time = time.time() - start_time

    # Итоговая статистика
    print("\n" + "=" * 80)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 80)

    generate_success = sum(1 for r in generate_results if r["success"])
    benchmark_success = sum(1 for r in benchmark_results if r["success"])

    print(f"Тесты /generate:   {generate_success}/5 успешных")
    print(f"Тесты /benchmark:  {benchmark_success}/5 успешных")
    print(f"Общее время:       {total_time:.1f} секунд")
    print(f"Всего тестов:      10")
    print(f"Успешность:        {(generate_success + benchmark_success)/10*100:.1f}%")

    # Очищаем временный файл
    if os.path.exists("test_prompts.txt"):
        os.remove("test_prompts.txt")

    print("\n✅ Тестирование завершено!")


if __name__ == "__main__":
    main()
