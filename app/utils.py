from datetime import datetime
import csv
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def create_benchmark_html_table(
    results: List[Dict[str, Any]],
    latency_stats: Dict[str, Any],
    tokens_stats: Dict[str, Any],
    model: str,
    runs: int,
) -> str:
    """Создает HTML таблицу с результатами бенчмарка"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Benchmark Results - {model}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
            .stat-box {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; flex: 1; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .number {{ text-align: right; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Benchmark Results</h1>
            <p><strong>Model:</strong> {model}</p>
            <p><strong>Runs:</strong> {runs}</p>
            <p><strong>Total Requests:</strong> {len(results)}</p>
            <p><strong>Generated at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <h3>Latency Statistics</h3>
                <p>Average: {latency_stats['avg']}s</p>
                <p>Min: {latency_stats['min']}s</p>
                <p>Max: {latency_stats['max']}s</p>
                <p>Std Dev: {latency_stats['std_dev']}s</p>
            </div>
            <div class="stat-box">
                <h3>Token Statistics</h3>
                <p>Average: {tokens_stats['avg']}</p>
                <p>Min: {tokens_stats['min']}</p>
                <p>Max: {tokens_stats['max']}</p>
                <p>Std Dev: {tokens_stats['std_dev']}</p>
            </div>
        </div>
        
        <h2>Detailed Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Run</th>
                    <th>Prompt ID</th>
                    <th>Prompt (truncated)</th>
                    <th>Responce (truncated)</th>
                    <th class="number">Latency (s)</th>
                    <th class="number">Tokens Used</th>
                    <th class="number">Response Length</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
    """

    for result in results:
        html += f"""
                <tr>
                    <td>{result['run_id']}</td>
                    <td>{result['prompt_id']}</td>
                    <td>{result['prompt']}</td>
                    <td>{result['response']}</td>
                    <td class="number">{result['latency_seconds']}</td>
                    <td class="number">{result['tokens_used']}</td>
                    <td class="number">{result['response_length']}</td>
                    <td>{result['timestamp']}</td>
                </tr>
        """

    html += """
            </tbody>
        </table>
    </body>
    </html>
    """

    return html


def save_results_csv(results: List[Dict[str, Any]], filename: str) -> str:
    """Сохраняет результаты в CSV и возвращает имя файла (экспорт результатов)."""
    try:
        with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
            if results:
                fieldnames = [
                    "run_id",
                    "prompt_id",
                    "prompt",
                    "model",
                    "latency_seconds",
                    "tokens_used",
                    "response_length",
                    "timestamp",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for r in results:
                    clean = {
                        k: (
                            v
                            if not isinstance(v, str)
                            else v.replace(",", ";").replace("\n", " ")
                        )
                        for k, v in r.items()
                        if k in fieldnames
                    }
                    writer.writerow(clean)

        return filename
    except Exception as e:
        logger.error(f"Error saving CSV {e}", exc_info=True)
        raise
