from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from .config import Settings
from .engine import (
    generate_tdr_from_commands,
    load_catalog,
    parse_entries,
    parse_tdr,
    recommend,
    render_tdr,
    validate_spec,
)
from .feedback import RESULTS, feedback_for_command, record_feedback, recent_feedback
from .ibm_docs import IBMDocs, IBMDocsError


def _load_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read {path}: {exc}")


def _print_report(report: dict) -> None:
    for error in report["errors"]:
        print(f"error:   {error}")
    for warning in report["warnings"]:
        print(f"warning: {warning}")
    print("valid" if report["valid"] else "invalid")


def cmd_recommend(args: argparse.Namespace, settings: Settings) -> int:
    reviewed = feedback_for_command(settings.feedback_db, args.command, limit=args.limit)
    observed = recommend(args.command, load_catalog(settings.catalog_path), limit=args.limit)
    if not reviewed and not observed:
        print("No match. Take expected strings from an approved runbook or a verified test run.")
        return 1
    for row in reviewed:
        print(f"[reviewed: {row['result']}] {row['command']} -> {row['expected_response']}"
              f"  ({row['reviewer']}, {row['system_name']}, {row['created_at']})")
    for i, rec in enumerate(observed, 1):
        print(f"{i}. {rec.command} -> {rec.response}")
        print(f"   {rec.match_type}, {rec.confidence}, seen {rec.count}x")
    if observed:
        print(f"\nNote: {observed[0].caveat}")
    return 0


def cmd_validate(args: argparse.Namespace, settings: Settings) -> int:
    report = validate_spec(_load_json(args.spec))
    _print_report(report)
    return 0 if report["valid"] else 2


def cmd_generate(args: argparse.Namespace, settings: Settings) -> int:
    spec = _load_json(args.spec)
    report = validate_spec(spec)
    _print_report(report)
    if not report["valid"]:
        return 2
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_tdr(spec), encoding="ascii", newline="\n")
    print(f"Wrote {args.output}. Operator review is required before use.")
    return 0


def cmd_build(args: argparse.Namespace, settings: Settings) -> int:
    catalog = load_catalog(settings.catalog_path)
    entries, global_unexpected = parse_entries("\n".join(args.commands))
    global_unexpected = [*global_unexpected, *(args.unexpected or [])]
    if args.file:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            raise SystemExit(f"Cannot read {args.file}: {exc}")
        file_entries, file_unexpected = parse_entries(text)
        entries += file_entries
        global_unexpected += file_unexpected
    if not entries:
        raise SystemExit("Give at least one command or use --file.")

    tdr_text, report, details = generate_tdr_from_commands(
        entries, catalog, default_timeout=args.timeout,
        global_unexpected=global_unexpected, ibm=IBMDocs.from_settings(settings),
    )
    _print_report(report)
    if not report["valid"]:
        return 2
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(tdr_text, encoding="ascii", newline="\n")
    print(f"Wrote {args.output} with {len(details)} step(s).")
    for item in details:
        print(f"  {item['command']} -> {', '.join(item['expected'])}  [{item['source']}: {item['status']}]")
        if item["status"] not in ("user-provided", "catalog-exact", "ibm-example"):
            print(f"      review: {item['note']}")
        if item["is_state_change"]:
            print("      caution: state-changing command, operator approval required")
    return 0


def cmd_ibm(args: argparse.Namespace, settings: Settings) -> int:
    docs = IBMDocs.from_settings(settings)
    try:
        page = docs.page(args.command, refresh=args.refresh)
    except IBMDocsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if page is None:
        print(f"{args.command} is not in the IBM z/TPF command index.")
        return 1
    print(page.to_markdown())
    return 0


def cmd_inspect(args: argparse.Namespace, settings: Settings) -> int:
    text = Path(args.tdr).read_text(encoding="ascii", errors="replace")
    print(json.dumps(parse_tdr(text), indent=2))
    return 0


def _print_reply(reply, verbose: bool) -> None:
    if verbose and reply.tool_calls:
        names = ", ".join(call.name for call in reply.tool_calls)
        print(f"[tools: {names}]\n", file=sys.stderr)
    print(reply.text)


def cmd_ask(args: argparse.Namespace, settings: Settings) -> int:
    from .assistant import Assistant, AssistantError

    try:
        reply = Assistant(settings).ask(args.question)
    except AssistantError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _print_reply(reply, args.verbose)
    return 0


def cmd_chat(args: argparse.Namespace, settings: Settings) -> int:
    from .assistant import Assistant, AssistantError

    assistant = Assistant(settings)
    mode = f"Claude ({settings.model})" if assistant.online else "offline search (ANTHROPIC_API_KEY not set)"
    print(f"z/TPF assistant - {mode}. Type 'exit' to quit, 'reset' to clear the conversation.")
    history: list[dict[str, str]] = []
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            return 0
        if question.lower() == "reset":
            history.clear()
            print("Conversation cleared.")
            continue
        try:
            reply = assistant.ask(question, history)
        except AssistantError as exc:
            print(f"error: {exc}")
            continue
        print()
        _print_reply(reply, args.verbose)
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": reply.text}]


def cmd_sources(args: argparse.Namespace, settings: Settings) -> int:
    from .knowledge import KnowledgeBase

    kb = KnowledgeBase.from_directory(settings.knowledge_dir, load_catalog(settings.catalog_path))
    print(f"{settings.knowledge_dir}: {len(kb.sources)} documents, {len(kb.passages)} passages")
    for source in kb.sources:
        print(f"  {source}")
    for source in kb.skipped:
        print(f"  {source} (skipped: unsupported format or missing pypdf)")
    return 0


def cmd_feedback_add(args: argparse.Namespace, settings: Settings) -> int:
    item = {key: getattr(args, key) for key in (
        "command", "expected_response", "actual_response", "result", "system_name",
        "ztpf_release", "environment", "source_file", "reviewer", "notes",
    )}
    try:
        row_id = record_feedback(settings.feedback_db, item)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Saved feedback #{row_id}.")
    return 0


def cmd_feedback_list(args: argparse.Namespace, settings: Settings) -> int:
    if args.command:
        rows = feedback_for_command(settings.feedback_db, args.command, args.limit)
    else:
        rows = recent_feedback(settings.feedback_db, args.limit)
    if not rows:
        print("No feedback recorded.")
    for row in rows:
        print(f"#{row['id']} {row['created_at']} [{row['result']}] {row['command']} -> "
              f"{row['expected_response']} ({row['reviewer'] or '-'})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tdrgen", description="z/TPF TDR script tooling with a Claude assistant.")
    parser.add_argument("--model", help="Claude model ID (default: $ANTHROPIC_MODEL or built-in default)")
    parser.add_argument("--catalog", type=Path, help="Response catalog CSV")
    parser.add_argument("--knowledge-dir", type=Path, help="Folder of documents the assistant can search")
    parser.add_argument("--db", type=Path, help="Feedback SQLite database")
    parser.add_argument("--no-ibm", action="store_true", help="Do not fetch IBM z/TPF documentation")
    sub = parser.add_subparsers(dest="action", required=True)

    p = sub.add_parser("recommend", help="Show reviewed and observed responses for a command")
    p.add_argument("command")
    p.add_argument("--limit", type=int, default=8)
    p.set_defaults(func=cmd_recommend)

    p = sub.add_parser("validate", help="Validate a JSON spec")
    p.add_argument("spec")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("generate", help="Render a JSON spec as a .TDR file")
    p.add_argument("spec")
    p.add_argument("-o", "--output", default="generated.tdr")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("build", help="Generate a .TDR file directly from command entries")
    p.add_argument("commands", nargs="*", help="Commands, optionally 'COMMAND -> EXPECTED1; EXPECTED2'")
    p.add_argument("-f", "--file", help="Text file with one entry per line (or an existing .TDR file)")
    p.add_argument("-u", "--unexpected", action="append", help="Global unexpected string (GU:), repeatable")
    p.add_argument("-t", "--timeout", type=int, default=120, help="Default timeout in seconds")
    p.add_argument("-o", "--output", default="generated.tdr", help="Output .tdr file path")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("ibm", help="Show the IBM z/TPF documentation page for a command")
    p.add_argument("command")
    p.add_argument("--refresh", action="store_true", help="Ignore the local cache")
    p.set_defaults(func=cmd_ibm)

    p = sub.add_parser("inspect", help="Parse a .TDR file")
    p.add_argument("tdr")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("ask", help="Ask the assistant one question")
    p.add_argument("question")
    p.add_argument("-v", "--verbose", action="store_true", help="Show which tools were used")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("chat", help="Interactive conversation with the assistant")
    p.add_argument("-v", "--verbose", action="store_true", help="Show which tools were used")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("sources", help="List documents in the knowledge folder")
    p.set_defaults(func=cmd_sources)

    feedback = sub.add_parser("feedback", help="Record or list human-reviewed outcomes")
    feedback_sub = feedback.add_subparsers(dest="feedback_action", required=True)

    p = feedback_sub.add_parser("add", help="Record a reviewed outcome")
    p.add_argument("--command", required=True)
    p.add_argument("--expected", dest="expected_response", required=True)
    p.add_argument("--result", choices=RESULTS, required=True)
    p.add_argument("--actual", dest="actual_response")
    p.add_argument("--system", dest="system_name")
    p.add_argument("--release", dest="ztpf_release")
    p.add_argument("--environment")
    p.add_argument("--source-file")
    p.add_argument("--reviewer")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_feedback_add)

    p = feedback_sub.add_parser("list", help="List recorded outcomes")
    p.add_argument("--command")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_feedback_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)

    settings = Settings.from_env()
    overrides = {
        "model": args.model,
        "catalog_path": args.catalog,
        "knowledge_dir": args.knowledge_dir,
        "feedback_db": args.db,
    }
    settings = replace(settings, **{k: v for k, v in overrides.items() if v})
    if args.knowledge_dir:
        settings = replace(settings, ibm_docs_dir=args.knowledge_dir / "ibm_docs")
    if args.no_ibm:
        settings = replace(settings, ibm_fallback=False)
    return args.func(args, settings)


if __name__ == "__main__":
    raise SystemExit(main())
