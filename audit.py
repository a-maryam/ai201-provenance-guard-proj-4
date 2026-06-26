import json
import os
from datetime import datetime, timezone

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit.jsonl")

def get_log() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    appealed_ids = {
        e["content_id"] for e in entries if e.get("event") == "appeal"
    }
    for e in entries:
        if e.get("event") != "appeal":
            e["appeal_filed"] = e.get("content_id") in appealed_ids

    return list(reversed(entries))


def find_submission(content_id: str) -> dict | None:
    if not os.path.exists(LOG_PATH):
        return None
    with open(LOG_PATH) as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if entry.get("content_id") == content_id and entry.get("event") != "appeal":
                    return entry
    return None


def log_submission(
    content_id: str,
    creator_id: str,
    attribution: str,
    confidence: float | None,
    llm_score: float,
    style_score: float,
) -> None:
    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": round(llm_score, 4),
        "style_score": round(style_score, 4),
        "status": "classified",
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def log_appeal(content_id: str, creator_id: str, creator_reasoning: str) -> None:
    entry = {
        "event": "appeal",
        "content_id": content_id,
        "creator_id": creator_id,
        "creator_reasoning": creator_reasoning,
        "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        "status": "under_review",
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
