"""Typo-tolerant ranking for the employee search (standard library only).

Why not a database feature: the portal runs on SQLite locally and PostgreSQL in production, and the
searchable content is small (hundreds of rows). Ranking in Python works the same on both.

Rules, per query word:
  exact word / word starts with it (typing in progress) / word contains it  -> strong match
  otherwise a close spelling (one or two wrong, missing or swapped letters)   -> weaker match
Words of 1-3 letters must match exactly or as a prefix (typo tolerance there only creates noise).
Every query word must match something, so "leave polcy" finds the leave policy but not any leave page.
"""
import re
import unicodedata
from difflib import SequenceMatcher

_NON_WORD = re.compile(r"[^0-9a-z]+")


def normalize(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return _NON_WORD.sub(" ", text.lower()).strip()


def tokens(text):
    return normalize(text).split()


def _threshold(length):
    if length <= 3:
        return None  # exact or prefix only
    return 0.75 if length == 4 else 0.78


def _close(query_word, vocab_word):
    """Similarity (0..1) of two words, also looking inside a longer word (e.g. 'trvel' in 'quest2travel')."""
    best = SequenceMatcher(None, query_word, vocab_word).ratio()
    n = len(query_word)
    if n >= 5 and len(vocab_word) > n + 1:  # in-word matching only for longer queries (less noise)
        for size in (n - 1, n, n + 1):
            if size < 3:
                continue
            for start in range(0, len(vocab_word) - size + 1):
                ratio = SequenceMatcher(None, query_word, vocab_word[start:start + size]).ratio()
                if ratio > best:
                    best = ratio
    return best


def match_word(query_word, vocab_word):
    """Score one query word against one vocabulary word (0 = no match)."""
    if query_word == vocab_word:
        return 1.0
    if len(query_word) >= 2 and vocab_word.startswith(query_word):
        return 0.92
    if len(query_word) >= 3 and query_word in vocab_word:
        return 0.8
    threshold = _threshold(len(query_word))
    if threshold is None or abs(len(vocab_word) - len(query_word)) > max(3, len(query_word)):
        return 0.0
    ratio = _close(query_word, vocab_word)
    return ratio * 0.75 if ratio >= threshold else 0.0


def rank(query, rows, fields, limit=25):
    """Return (ranked_rows, suggestion).

    rows    iterable of objects or dicts
    fields  [(attribute_name, weight), ...]  e.g. [("title", 1.0), ("summary", 0.5)]
    suggestion  corrected spelling to offer ("Showing results for ..."), or "" when nothing was corrected
    """
    q_words = tokens(query)
    if not q_words:
        return [], ""
    prepared = []
    vocabulary = set()
    for row in rows:
        per_field = []
        for name, weight in fields:
            value = row.get(name) if isinstance(row, dict) else getattr(row, name, "")
            words = tokens(value)
            per_field.append((normalize(value), words, weight))
            vocabulary.update(words)
        prepared.append((row, per_field))

    # Match every query word against the distinct words once, not against every row.
    lookup = {}
    corrected = []
    for qw in q_words:
        scores = {}
        for vw in vocabulary:
            score = match_word(qw, vw)
            if score:
                scores[vw] = score
        lookup[qw] = scores
        best = max(scores.items(), key=lambda kv: (kv[1], -len(kv[0]))) if scores else None
        corrected.append(best[0] if best and best[1] < 0.8 else qw)

    ranked = []
    phrase = " ".join(q_words)
    for row, per_field in prepared:
        total = 0.0
        for qw in q_words:
            best = 0.0
            for _, words, weight in per_field:
                for word in words:
                    score = lookup[qw].get(word)
                    if score and score * weight > best:
                        best = score * weight
            if best == 0.0:
                total = 0.0
                break
            total += best
        if total == 0.0:
            continue
        score = total / len(q_words)
        if any(phrase in text for text, _, weight in per_field if weight >= 1.0):
            score += 0.3  # the whole phrase appears in the main field
        ranked.append((score, row))
    ranked.sort(key=lambda pair: -pair[0])
    suggestion = " ".join(corrected) if corrected != q_words and ranked else ""
    return [row for _, row in ranked[:limit]], suggestion
