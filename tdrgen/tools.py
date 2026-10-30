from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Callable

from .config import Settings
from .engine import (
    generate_tdr_from_commands,
    load_catalog,
    parse_tdr,
    recommend,
    render_tdr,
    validate_spec,
)
from .feedback import feedback_for_command
from .ibm_docs import IBMDocs, IBMDocsError
from .knowledge import KnowledgeBase

POS_SUFFIX = re.compile(r"\?pos=\d+")
SPEC_SCHEMA = {
    "type": "object",
    "description": "TDR spec with a 'steps' list and an optional 'global_unexpected' list of strings.",
    "properties": {
        "global_unexpected": {"type": "array", "items": {"type": "string"}},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "expected": {"type": "array", "items": {"type": "string"}},
                    "unexpected": {"type": "array", "items": {"type": "string"}},
                    "timeout": {"type": "integer"},
                    "timeout_continue": {"type": "integer"},
                    "comment": {"type": "string"},
                },
                "required": ["command"],
            },
        },
    },
    "required": ["steps"],
}

TOOL_DEFINITIONS = [
    {
        "name": "search_knowledge",
        "description": (
            "Full-text search over the team's own z/TPF documents (runbooks, IBM manuals, notes, "
            "sample TDR scripts) stored in the knowledge folder. Returns passages with their source file. "
            "Use this first for any question about commands, messages, procedures or site conventions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords, command names or message IDs."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "lookup_command",
        "description": (
            "Look up a z/TPF command in the historical response catalog, the human-reviewed feedback "
            "database and, when neither has an exact answer, the official IBM z/TPF documentation. "
            "Use this before suggesting an expected response string for a command."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Full command text, e.g. 'ZSTAT DACS'."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["command"],
        },
    },
    {
        "name": "lookup_ibm_documentation",
        "description": (
            "Fetch the official IBM z/TPF documentation page for a command (Z entry): what it does, "
            "requirements, parameters and real example responses with message IDs. Use it whenever the "
            "local sources do not explain a command. Pages are cached locally after the first fetch."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Command text, e.g. 'ZAURS DURT' or 'ZSTAT DACS'."},
                "refresh": {"type": "boolean", "description": "Ignore the local cache and fetch again."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "validate_tdr_spec",
        "description": "Statically check a TDR spec: required fields, single-line ASCII values, timeout range, state-changing commands.",
        "input_schema": {"type": "object", "properties": {"spec": SPEC_SCHEMA}, "required": ["spec"]},
    },
    {
        "name": "render_tdr_script",
        "description": "Validate a TDR spec and render it as ASCII .TDR text. Fails with the validation errors if the spec is invalid.",
        "input_schema": {"type": "object", "properties": {"spec": SPEC_SCHEMA}, "required": ["spec"]},
    },
    {
        "name": "inspect_tdr_script",
        "description": "Parse raw .TDR text into command blocks and report lines the runner would not understand.",
        "input_schema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    },
    {
        "name": "generate_tdr_from_entries",
        "description": (
            "Build a complete .TDR script from a list of z/TPF command entries. Expected responses are "
            "resolved in this order: strings supplied with the entry, the response catalog, an exact IBM "
            "documentation example, an IBM candidate, a related catalog command. Anything not confirmed is "
            "marked REVIEW with a placeholder. The script is validated before it is returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string"},
                                    "expected": {"type": "array", "items": {"type": "string"}},
                                    "unexpected": {"type": "array", "items": {"type": "string"}},
                                    "timeout": {"type": "integer"},
                                },
                                "required": ["command"],
                            },
                        ]
                    },
                    "description": "Commands, or objects carrying user-supplied expected strings and timeouts.",
                },
                "default_timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds for each step (default 120).",
                },
                "global_unexpected": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional global unexpected strings (GU:). Only add ones the user provided.",
                },
            },
            "required": ["commands"],
        },
    },
    {
        "name": "list_knowledge_sources",
        "description": "List the documents currently indexed in the knowledge folder.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


class ToolError(Exception):
    pass


class Toolbox:
    definitions = TOOL_DEFINITIONS

    def __init__(self, settings: Settings, knowledge: KnowledgeBase | None = None,
                 catalog: list[dict[str, str]] | None = None, ibm: IBMDocs | None = None):
        self.settings = settings
        self.catalog = catalog if catalog is not None else load_catalog(settings.catalog_path)
        self.knowledge = (
            knowledge if knowledge is not None
            else KnowledgeBase.from_directory(settings.knowledge_dir, self.catalog)
        )
        self.ibm = ibm if ibm is not None else IBMDocs.from_settings(settings)
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "search_knowledge": self.search_knowledge,
            "lookup_command": self.lookup_command,
            "lookup_ibm_documentation": self.lookup_ibm_documentation,
            "validate_tdr_spec": lambda args: validate_spec(args.get("spec")),
            "render_tdr_script": self.render_tdr_script,
            "inspect_tdr_script": lambda args: parse_tdr(str(args.get("content", ""))),
            "generate_tdr_from_entries": self.generate_tdr_from_entries_handler,
            "list_knowledge_sources": self.list_knowledge_sources,
        }

    def run(self, name: str, arguments: dict[str, Any]) -> tuple[Any, bool]:
        handler = self._handlers.get(name)
        if handler is None:
            return {"error": f"Unknown tool '{name}'."}, True
        try:
            return handler(arguments or {}), False
        except (ToolError, ValueError, TypeError, KeyError) as exc:
            return {"error": str(exc)}, True

    def search_knowledge(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ToolError("query is required.")
        limit = max(1, min(int(args.get("limit") or 5), 10))
        unique = []
        seen = set()
        for hit in self.knowledge.search(query, limit=limit * 3):
            key = (hit.passage.source, hit.passage.heading, POS_SUFFIX.sub("", hit.passage.text))
            if key not in seen:
                seen.add(key)
                unique.append(hit)
        hits = unique[:limit]
        return {
            "query": query,
            "indexed_documents": len(self.knowledge.sources),
            "results": [
                {"source": h.passage.source, "section": h.passage.heading, "score": h.score, "text": h.passage.text}
                for h in hits
            ],
        }

    def ibm_page(self, command: str, refresh: bool = False) -> dict[str, Any]:
        try:
            page = self.ibm.page(command, refresh=refresh)
        except IBMDocsError as exc:
            return {"command": command, "found": False, "reason": str(exc)}
        if page is None:
            return {
                "command": command,
                "found": False,
                "reason": "The command is not in the IBM z/TPF command index.",
            }
        return {"found": True, **page.to_dict()}

    def lookup_ibm_documentation(self, args: dict[str, Any]) -> dict[str, Any]:
        command = str(args.get("command", "")).strip()
        if not command:
            raise ToolError("command is required.")
        return self.ibm_page(command, refresh=bool(args.get("refresh")))

    def lookup_command(self, args: dict[str, Any]) -> dict[str, Any]:
        command = str(args.get("command", "")).strip()
        if not command:
            raise ToolError("command is required.")
        limit = max(1, min(int(args.get("limit") or 8), 20))
        doc_hits = [
            {"source": h.passage.source, "heading": h.passage.heading, "text": h.passage.text}
            for h in self.knowledge.search(command, limit=3)
            if h.passage.source != "response_catalog.csv"
        ]
        reviewed = feedback_for_command(self.settings.feedback_db, command, limit=limit)
        observed = [asdict(rec) for rec in recommend(command, self.catalog, limit=limit)]
        result: dict[str, Any] = {
            "command": command,
            "official_documentation": doc_hits,
            "reviewed_feedback": reviewed,
            "historical_observations": observed,
        }
        has_exact_answer = bool(reviewed) or any(rec["match_type"] == "exact" for rec in observed)
        if not has_exact_answer:
            result["ibm_documentation"] = self.ibm_page(command)
        return result

    def render_tdr_script(self, args: dict[str, Any]) -> dict[str, Any]:
        spec = args.get("spec")
        report = validate_spec(spec)
        if not report["valid"]:
            return {"rendered": False, **report}
        return {"rendered": True, "warnings": report["warnings"], "tdr": render_tdr(spec)}

    def generate_tdr_from_entries_handler(self, args: dict[str, Any]) -> dict[str, Any]:
        commands = args.get("commands")
        if not commands or not isinstance(commands, list):
            raise ToolError("commands must be a non-empty list of command strings.")
        default_timeout = int(args.get("default_timeout") or 120)
        global_unexpected = args.get("global_unexpected")
        tdr_text, report, step_details = generate_tdr_from_commands(
            commands, self.catalog, default_timeout=default_timeout,
            global_unexpected=global_unexpected, ibm=self.ibm,
        )
        return {
            "tdr": tdr_text,
            "valid": report["valid"],
            "errors": report["errors"],
            "warnings": report["warnings"],
            "step_details": step_details,
        }

    def list_knowledge_sources(self, _args: dict[str, Any]) -> dict[str, Any]:
        return {
            "documents": self.knowledge.sources,
            "passages": len(self.knowledge.passages),
            "unreadable": self.knowledge.skipped,
        }
