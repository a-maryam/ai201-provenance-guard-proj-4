import math
import re

_MIN_WORDS = 30


def _sentence_uniformity_score(sentences: list) -> float:
    """Low coefficient of variation in sentence length → more AI-like → higher score."""
    lengths = [len(s.split()) for s in sentences if s.strip()]
    if len(lengths) < 3:
        return 0.5
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.5
    std = math.sqrt(sum((l - mean) ** 2 for l in lengths) / len(lengths))
    cv = std / mean  # lower CV = more uniform = more AI
    # CV ≈ 0 → score 1.0; CV ≥ 0.7 → score 0.0
    return max(0.0, min(1.0, 1.0 - (cv / 0.7)))


def _vocab_richness_score(words: list) -> float:
    """Low type-token ratio (repetitive vocabulary) → more AI-like → higher score."""
    if len(words) < 20:
        return 0.5
    ttr = len({w.lower() for w in words}) / len(words)
    # TTR ≤ 0.30 → score 1.0; TTR ≥ 0.65 → score 0.0
    return max(0.0, min(1.0, (0.65 - ttr) / 0.35))


def _word_length_score(words: list) -> float:
    """Higher average word length → more formal/AI-like → higher score."""
    if not words:
        return 0.5
    avg_len = sum(len(w) for w in words) / len(words)
    # avg_len ≤ 4 → score 0.0 (casual, human); avg_len ≥ 6 → score 1.0 (formal, AI)
    return max(0.0, min(1.0, (avg_len - 4.0) / 2.0))


def classify_with_stylometry(text: str) -> float:
    """Return a 0-1 score for the probability that *text* is AI-generated,
    based on structural heuristics. Returns 0.5 when text is too short."""
    words = re.findall(r"\b\w+\b", text)
    if len(words) < _MIN_WORDS:
        return 0.5

    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]

    sent_score = _sentence_uniformity_score(sentences)
    vocab_score = _vocab_richness_score(words)
    word_len_score = _word_length_score(words)

    combined = (sent_score * 0.50) + (vocab_score * 0.30) + (word_len_score * 0.20)
    return round(max(0.0, min(1.0, combined)), 4)
