from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RECORD_KEYS = ("GU", "C", "T", "TC", "E", "LU")
TIMEOUT_MIN = 60
TIMEOUT_MAX = 3600
COMMENT_PREFIXES = ("*", "\\", "/")

STATE_CHANGE = re.compile(
    r"\b(IPL|LOAD|FILL|STOP|INACT|ACTIVATE|START|ENABLE|DISABLE|BRING.?UP|BRING.?DOWN|"
    r"PROTECT|UNPROTECT|DELETE|PURGE|RESET|VARY|ALTER|UPDATE|RESTART)\b",
    re.IGNORECASE,
)
ERROR_WORDS = re.compile(
    r"\b(ERROR|FAILED|FAILURE|NOT FOUND|INVALID|ABEND|FATAL|REJECTED)\b", re.IGNORECASE
)
PLACEHOLDER = re.compile(r"<[A-Z0-9_ ]+>")
HISTORICAL_CAVEAT = "Historical sample only; confirm for the target system/release and current runbook."


@dataclass(frozen=True)
class Recommendation:
    command: str
    response: str
    match_type: str
    count: int
    confidence: str
    caveat: str = HISTORICAL_CAVEAT


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip()).upper()


def load_catalog(path: str | Path) -> list[dict[str, str]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _observed_count(row: dict[str, str]) -> int:
    try:
        return int(row.get("observed_count") or 1)
    except ValueError:
        return 1


def recommend(command: str, catalog: list[dict[str, str]], limit: int = 8) -> list[Recommendation]:
    query = normalize_command(command)
    if not query:
        return []
    query_tokens = query.split()

    exact: list[Recommendation] = []
    family: list[Recommendation] = []
    for row in catalog:
        candidate = normalize_command(row.get("command", ""))
        if not candidate:
            continue
        count = _observed_count(row)
        response = row.get("observed_expected_response", "")
        if candidate == query:
            confidence = "historical-repeat" if count >= 2 else "single-observation"
            exact.append(Recommendation(row["command"], response, "exact", count, confidence))
            continue
        tokens = candidate.split()
        if tokens[0] == query_tokens[0] and abs(len(tokens) - len(query_tokens)) <= 2:
            family.append(Recommendation(row["command"], response, "same-command-family", count, "candidate-only"))

    family.sort(key=lambda r: (-r.count, abs(len(r.command.split()) - len(query_tokens)), r.command))

    results: list[Recommendation] = []
    seen: set[tuple[str, str]] = set()
    for rec in exact + family:
        key = (normalize_command(rec.command), rec.response)
        if key in seen:
            continue
        seen.add(key)
        results.append(rec)
        if len(results) >= limit:
            break
    return results


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)


def _check_text(prefix: str, field: str, value: str, errors: list[str], warnings: list[str]) -> None:
    if "\n" in value or "\r" in value:
        errors.append(f"{prefix}: each {field} value must fit on a single line.")
    if not value.isascii():
        errors.append(f"{prefix}: {field} contains non-ASCII characters.")
    if value.lstrip().upper().startswith(tuple(f"{key}:" for key in RECORD_KEYS)):
        warnings.append(f"{prefix}: {field} starts with a TDR key; check for accidental nested syntax.")
    if PLACEHOLDER.search(value):
        warnings.append(f"{prefix}: {field} still contains a placeholder ({value}).")


def validate_spec(spec: Any) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(spec, dict) or not isinstance(spec.get("steps"), list) or not spec["steps"]:
        return {"valid": False, "errors": ["Spec must contain a non-empty 'steps' list."], "warnings": []}

    global_unexpected = spec.get("global_unexpected") or []
    if not _is_string_list(global_unexpected):
        errors.append("'global_unexpected' must be a list of non-empty strings.")
    else:
        for value in global_unexpected:
            _check_text("Global", "global_unexpected", value, errors, warnings)

    for number, step in enumerate(spec["steps"], 1):
        prefix = f"Step {number}"
        if not isinstance(step, dict):
            errors.append(f"{prefix}: must be an object.")
            continue

        command = step.get("command")
        if not isinstance(command, str) or not command.strip():
            errors.append(f"{prefix}: command is required.")
            continue
        _check_text(prefix, "command", command, errors, warnings)

        expected = step.get("expected") or []
        unexpected = step.get("unexpected") or []
        for field, values in (("expected", expected), ("unexpected", unexpected)):
            if not _is_string_list(values):
                errors.append(f"{prefix}: {field} must be a list of non-empty strings.")
                continue
            for value in values:
                _check_text(prefix, field, value, errors, warnings)

        timeout = step.get("timeout")
        timeout_continue = step.get("timeout_continue")
        if timeout is not None and timeout_continue is not None:
            errors.append(f"{prefix}: use either timeout or timeout_continue, not both.")
        for field, value in (("timeout", timeout), ("timeout_continue", timeout_continue)):
            if value is None:
                continue
            if not _is_int(value):
                errors.append(f"{prefix}: {field} must be a whole number of seconds.")
            elif not TIMEOUT_MIN < value < TIMEOUT_MAX:
                warnings.append(
                    f"{prefix}: {field} {value} is outside the documented range (>60 and <3600 seconds); "
                    "confirm what your runner accepts."
                )

        if STATE_CHANGE.search(command):
            warnings.append(f"{prefix}: command looks state-changing; get operator review and an approved change window.")
        if not expected:
            warnings.append(f"{prefix}: no expected response, so this step cannot confirm success.")
        elif isinstance(expected, list) and any(isinstance(v, str) and ERROR_WORDS.search(v) for v in expected):
            warnings.append(f"{prefix}: an expected string looks like an error message; confirm this is intended.")

    return {"valid": not errors, "errors": errors, "warnings": list(dict.fromkeys(warnings))}


def render_tdr(spec: dict[str, Any]) -> str:
    result = validate_spec(spec)
    if not result["valid"]:
        raise ValueError("; ".join(result["errors"]))

    lines = [
        "*" * 79,
        "* Generated by tdrgen. Review every command and expected response before use.",
        "*" * 79,
    ]
    global_unexpected = spec.get("global_unexpected") or []
    lines.extend(f"GU:{value.strip()}" for value in global_unexpected)
    if global_unexpected:
        lines.append("")

    for step in spec["steps"]:
        comment = (step.get("comment") or "").strip()
        lines.extend(f"* {line}" for line in comment.splitlines())
        lines.append(f"C:{step['command'].strip()}")
        if step.get("timeout") is not None:
            lines.append(f"T:{step['timeout']}")
        elif step.get("timeout_continue") is not None:
            lines.append(f"TC:{step['timeout_continue']}")
        lines.extend(f"E:{value.strip()}" for value in step.get("expected") or [])
        lines.extend(f"LU:{value.strip()}" for value in step.get("unexpected") or [])
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    if not text.isascii():
        raise ValueError("TDR output must be ASCII; remove non-ASCII characters from comments.")
    return text


def _parse_timeout(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def parse_tdr(text: str) -> dict[str, Any]:
    global_unexpected: list[str] = []
    steps: list[dict[str, Any]] = []
    warnings: list[str] = []
    current: dict[str, Any] | None = None

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(COMMENT_PREFIXES):
            continue
        key, sep, value = line.partition(":")
        key = key.strip().upper()
        if not sep or key not in RECORD_KEYS:
            warnings.append(f"Line {lineno}: not a comment and does not start with a TDR key; the runner will reject or ignore it.")
            continue
        value = value.strip()

        if key == "GU":
            global_unexpected.append(value)
        elif key == "C":
            current = {"line": lineno, "command": value, "timeout": None, "timeout_continue": None,
                       "expected": [], "unexpected": []}
            steps.append(current)
        elif current is None:
            warnings.append(f"Line {lineno}: {key}: appears before any C: command.")
        elif key == "E":
            current["expected"].append(value)
        elif key == "LU":
            current["unexpected"].append(value)
        elif key == "T":
            current["timeout"] = _parse_timeout(value)
        elif key == "TC":
            current["timeout_continue"] = _parse_timeout(value)

    return {"global_unexpected": global_unexpected, "steps": steps, "warnings": warnings}


ENTRY_SPLIT = re.compile(r"\s*(?:->|=>|\|)\s*")
ENTRY_BULLET = re.compile(r"^\s*(?:[-\u2022]\s+|\d+[.)]\s+)")
TDR_KEY_LINE = re.compile(r"^\s*(?:GU|C|T|TC|E|LU):", re.IGNORECASE)
EXPECTED_CAP = 6


def parse_entries(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    if any(TDR_KEY_LINE.match(line) for line in text.splitlines()):
        parsed = parse_tdr(text)
        entries = [
            {
                "command": step["command"],
                "expected": step["expected"],
                "unexpected": step["unexpected"],
                "timeout": step["timeout"] if isinstance(step["timeout"], int) else None,
            }
            for step in parsed["steps"]
            if step["command"]
        ]
        return entries, parsed["global_unexpected"]

    entries = []
    for raw in text.splitlines():
        line = ENTRY_BULLET.sub("", raw).strip()
        if not line or line.startswith(COMMENT_PREFIXES):
            continue
        command, *rest = ENTRY_SPLIT.split(line, maxsplit=1)
        expected = [part.strip() for part in rest[0].split(";") if part.strip()] if rest else []
        if command.strip():
            entries.append({"command": " ".join(command.split()), "expected": expected})
    return entries, []


def _as_entry(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        return {"command": " ".join(item.split())}
    if isinstance(item, dict):
        entry = dict(item)
        entry["command"] = " ".join(str(entry.get("command", "")).split())
        return entry
    raise ValueError("Each entry must be a command string or an object with a 'command' field.")


def _ascii(text: str) -> str:
    return text.encode("ascii", errors="replace").decode("ascii")


def generate_tdr_from_commands(
    entries: list[Any],
    catalog: list[dict[str, str]],
    default_timeout: int = 120,
    global_unexpected: list[str] | None = None,
    ibm: Any = None,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    steps: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []

    for item in entries:
        entry = _as_entry(item)
        command = entry["command"]
        if not command:
            continue

        expected = [value for value in entry.get("expected") or [] if str(value).strip()]
        status, source, note = "user-provided", "User input", "Expected strings supplied with the entry."
        review = False

        if not expected:
            hints = recommend(command, catalog, limit=EXPECTED_CAP * 2)
            exact = [h for h in hints if h.match_type == "exact" and h.response.strip()]
            family = [h for h in hints if h.match_type != "exact" and h.response.strip()]
            if exact:
                expected = list(dict.fromkeys(h.response for h in exact))[:EXPECTED_CAP]
                status, source = "catalog-exact", "Response catalog"
                note = f"Observed {max(h.count for h in exact)}x in historical runs of this exact command."
            else:
                resolved = ibm.resolve_expected(command) if ibm is not None else None
                if resolved and resolved["status"] == "ibm-example":
                    expected = resolved["expected"]
                    status, source, note = resolved["status"], "IBM z/TPF documentation", resolved["note"]
                elif resolved and resolved["status"] == "ibm-candidate":
                    expected = resolved["expected"]
                    status, source, note = resolved["status"], "IBM z/TPF documentation", resolved["note"]
                    review = True
                elif family:
                    expected = [family[0].response]
                    status, source = "catalog-family-candidate", "Response catalog"
                    note = f"Seen for a related command ({family[0].command}); parameters differ, so confirm it."
                    review = True
                else:
                    status, source = "unresolved", "None"
                    note = resolved["note"] if resolved else "No response found locally or in IBM documentation."
                    review = True

        placeholder = not expected
        if placeholder:
            expected = ["<EXPECTED_RESPONSE>"]

        state_change = bool(STATE_CHANGE.search(command)) or bool(ibm is not None and ibm.is_state_change(command))
        comment_lines = []
        if review or placeholder:
            comment_lines.append(f"REVIEW: {note}")
        if state_change:
            comment_lines.append("CAUTION: state-changing command; operator approval and a change window are required.")

        step: dict[str, Any] = {
            "command": command,
            "expected": expected,
            "unexpected": list(entry.get("unexpected") or []),
        }
        timeout = entry.get("timeout")
        step["timeout"] = timeout if isinstance(timeout, int) and not isinstance(timeout, bool) else default_timeout
        if comment_lines:
            step["comment"] = _ascii("\n".join(comment_lines))
        steps.append(step)
        details.append({
            "command": command,
            "expected": expected,
            "status": status,
            "source": source,
            "note": note,
            "is_state_change": state_change,
        })

    spec = {"global_unexpected": list(global_unexpected or []), "steps": steps}
    report = validate_spec(spec)
    tdr_text = render_tdr(spec) if report["valid"] else ""
    return tdr_text, report, details
