"""Event Tracking Helper - OCR line extraction, matching, and state helpers."""

import re
from typing import Optional


def _normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching."""
    import unicodedata

    nfd = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return stripped.lower().strip()


def normalize_ocr_text(text: str) -> str:
    """Normalize OCR text for matching."""
    import unicodedata
    import re as _re

    if not text:
        return ""

    text = text.replace("\u0111", "d").replace("\u0110", "D")
    nfd = unicodedata.normalize("NFD", text)
    text = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = _re.sub(r"[|_~^`]", " ", text)
    text = _re.sub(r"\s+", " ", text).strip()
    return text


def _pattern_to_regex(pattern: str) -> tuple[str, list[str]]:
    """Convert pattern with placeholders to regex."""
    var_names = []
    regex = re.escape(pattern)
    regex = regex.replace(r"\{", "{").replace(r"\}", "}")

    def replace_placeholder(match):
        inner = match.group(1)
        var_names.append(inner)
        if inner in {"NUMBER", "minutes", "minute", "count"}:
            return r"(\d+(?:[.,]\d+)?)"
        return r"(.+?)"

    regex = re.sub(r"\{(\w+)\}", replace_placeholder, regex)
    return regex, var_names


def _extract_variables_from_text(ocr_text: str, pattern: str, var_names: list[str]) -> list[tuple]:
    """Extract variable values from OCR text using the pattern anchors."""
    if not var_names:
        return []

    parts = re.split(r"\{(?:NUMBER|TEXT|\w+)\}", pattern)
    placeholders = re.findall(r"\{(\w+)\}", pattern)
    norm_ocr = _normalize_text(ocr_text)

    try:
        from rapidfuzz import fuzz
    except ImportError:
        return []

    positions = []
    search_start = 0
    for part in parts:
        norm_part = _normalize_text(part)
        if not norm_part:
            positions.append((search_start, search_start))
            continue

        best_pos = -1
        best_score = 0
        win_len = len(norm_part)
        for i in range(search_start, max(search_start + 1, len(norm_ocr) - win_len + 2)):
            window = norm_ocr[i:i + win_len + 5]
            score = fuzz.ratio(norm_part, window[:win_len])
            if score > best_score:
                best_score = score
                best_pos = i

        if best_pos >= 0:
            positions.append((best_pos, best_pos + len(norm_part)))
            search_start = best_pos + len(norm_part)
        else:
            positions.append((search_start, search_start))

    variables = []
    for i, placeholder in enumerate(placeholders):
        start = positions[i][1]
        end = positions[i + 1][0] if i + 1 < len(positions) else len(norm_ocr)
        raw_value = norm_ocr[start:end].strip()
        if placeholder in {"NUMBER", "minutes", "minute", "count"}:
            nums = re.findall(r"\d+(?:[.,]\d+)?", raw_value)
            raw_value = nums[0] if nums else raw_value
        variables.append((placeholder, raw_value))

    return variables


def _pattern_static_chunks(pattern: str) -> list[str]:
    chunks = []
    for part in re.split(r"\{(?:NUMBER|TEXT|\w+)\}", pattern or ""):
        norm_part = normalize_ocr_text(part)
        if len(norm_part) >= 4:
            chunks.append(norm_part)
    return chunks


def _count_tokens(text: str) -> int:
    """Count normalized word-like tokens."""
    norm_text = normalize_ocr_text(text)
    if not norm_text:
        return 0
    return len([token for token in norm_text.split(" ") if token])


def _has_event_state_contradiction(pattern_text: str, line_text: str) -> bool:
    """Reject countdown/open-state cross matches that fuzzy matching can over-score."""
    pattern_norm = normalize_ocr_text(pattern_text)
    line_norm = normalize_ocr_text(line_text)

    pattern_is_open = "da bat dau" in pattern_norm
    line_is_countdown = (
        "se bat dau" in line_norm
        or "bat dau sau" in line_norm
        or "phut" in line_norm
        or "nua" in line_norm
    )
    if pattern_is_open and line_is_countdown:
        return True

    pattern_is_countdown = "se bat dau" in pattern_norm or "bat dau sau" in pattern_norm
    line_is_open = "da bat dau" in line_norm
    if pattern_is_countdown and line_is_open:
        return True

    return False


def _split_by_event_anchors(text: str) -> list[str]:
    anchor_pattern = re.compile(
        r"(?=(?:S[ựu] ki[ệe]n|Su kien|C[aá]nh c[ửu]a v[aà]o S[ựu] ki[ệe]n|Canh cua vao Su kien))",
        re.IGNORECASE,
    )
    parts = []
    for chunk in anchor_pattern.split(text):
        chunk = " ".join(str(chunk or "").split()).strip()
        if chunk:
            parts.append(chunk)
    return parts


def extract_event_tracking_lines(ocr_text: str, pattern: str = "") -> list[str]:
    """Extract likely event lines from OCR text for event tracking."""
    if not ocr_text:
        return []

    text = str(ocr_text or "").replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = [" ".join(line.split()).strip() for line in text.split("\n") if line.strip()]
    candidate_lines = raw_lines[:] if raw_lines else []

    if len(candidate_lines) <= 1:
        candidate_lines = _split_by_event_anchors(text)

    static_chunks = _pattern_static_chunks(pattern)
    filtered_lines = []
    for line in candidate_lines:
        norm_line = normalize_ocr_text(line)
        if static_chunks:
            if any(chunk in norm_line for chunk in static_chunks):
                filtered_lines.append(line)
                continue
        if "su kien" in norm_line or "imperial guardian" in norm_line:
            filtered_lines.append(line)

    seen = set()
    result = []
    for line in filtered_lines or candidate_lines:
        line = " ".join(str(line or "").split()).strip()
        if not line:
            continue
        dedup_key = normalize_ocr_text(line)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        result.append(line)
    return result


def match_ocr_pattern(ocr_text: str, pattern: str, threshold: float) -> Optional[dict]:
    """Match OCR text against one pattern with fuzzy matching + variable extraction."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        fuzz = None

    if not ocr_text or not pattern:
        return None

    regex_str, var_names = _pattern_to_regex(pattern)
    pattern_no_vars = re.sub(r"\{[^}]+\}", " ", pattern).strip()
    norm_pattern_no_vars = _normalize_text(pattern_no_vars)
    pattern_token_count = _count_tokens(pattern_no_vars)

    raw_text = str(ocr_text or "")
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    if not lines:
        lines = [raw_text.strip()]

    best_result = None
    best_score = -1.0

    for line_index, line in enumerate(lines):
        norm_line = normalize_ocr_text(line)
        line_token_count = _count_tokens(line)

        if _has_event_state_contradiction(pattern_no_vars, line):
            continue

        try:
            match = re.search(regex_str, line, re.IGNORECASE)
            if match:
                if pattern_token_count > 0 and line_token_count != pattern_token_count:
                    continue
                variables = list(zip(var_names, [value.strip() if value else "" for value in match.groups()]))
                if 100.0 > best_score:
                    best_score = 100.0
                    best_result = {"score": 100.0, "variables": variables, "line": line, "line_index": line_index}
                continue
        except Exception:
            pass

        if fuzz is None:
            continue

        if pattern_token_count > 0 and line_token_count != pattern_token_count:
            continue

        if not norm_pattern_no_vars:
            score = 0
        elif var_names:
            score = fuzz.partial_ratio(norm_pattern_no_vars, norm_line)
        else:
            # No placeholders means the whole notification must represent the same state.
            # partial_ratio can falsely match "da bat dau" against countdown lines.
            score = fuzz.ratio(norm_pattern_no_vars, norm_line)
        if score >= threshold and score > best_score:
            variables = _extract_variables_from_text(line, pattern, var_names)
            best_score = score
            best_result = {"score": score, "variables": variables, "line": line, "line_index": line_index}

    return best_result if best_result else None


def match_event_tracking_lines(lines: list[str], pattern: str, threshold: float) -> Optional[dict]:
    """Match one event tracking pattern against extracted OCR lines."""
    best_match = None
    best_score = -1.0
    for line_index, line in enumerate(lines):
        result = match_ocr_pattern(line, pattern, threshold)
        if not result:
            continue
        score = float(result.get("score", 0.0) or 0.0)
        if score > best_score:
            best_score = score
            best_match = {
                "score": score,
                "variables": list(result.get("variables", []) or []),
                "line": line,
                "line_index": line_index,
            }
    return best_match


def match_ocr_patterns(ocr_text: str, patterns: list[dict]) -> list[dict]:
    """Match OCR text against multiple patterns and return all matches."""
    matches = []

    for index, pattern_data in enumerate(patterns):
        pattern_str = pattern_data.get("pattern", "")
        threshold = float(pattern_data.get("threshold", 80.0))
        result = match_ocr_pattern(ocr_text, pattern_str, threshold)
        if result:
            matches.append(
                {
                    "pattern_index": index,
                    "pattern": pattern_str,
                    "score": result["score"],
                    "variables": result["variables"],
                }
            )

    return matches


def update_event_tracking_state(
    cache: dict,
    resolved_pattern: Optional[str],
    now_ts: float,
    reappear_timeout_s: float,
) -> dict:
    """Update cache for event tracking and decide whether a matched pattern should trigger."""
    seen_patterns = cache.setdefault("seen_patterns", {})
    current_visible = str(cache.get("current_visible_pattern", "") or "")

    if not resolved_pattern:
        if current_visible:
            current_entry = seen_patterns.setdefault(current_visible, {})
            if current_entry.get("missing_since") is None:
                current_entry["missing_since"] = now_ts
            cache["current_visible_pattern"] = ""
        return {"should_pass": False, "reason": "no_match"}

    resolved_pattern = str(resolved_pattern)
    entry = seen_patterns.setdefault(resolved_pattern, {})
    entry["last_seen_at"] = now_ts

    if not entry.get("has_triggered", False):
        entry["has_triggered"] = True
        entry["last_triggered_at"] = now_ts
        entry["missing_since"] = None
        cache["current_visible_pattern"] = resolved_pattern
        return {"should_pass": True, "reason": "first_seen"}

    if current_visible == resolved_pattern:
        entry["missing_since"] = None
        return {"should_pass": False, "reason": "duplicate_visible"}

    missing_since = entry.get("missing_since")
    cache["current_visible_pattern"] = resolved_pattern
    entry["missing_since"] = None
    if missing_since is not None and (now_ts - float(missing_since)) >= reappear_timeout_s:
        entry["last_triggered_at"] = now_ts
        return {"should_pass": True, "reason": "reappeared_after_timeout"}

    return {"should_pass": False, "reason": "seen_recently"}
