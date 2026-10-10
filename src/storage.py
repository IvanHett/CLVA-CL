"""Evaluation logging: records queries, responses and unanswered queries as CSV.

The three files mirror the Queries, Responses and Unanswered Queries tables of
the planned database schema, so they can be imported into it later.
"""
import csv
import threading
from datetime import datetime
from pathlib import Path

from . import config
from .preprocessing import normalise

QUERY_FIELDS = ["query_id", "user_input", "timestamp", "predicted_intent"]
RESPONSE_FIELDS = [
    "response_id", "response_text", "related_query_id", "response_time_ms", "matched", "stage", "mode",
]
UNANSWERED_FIELDS = ["id", "query_text", "frequency_count", "first_seen", "last_seen"]


def _read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _append(path: Path, fields: list[str], row: dict) -> None:
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


class InteractionLogger:
    def __init__(self, log_dir: Path = config.LOG_DIR):
        self._dir = Path(log_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._queries = self._dir / "queries_log.csv"
        self._responses = self._dir / "responses_log.csv"
        self._unanswered = self._dir / "unanswered_queries.csv"
        self._lock = threading.Lock()
        self._next_id = len(_read(self._queries)) + 1

    def record(
        self, user_input: str, intent: str, response_text: str,
        response_time_ms: float, matched: bool, stage: str, mode: str,
    ) -> int:
        """Log one interaction and return its query id."""
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            query_id = self._next_id
            self._next_id += 1
            _append(self._queries, QUERY_FIELDS, {
                "query_id": query_id, "user_input": user_input,
                "timestamp": now, "predicted_intent": intent,
            })
            _append(self._responses, RESPONSE_FIELDS, {
                "response_id": query_id, "response_text": response_text,
                "related_query_id": query_id, "response_time_ms": f"{response_time_ms:.2f}",
                "matched": matched, "stage": stage, "mode": mode,
            })
            if not matched:
                self._record_unanswered(user_input, now)
        return query_id

    def _record_unanswered(self, user_input: str, now: str) -> None:
        key = normalise(user_input)
        if not key:
            return
        rows = _read(self._unanswered)
        for row in rows:
            if row["query_text"] == key:
                row["frequency_count"] = int(row["frequency_count"]) + 1
                row["last_seen"] = now
                break
        else:
            rows.append({
                "id": len(rows) + 1, "query_text": key, "frequency_count": 1,
                "first_seen": now, "last_seen": now,
            })
        _write(self._unanswered, UNANSWERED_FIELDS, rows)

    def unanswered(self) -> list[dict]:
        """Unanswered queries, most frequently asked first."""
        with self._lock:
            rows = _read(self._unanswered)
        for row in rows:
            row["id"] = int(row["id"])
            row["frequency_count"] = int(row["frequency_count"])
        return sorted(rows, key=lambda r: r["frequency_count"], reverse=True)
