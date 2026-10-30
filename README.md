# STS Coder

Tooling for z/TPF `.TDR` command scripts, plus an advanced assistant that answers questions about
z/TPF using official IBM product documentation, system runbooks, message catalogs, and verified operational data.

- Generate, validate and inspect `.TDR` scripts conforming to the IBM RAVEN runner specification.
- Ingested 1,947 official IBM z/TPF product command definitions across all command families (ZAxxx through ZZxxx),
  including functional descriptions, subcommand parameters, and operational safety classifications.
- Query historical command-to-response patterns (625 verified pairs across 184 command families) without exposing
  raw test script filenames.
- Enforce strict operational rules and regulations: state-changing commands require operator authorization,
  hallucinations are forbidden, and syntax is strictly validated against single-line ASCII runner standards.
- Record human-reviewed outcomes in SQLite so verified operator runbook knowledge outranks raw samples.
- Chat with Claude using a 6-tool autonomous agent loop, with automatic offline fallback to local BM25 search
  when an API key is not supplied.

The tool produces and checks text only. It never connects directly to a live host without authorization.

## How the assistant stays accurate

Claude relies on indexed reference sources rather than memory. It uses specialized tools and a strict
policy system prompt that ranks evidence in this order:

1. Reviewed operator feedback (outcomes confirmed by a named reviewer).
2. Official IBM z/TPF product documentation and runbooks in the `knowledge/` directory.
3. Responses observed in the response catalog (historical operational observations).
4. General knowledge, which must be explicitly qualified as unverified.

The assistant is bound by strict operational rules:
- Grounding: Always query indexed sources before formulating responses.
- Attribution: Never expose or cite raw test script filenames; attribute to official IBM documentation or the catalog.
- Safety: Flag every state-changing command (IPL, CYCLE, ALTER, LOAD, START, STOP, VARY, etc.) with operational warnings.
- No fabrication: Never invent parameters or response strings; use explicit placeholders when confirmation is needed.
- TDR Compliance: Ensure generated scripts conform strictly to single-line ASCII records and documented timeout rules.

## Setup

Python 3.10 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

The generator, validator, parser, catalog lookup, IBM fallback and feedback store need no third-party packages.
Without an API key the assistant falls back to a plain search of local sources and official IBM documentation.

## Usage

The primary interface is the interactive Chatbot workbench:

```powershell
streamlit run app.py
```

Open `http://localhost:8501` to use the chatbot interface. It features:
- Interactive conversations answering questions about any of the 1,947 z/TPF commands, what each does, format, restrictions, and expected system messages.
- Automatic lookup in official IBM z/TPF documentation whenever local runbooks and response catalogs lack an exact match.
- Paste command entries or attach a `.txt`/`.tdr` file to build a final, downloadable `.TDR` script with instant download button and per-step evidence tracking.
- Pre-built quick-action buttons for common operations ("Explain a command", "Build a TDR file", "Decode a message", etc.).
- Conversation export and one-click reset.

CLI commands are also available when needed:
```powershell
python -m tdrgen build "ZDSYS" "ZAURS DURT PR1,PR2" "ZCYCL NORM" -o output.tdr
python -m tdrgen ibm "ZAURS DURT"
python -m tdrgen ask -v "What does ZAURS DURT do?"
python -m tdrgen chat
python -m tdrgen recommend "ZSTAT DACS"
python -m tdrgen validate examples/status_check_spec.json
python -m tdrgen generate examples/status_check_spec.json -o status_check.tdr
python -m tdrgen inspect status_check.tdr
python -m tdrgen sources
python -m tdrgen feedback add --command "ZSTAT DACS" --expected STAT0007I --result needs_review
python -m tdrgen feedback list
```

`pip install -e .` also installs a `tdrgen` command.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | none | Enables Claude |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Model ID (the app lists the models your key can use) |
| `TDRGEN_IBM_FALLBACK` | `true` | Query IBM documentation when data is missing locally (set `false` to disable) |
| `TDRGEN_IBM_TIMEOUT` | `20` | Timeout in seconds for IBM documentation HTTP requests |
| `TDRGEN_KNOWLEDGE_DIR` | `knowledge/` | Documents the assistant searches |
| `TDRGEN_CATALOG` | `data/response_catalog.csv` | Historical command/response pairs |
| `TDRGEN_FEEDBACK_DB` | `data/feedback.db` | Reviewed outcomes |

Command-line flags `--model`, `--catalog`, `--knowledge-dir`, `--db` and `--no-ibm` override these.

## Layout

```
tdrgen/
  ibm_docs.py    IBM z/TPF documentation client, scraper, cache and response resolver
  engine.py      catalog lookup, entry parsing, spec validation, TDR render and parse
  feedback.py    SQLite store for reviewed outcomes
  knowledge.py   document loading and BM25 search
  tools.py       tool schemas and handlers exposed to Claude
  assistant.py   Claude tool-use loop and offline fallback
  policy.py      operational rules, system prompt and safety guardrails
  cli.py         command-line interface
  config.py      settings
app.py           Streamlit UI
knowledge/       documents the assistant searches, including ibm_docs/ cache
data/            response catalog and sample inventory
examples/        spec example and universal TDR template
tests/           unit tests (hermetic, no network or API key needed)
```

## Tests

```powershell
python -m unittest discover -s tests
```

## Rules the tool enforces

- Values must be single-line ASCII; `T:`/`TC:` must be whole seconds, warned when outside >60 and <3600.
- A step cannot have both `timeout` and `timeout_continue`.
- Commands that look state-changing (IPL, LOAD, START, STOP, VARY, ALTER, RESET, ...) are warned about.
- Unfilled `<PLACEHOLDER>` text is warned about.
- A `verified` feedback record requires the actual response, reviewer, system, z/TPF release and environment.
- A catalog match is evidence about the sample files only. Matches by command family are labelled
  `candidate-only`, because parameters can change behaviour.

## Limits

- The runner decides what it accepts. The IBM page itself shows a `T:10` example that contradicts its own
  >60 rule, so confirm the range on your installed level.
- Passage search is keyword-based (BM25), not semantic. Use the exact command or message ID when searching.
- The Streamlit app has no authentication. Do not expose it to a network without adding authentication,
  authorization, audit logging and secrets management.

IBM reference: https://www.ibm.com/docs/en/ztpf/1.1.2025?topic=files-tdr-command-script-file-type
