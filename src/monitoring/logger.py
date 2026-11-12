# Latency, token usage, and pipeline trace logging
# src/monitoring/logger.py
import os
import json
import csv
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

CSV_LOG_PATH = LOG_DIR / "query_logs.csv"
JSONL_LOG_PATH = LOG_DIR / "query_logs.jsonl"

CSV_HEADERS = [
    "timestamp",
    "user",
    "role",
    "query",
    "allowed_departments",
    "target_department",
    "retrieved_chunks_count",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "latency_seconds",
    "status",
    "response_preview"
]


def _init_csv_log():
    """Ensure CSV log file exists with appropriate headers."""
    if not CSV_LOG_PATH.exists():
        with open(CSV_LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def log_interaction(
    user: str,
    role: str,
    query: str,
    allowed_departments: list,
    target_department: str,
    retrieved_chunks: list,
    response: str,
    latency_seconds: float,
    token_usage: dict = None,
    status: str = "SUCCESS"
):
    """
    Records query interactions, context, latency, and token consumption.
    """
    try:
        _init_csv_log()
        now_iso = datetime.utcnow().isoformat() + "Z"
        
        token_usage = token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)

        preview = response.replace("\n", " ").strip()[:100]

        # 1. Summary entry in CSV
        csv_row = [
            now_iso,
            user,
            role,
            query,
            ";".join(allowed_departments) if allowed_departments else "all",
            target_department or "unknown",
            len(retrieved_chunks),
            prompt_tokens,
            completion_tokens,
            total_tokens,
            f"{latency_seconds:.2f}",
            status,
            preview
        ]
        with open(CSV_LOG_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_row)

        # 2. Complete record in JSONL
        jsonl_record = {
            "timestamp": now_iso,
            "user": user,
            "role": role,
            "query": query,
            "allowed_departments": allowed_departments,
            "target_department": target_department,
            "contexts": [c.get("content", "") for c in retrieved_chunks],
            "response": response,
            "token_usage": token_usage,
            "latency_seconds": round(latency_seconds, 2),
            "status": status
        }
        with open(JSONL_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(jsonl_record, ensure_ascii=False) + "\n")

    except Exception as e:
        print(f"[LOGGING ERROR] Failed to record query log: {e}")
