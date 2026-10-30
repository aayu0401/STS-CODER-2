from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import streamlit as st

from tdrgen.assistant import Assistant, AssistantError
from tdrgen.config import Settings
from tdrgen.engine import (
    generate_tdr_from_commands,
    load_catalog,
    parse_entries,
    recommend,
    render_tdr,
    validate_spec,
)
from tdrgen.feedback import RESULTS, recent_feedback, record_feedback
from tdrgen.ibm_docs import IBMDocs, IBMDocsError
from tdrgen.knowledge import SUPPORTED_SUFFIXES, KnowledgeBase
from tdrgen.policy import collect_sources
from tdrgen.tools import Toolbox

APP_NAME = "STS Coder"
APP_TAGLINE = "z/TPF command knowledge and TDR script workbench"

STYLE = """
<style>
.block-container { padding-top: 2rem; max-width: 1200px; }
.app-header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 0.25rem; }
.app-header h1 { margin: 0; font-size: 1.75rem; font-weight: 650; letter-spacing: -0.01em; }
.app-header span { color: #8b98b5; font-size: 0.95rem; }
.status-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin: 1rem 0 1.25rem; }
.status-card { background: #111a2e; border: 1px solid #1f2b45; border-radius: 8px; padding: 0.7rem 0.9rem; }
.status-card .label { color: #8b98b5; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
.status-card .value { font-size: 1.25rem; font-weight: 600; margin-top: 0.1rem; }
.status-card .value.on { color: #34d399; }
.status-card .value.off { color: #fbbf24; }
button[data-baseweb="tab"] { font-weight: 550; }
div[data-testid="stExpander"] { border: 1px solid #1f2b45; border-radius: 8px; }
.welcome { text-align: center; padding: 1.5rem 1rem 0.75rem; }
.welcome h2 { margin: 0 0 0.4rem; font-size: 1.6rem; font-weight: 650; letter-spacing: -0.01em; }
.welcome p { color: #8b98b5; max-width: 46rem; margin: 0 auto; line-height: 1.5; }
div[data-testid="stChatMessage"] { border-radius: 10px; }
</style>
"""


@st.cache_resource(show_spinner="Indexing knowledge sources")
def get_knowledge(directory: str, catalog_path: str, stamp: float, _catalog: list[dict[str, str]]) -> KnowledgeBase:
    return KnowledgeBase.from_directory(directory, _catalog)


@st.cache_data
def get_catalog(path: str, stamp: float) -> list[dict[str, str]]:
    return load_catalog(path)


@st.cache_data(ttl=3600, show_spinner=False)
def list_models(api_key: str) -> list[str]:
    try:
        import anthropic

        return [model.id for model in anthropic.Anthropic(api_key=api_key).models.list(limit=100)]
    except Exception:
        return []


def newest_mtime(*paths: Path) -> float:
    stamps = [0.0]
    for path in paths:
        if path.is_file():
            stamps.append(path.stat().st_mtime)
        elif path.is_dir():
            stamps.extend(p.stat().st_mtime for p in path.rglob("*") if p.is_file())
    return max(stamps)


def sidebar(settings: Settings) -> Settings:
    st.sidebar.markdown(f"### {APP_NAME}")
    st.sidebar.caption(APP_TAGLINE)
    st.sidebar.divider()
    messages = st.session_state.get("messages", [])
    st.sidebar.markdown("**Conversation**")
    if st.sidebar.button("New conversation", disabled=not messages, width="stretch"):
        st.session_state["messages"] = []
        st.rerun()
    if messages:
        st.sidebar.download_button(
            "Export transcript",
            transcript(messages).encode("utf-8"),
            file_name="conversation.md",
            mime="text/markdown",
            width="stretch",
        )
    st.sidebar.divider()
    st.sidebar.markdown("**Claude connection**")
    api_key = st.sidebar.text_input("Anthropic API key", value=settings.api_key, type="password").strip()

    models = list_models(api_key) if api_key else []
    if models:
        index = models.index(settings.model) if settings.model in models else 0
        model = st.sidebar.selectbox("Model", models, index=index)
    else:
        model = st.sidebar.text_input("Model", value=settings.model).strip() or settings.model

    if api_key and not models:
        st.sidebar.warning("The key could not list models. Check the key and network access.")

    st.sidebar.divider()
    st.sidebar.markdown("**IBM documentation fallback**")
    ibm_fallback = st.sidebar.checkbox(
        "Check IBM docs if not found locally",
        value=settings.ibm_fallback,
        help="When local runbooks and response catalog lack an exact match, check official IBM z/TPF documentation for syntax, descriptions, restrictions, and example message IDs.",
    )
    ibm_timeout = st.sidebar.number_input(
        "IBM request timeout (sec)",
        min_value=5,
        max_value=120,
        value=settings.ibm_timeout,
        step=5,
    )

    st.sidebar.divider()
    st.sidebar.markdown("**Data locations**")
    st.sidebar.caption(f"Knowledge folder: `{settings.knowledge_dir}`")
    st.sidebar.caption(f"IBM docs cache: `{settings.ibm_docs_dir}`")
    st.sidebar.caption(f"Response catalog: `{settings.catalog_path}`")
    st.sidebar.caption(f"Feedback database: `{settings.feedback_db}`")
    return replace(
        settings,
        api_key=api_key,
        model=model,
        ibm_fallback=ibm_fallback,
        ibm_timeout=int(ibm_timeout),
    )


def status_strip(settings: Settings, knowledge: KnowledgeBase, catalog: list[dict[str, str]]) -> None:
    claude_on = bool(settings.api_key)
    cached_count = len(list(settings.ibm_docs_dir.glob("*.md"))) if settings.ibm_docs_dir.is_dir() else 0
    cards = [
        ("Assistant", "Claude connected" if claude_on else "Search only", "on" if claude_on else "off"),
        ("IBM Fallback", f"Active ({cached_count} cached)" if settings.ibm_fallback else "Disabled", "on" if settings.ibm_fallback else "off"),
        ("Indexed sources", f"{len(knowledge.sources)} / {len(knowledge.passages)} passages", ""),
        ("Catalog entries", f"{len(catalog)}", ""),
    ]
    html = "".join(
        f'<div class="status-card"><div class="label">{label}</div><div class="value {tone}">{value}</div></div>'
        for label, value, tone in cards
    )
    st.markdown(f'<div class="status-strip">{html}</div>', unsafe_allow_html=True)


SUGGESTIONS = [
    ("Explain a command", "What does ZAURS DURT do?"),
    ("Expected response", "What does ZSTAT DACS return?"),
    ("Decode a message", "What is CORE0397I?"),
    ("Is it safe to run?", "Is ZCYCL NORM safe to run?"),
    ("Build a TDR file", "Generate TDR for:\nZDSYS\nZSTAT DACS\nZAURS DURT ALL"),
    ("TDR keys", "What is the difference between T: and TC:?"),
]
ATTACH_TYPES = ["txt", "tdr", "md", "csv", "log"]
CONFIRMED_STATUSES = {"user-provided", "catalog-exact", "ibm-example"}
FENCED_TDR_BLOCK = re.compile(r"```tdr\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_tdr_block(text: str) -> str | None:
    match = FENCED_TDR_BLOCK.search(text)
    if match:
        body = match.group(1).strip()
        if any(line.startswith("C:") for line in body.splitlines()):
            return body + "\n"
    return None


def reply_tdr(message: dict) -> tuple[str | None, list[dict]]:
    details: list[dict] = []
    tdr = None
    for call in reversed(message.get("tool_calls") or []):
        result = call.result
        if call.name == "generate_tdr_from_entries" and not call.is_error and isinstance(result, dict) and result.get("valid"):
            details = result.get("step_details", [])
            tdr = result.get("tdr")
            break
    block = _extract_tdr_block(message["content"])
    return (block or tdr), details


def show_evidence(calls) -> None:
    if not calls:
        return
    sources = collect_sources(calls)
    label = "Sources: " + ", ".join(sources) if sources else f"Evidence ({len(calls)} lookups)"
    with st.expander(label):
        for call in calls:
            st.markdown(f"**{call.name}**" + ("  (error)" if call.is_error else ""))
            st.json({"input": call.arguments, "output": call.result}, expanded=False)


def show_steps(details: list[dict]) -> None:
    needs_review = sum(1 for item in details if item["status"] not in CONFIRMED_STATUSES)
    cautions = sum(1 for item in details if item["is_state_change"])
    summary = f"{len(details)} steps"
    if needs_review:
        summary += f", {needs_review} need review"
    if cautions:
        summary += f", {cautions} state-changing"
    with st.expander(f"Step sources ({summary})", expanded=bool(needs_review or cautions)):
        st.dataframe(
            [
                {
                    "Command": item["command"],
                    "Expected (E:)": ", ".join(item["expected"]),
                    "Source": item["source"],
                    "Status": item["status"],
                    "Note": item["note"],
                    "Safety": "State-changing" if item["is_state_change"] else "Read-only or unknown",
                }
                for item in details
            ],
            width="stretch",
            hide_index=True,
        )


def render_message(message: dict, key: str) -> None:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            if "\n" in message["content"]:
                st.text(message["content"])
            else:
                st.markdown(message["content"])
            return
        st.markdown(message["content"])
        tdr, details = reply_tdr(message)
        if tdr:
            st.download_button(
                "Download .TDR file",
                tdr.encode("ascii", errors="replace"),
                file_name="generated.tdr",
                mime="text/plain",
                key=f"download_{key}",
                type="primary",
            )
        if details:
            show_steps(details)
        show_evidence(message.get("tool_calls"))


def compose_prompt(submitted) -> str | None:
    if not submitted:
        return None
    if isinstance(submitted, str):
        return submitted.strip() or None
    text = (getattr(submitted, "text", "") or "").strip()
    attachments = [
        upload.getvalue().decode("utf-8", errors="replace").strip()
        for upload in (getattr(submitted, "files", None) or [])
    ]
    body = "\n".join(chunk for chunk in attachments if chunk)
    if body:
        return f"{text}\n{body}" if text else f"Generate TDR for:\n{body}"
    return text or None


def render_welcome(assistant: Assistant) -> None:
    st.markdown(
        '<div class="welcome"><h2>Ask anything about z/TPF</h2>'
        "<p>Commands and what they do, the responses to expect, system messages, TDR syntax, and ready-to-run "
        ".TDR files. If something is missing locally, the official IBM z/TPF documentation is checked.</p></div>",
        unsafe_allow_html=True,
    )
    columns = st.columns(3)
    for index, (label, prompt) in enumerate(SUGGESTIONS):
        if columns[index % 3].button(label, key=f"suggest_{index}", width="stretch", help=prompt):
            st.session_state["queued_prompt"] = prompt
            st.rerun()
    st.caption(
        "To build a TDR, paste commands one per line, write `COMMAND -> EXPECTED` to set a response yourself, "
        "or attach a .txt or .tdr file with the paperclip."
    )


def transcript(messages: list[dict]) -> str:
    parts = []
    for message in messages:
        speaker = "You" if message["role"] == "user" else "Assistant"
        parts.append(f"## {speaker}\n\n{message['content']}\n")
    return "\n".join(parts)


def assistant_tab(assistant: Assistant) -> None:
    messages = st.session_state.setdefault("messages", [])
    queued = st.session_state.pop("queued_prompt", None)

    if not assistant.online:
        st.caption("Claude is not connected. Answers come from the local knowledge base and IBM documentation.")

    for index, message in enumerate(messages):
        render_message(message, str(index))
    if not messages and not queued:
        render_welcome(assistant)

    submitted = st.chat_input(
        "Ask about a command or message, or paste commands to build a TDR",
        accept_file="multiple",
        file_type=ATTACH_TYPES,
    )
    prompt = queued or compose_prompt(submitted)
    if not prompt:
        return

    history = [{"role": m["role"], "content": m["content"]} for m in messages]
    user_message = {"role": "user", "content": prompt}
    messages.append(user_message)
    render_message(user_message, f"{len(messages)}u")

    with st.chat_message("assistant"):
        try:
            with st.spinner("Checking local sources and IBM documentation"):
                reply = assistant.ask(prompt, history)
        except AssistantError as exc:
            messages.pop()
            st.error(str(exc))
            return
        except Exception as exc:
            messages.pop()
            st.error(f"Something went wrong while answering: {exc}")
            return
    answer = {"role": "assistant", "content": reply.text, "tool_calls": reply.tool_calls}
    messages.append(answer)
    st.rerun()


def build_tab(catalog: list[dict[str, str]], ibm: IBMDocs | None = None) -> None:
    mode = st.radio(
        "Generator Mode",
        ["Quick Generator (Paste Entries)", "Step-by-Step Builder"],
        horizontal=True,
    )
    if mode == "Quick Generator (Paste Entries)":
        st.markdown("**Paste your z/TPF command entries below** (one command per line, or `CMD -> RESP1; RESP2`):")
        example_commands = "ZDSYS\nZSTAT DACS\nZAURS DURT PR1,PR2\nZTTCP DIS ALL"
        entries_text = st.text_area(
            "Command entries",
            value=st.session_state.get("quick_entries", example_commands),
            height=140,
            placeholder="ZDSYS\nZSTAT DACS\nZAURS DURT PR1,PR2\nZTTCP DIS ALL",
            key="quick_entries_area",
        )
        col1, col2 = st.columns([1, 2])
        default_t = col1.number_input("Default timeout (T: seconds)", min_value=10, max_value=3599, value=120, step=10)
        global_unexp = col2.text_input("Global unexpected (GU: optional, comma-separated)", value="", placeholder="e.g. NOT AUTHORIZED, COMMAND REJECTED")

        if st.button("Generate Final TDR File", type="primary", key="btn_quick_gen"):
            parsed_entries, parsed_unexp = parse_entries(entries_text)
            if not parsed_entries:
                st.warning("Please enter at least one command.")
                return
            unexp_list = [u.strip() for u in global_unexp.split(",") if u.strip()] + parsed_unexp
            tdr_text, report, step_details = generate_tdr_from_commands(
                parsed_entries, catalog, default_timeout=int(default_t), global_unexpected=unexp_list, ibm=ibm
            )
            for err in report["errors"]:
                st.error(err)
            for warn in report["warnings"]:
                st.warning(warn)
            if report["valid"]:
                st.success(f"Generated valid TDR script with {len(parsed_entries)} step(s).")
                st.code(tdr_text, language="text")
                st.download_button(
                    "Download Final .TDR File",
                    tdr_text.encode("ascii", errors="replace"),
                    file_name="generated.tdr",
                    mime="text/plain",
                    key="quick_dl_btn",
                )
                with st.expander("Step resolution details", expanded=True):
                    st.dataframe(
                        [
                            {
                                "Command": s["command"],
                                "Resolved Expected (E:)": ", ".join(s["expected"]),
                                "Source": s["source"],
                                "Status": s["status"],
                                "Operational Note": s["note"],
                                "Safety Caution": "CRITICAL: State Change" if s["is_state_change"] else "Safe",
                            }
                            for s in step_details
                        ],
                        width="stretch",
                        hide_index=True,
                    )
        return

    left, right = st.columns([1, 2])
    count = left.number_input("Command steps", min_value=1, max_value=50, value=1, step=1)
    global_unexpected = right.text_area("Global unexpected strings (GU:), one per line", height=68)

    steps = []
    for i in range(int(count)):
        with st.expander(f"Step {i + 1}", expanded=i == 0):
            command = st.text_input("Command (C:)", key=f"cmd_{i}", placeholder="ZSTAT DACS")
            if command.strip():
                hints = recommend(command, catalog, limit=3)
                if hints:
                    st.caption("Seen in past runs: " + "; ".join(
                        f"`{h.response}` ({h.match_type}, {h.count}x)" for h in hints))
            col_a, col_b = st.columns(2)
            use_timeout = col_a.checkbox("Set timeout (T:)", key=f"use_t_{i}")
            timeout = (
                col_b.number_input("Seconds", min_value=61, max_value=3599, value=120, key=f"t_{i}")
                if use_timeout else None
            )
            expected = st.text_area("Expected strings (E:), one per line", key=f"exp_{i}", height=80)
            unexpected = st.text_area("Local unexpected strings (LU:), one per line", key=f"lu_{i}", height=60)
            comment = st.text_input("Comment", key=f"comment_{i}")
            steps.append({
                "command": command,
                "timeout": int(timeout) if timeout is not None else None,
                "expected": [line.strip() for line in expected.splitlines() if line.strip()],
                "unexpected": [line.strip() for line in unexpected.splitlines() if line.strip()],
                "comment": comment,
            })

    if not st.button("Validate and generate", type="primary"):
        return
    spec = {"global_unexpected": [l.strip() for l in global_unexpected.splitlines() if l.strip()], "steps": steps}
    report = validate_spec(spec)
    for error in report["errors"]:
        st.error(error)
    for warning in report["warnings"]:
        st.warning(warning)
    if report["valid"]:
        tdr = render_tdr(spec)
        st.code(tdr, language="text")
        st.download_button("Download .TDR", tdr.encode("ascii"), file_name="generated.tdr", mime="text/plain")


def lookup_tab(catalog: list[dict[str, str]], ibm: IBMDocs | None = None) -> None:
    command = st.text_input("Command", placeholder="ZSTAT DACS", key="lookup_command").strip()
    if not command:
        st.caption("Enter a command to see recorded responses and official IBM documentation.")
        return
    matches = recommend(command, catalog, limit=15)
    exact_matches = [m for m in matches if m.match_type == "exact"]
    if matches:
        st.markdown("**Historical response catalog**")
        st.dataframe(
            [{"Command": m.command, "Response": m.response, "Match": m.match_type,
              "Confidence": m.confidence, "Seen": m.count} for m in matches],
            width="stretch",
            hide_index=True,
        )
        st.caption(matches[0].caveat)

    if ibm is None:
        return

    if not exact_matches:
        st.info("No exact match in the local response catalog. Checking official IBM z/TPF documentation...")

    try:
        page = ibm.page(command)
    except IBMDocsError as exc:
        st.warning(f"IBM documentation lookup: {exc}")
        return

    if page is not None:
        st.markdown(f"### {page.title}")
        st.caption(f"Source: [{page.url}]({page.url})")
        if ibm.is_state_change(command):
            st.error("Caution: State-changing command. Requires operator approval and change window.")
        if page.summary:
            st.markdown(f"**Summary:** {page.summary}")
        for sec_name, sec_body in page.sections.items():
            with st.expander(sec_name, expanded=sec_name in ("Requirements and restrictions", "Format")):
                st.text(sec_body)
        if page.examples:
            st.markdown("**Official IBM Examples & Message IDs:**")
            for ex in page.examples:
                ids = ", ".join(ex.message_ids) or "None"
                st.markdown(f"- Input: `{ex.input}` -> Expected Message IDs: `{ids}`")
                with st.expander(f"Example output for `{ex.input}`"):
                    st.code(f"User: {ex.input}\nSystem: {ex.output}", language="text")
    elif not matches:
        st.warning("Command not found in local catalog or IBM z/TPF index.")


def feedback_tab(settings: Settings) -> None:
    st.caption("A verified record requires the actual response, reviewer, system, z/TPF release and environment.")
    with st.form("feedback", clear_on_submit=True):
        left, right = st.columns(2)
        command = left.text_input("Command")
        expected = right.text_input("Expected response")
        actual = st.text_area("Actual host response", height=80)
        result = left.selectbox("Result", RESULTS, index=2)
        environment = right.selectbox("Environment", ["test", "staging", "production"])
        system = left.text_input("System / subsystem")
        release = right.text_input("z/TPF release")
        reviewer = left.text_input("Reviewer")
        source_file = right.text_input("Source TDR file")
        notes = st.text_area("Notes", height=60)
        submitted = st.form_submit_button("Save record", type="primary")

    if submitted:
        record = {
            "command": command, "expected_response": expected, "actual_response": actual,
            "result": result, "system_name": system, "ztpf_release": release, "environment": environment,
            "source_file": source_file, "reviewer": reviewer, "notes": notes,
        }
        try:
            row_id = record_feedback(settings.feedback_db, record)
            st.success(f"Saved record {row_id}.")
        except ValueError as exc:
            st.error(str(exc))

    rows = recent_feedback(settings.feedback_db, limit=25)
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
        st.download_button("Export JSON", json.dumps(rows, indent=2), file_name="feedback.json",
                           mime="application/json")
    else:
        st.caption("No records yet.")


def knowledge_tab(settings: Settings, knowledge: KnowledgeBase) -> None:
    st.caption(
        "Documents added here become searchable by the assistant: runbooks, IBM manuals, message references, "
        "past TDR scripts and incident notes. PDF files require the pypdf package."
    )
    uploads = st.file_uploader(
        "Add documents",
        type=sorted(s.lstrip(".") for s in SUPPORTED_SUFFIXES),
        accept_multiple_files=True,
    )
    if uploads and st.button("Save to knowledge folder"):
        settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
        for upload in uploads:
            (settings.knowledge_dir / Path(upload.name).name).write_bytes(upload.getvalue())
        st.success(f"Saved {len(uploads)} file(s).")
        st.rerun()

    st.dataframe(
        [{"Source": s, "Passages": sum(1 for p in knowledge.passages if p.source == s)} for s in knowledge.sources]
        + [{"Source": f"{s} (unreadable)", "Passages": 0} for s in knowledge.skipped],
        width="stretch",
        hide_index=True,
    )

    query = st.text_input("Test a search", key="kb_query", placeholder="CORE0397I")
    for hit in knowledge.search(query, limit=5) if query else []:
        st.markdown(f"**{hit.passage.source}**  {hit.passage.heading}  (score {hit.score})")
        st.text(hit.passage.text[:800])


def main() -> None:
    st.set_page_config(page_title=f"{APP_NAME} | z/TPF Workbench", layout="wide")
    st.markdown(STYLE, unsafe_allow_html=True)

    settings = sidebar(Settings.from_env())
    catalog_stamp = newest_mtime(settings.catalog_path)
    catalog = get_catalog(str(settings.catalog_path), catalog_stamp)
    knowledge = get_knowledge(
        str(settings.knowledge_dir), str(settings.catalog_path),
        newest_mtime(settings.knowledge_dir, settings.catalog_path), catalog,
    )
    assistant = Assistant(settings, Toolbox(settings, knowledge=knowledge, catalog=catalog))

    st.markdown(
        f'<div class="app-header"><h1>{APP_NAME}</h1><span>{APP_TAGLINE}</span></div>',
        unsafe_allow_html=True,
    )
    status_strip(settings, knowledge, catalog)

    views = ["Chat", "TDR builder", "Command lookup", "Review log", "Knowledge"]
    view = st.segmented_control("View", views, default="Chat", label_visibility="collapsed") or "Chat"
    if view == "Chat":
        assistant_tab(assistant)
    elif view == "TDR builder":
        build_tab(catalog, assistant.toolbox.ibm)
    elif view == "Command lookup":
        lookup_tab(catalog, assistant.toolbox.ibm)
    elif view == "Review log":
        feedback_tab(settings)
    else:
        knowledge_tab(settings, knowledge)

if __name__ == "__main__":
    main()
