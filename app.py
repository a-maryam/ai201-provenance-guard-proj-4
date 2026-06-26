import uuid

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from audit import find_submission, get_log, log_appeal, log_submission
from signals.llm_classifier import classify_with_llm
from signals.stylometry import classify_with_stylometry

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


def _attribution_result(score: float) -> str:
    if score >= 0.80:
        return "likely_ai"
    if score >= 0.40:
        return "uncertain"
    return "likely_human"


def get_transparency_label(score: float) -> str:
    if score >= 0.80:
        return "High-confidence AI"
    if score >= 0.40:
        return "Uncertain / Mixed signals"
    return "High-confidence Human"


def score_confidence(llm_score: float, style_score: float) -> float:
    """Weighted combination per planning.md: LLM carries more weight than structure."""
    return round((llm_score * 0.6) + (style_score * 0.4), 4)

@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(silent=True)
    if not data or "text" not in data or "creator_id" not in data:
        return jsonify({"error": "Request body must be JSON with 'text' and 'creator_id' fields"}), 400

    text = data["text"]
    creator_id = data["creator_id"]

    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "'text' must be a non-empty string"}), 400
    if not isinstance(creator_id, str) or not creator_id.strip():
        return jsonify({"error": "'creator_id' must be a non-empty string"}), 400

    content_id = str(uuid.uuid4())

    # Signal 1: LLM semantic classification
    llm_score = classify_with_llm(text)

    # Signal 2: Stylometric heuristics
    style_score = classify_with_stylometry(text)

    # Confidence scoring: weighted combination of both signals
    weighted_score = score_confidence(llm_score, style_score)

    attribution = _attribution_result(weighted_score)
    confidence = weighted_score

    log_submission(
        content_id=content_id,
        creator_id=creator_id,
        attribution=attribution,
        confidence=confidence,
        llm_score=llm_score,
        style_score=style_score,
    )

    return jsonify(
        {
            "content_id": content_id,
            "attribution_result": attribution,
            "confidence": confidence,
            "label": get_transparency_label(confidence),
        }
    ), 200


@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json(silent=True)
    if not data or not all(k in data for k in ("content_id", "creator_id", "creator_reasoning")):
        return jsonify({"error": "Request body must include 'content_id', 'creator_id', and 'creator_reasoning'"}), 400

    content_id = data["content_id"]
    creator_id = data["creator_id"]
    creator_reasoning = data["creator_reasoning"]

    if not isinstance(creator_reasoning, str) or not creator_reasoning.strip():
        return jsonify({"error": "'creator_reasoning' must be a non-empty string"}), 400

    submission = find_submission(content_id)
    if submission is None:
        return jsonify({"error": "content_id not found"}), 404

    if submission["creator_id"] != creator_id:
        return jsonify({"error": "Only the original creator may appeal this content"}), 403

    log_appeal(content_id=content_id, creator_id=creator_id, creator_reasoning=creator_reasoning)

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Your appeal has been received and is under review.",
    }), 200


@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()})


if __name__ == "__main__":
    app.run(debug=True)
