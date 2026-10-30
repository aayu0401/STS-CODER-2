from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "claude-sonnet-5-5"
AUDIT_DISABLED_VALUES = {"off", "none", "disabled", "0", "false"}
DEFAULT_IBM_TIMEOUT = 20


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value else default


def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value not in AUDIT_DISABLED_VALUES


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, "").strip()))
    except ValueError:
        return default


def _audit_path(default: Path) -> Path | None:
    value = os.environ.get("TDRGEN_AUDIT_LOG", "").strip()
    if value.lower() in AUDIT_DISABLED_VALUES:
        return None
    return Path(value).expanduser() if value else default


@dataclass(frozen=True)
class Settings:
    api_key: str = ""
    model: str = DEFAULT_MODEL
    max_tokens: int = 4096
    catalog_path: Path = PROJECT_ROOT / "data" / "response_catalog.csv"
    knowledge_dir: Path = PROJECT_ROOT / "knowledge"
    feedback_db: Path = PROJECT_ROOT / "data" / "feedback.db"
    audit_log: Path | None = PROJECT_ROOT / "data" / "audit.jsonl"
    ibm_fallback: bool = True
    ibm_timeout: int = DEFAULT_IBM_TIMEOUT
    ibm_docs_dir: Path = PROJECT_ROOT / "knowledge" / "ibm_docs"

    @classmethod
    def from_env(cls) -> Settings:
        defaults = cls()
        knowledge_dir = _env_path("TDRGEN_KNOWLEDGE_DIR", defaults.knowledge_dir)
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "").strip(),
            model=os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_MODEL,
            catalog_path=_env_path("TDRGEN_CATALOG", defaults.catalog_path),
            knowledge_dir=knowledge_dir,
            feedback_db=_env_path("TDRGEN_FEEDBACK_DB", defaults.feedback_db),
            audit_log=_audit_path(defaults.audit_log),
            ibm_fallback=_env_flag("TDRGEN_IBM_FALLBACK", defaults.ibm_fallback),
            ibm_timeout=_env_int("TDRGEN_IBM_TIMEOUT", defaults.ibm_timeout),
            ibm_docs_dir=knowledge_dir / "ibm_docs",
        )
