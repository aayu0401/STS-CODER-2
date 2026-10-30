from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .knowledge import html_to_text

CONTENT_API = "https://www.ibm.com/docs/api/v1/content/"
PUBLIC_DOCS = "https://www.ibm.com/docs/en/"
COMMAND_INDEX_FILE = "ztpf_commands_catalog.md"
SOURCE_LABEL = "IBM z/TPF documentation"
SECTION_LIMIT = 8000
MAX_EXAMPLE_CHARS = 1500

MESSAGE_ID = re.compile(r"\b[A-Z]{4}\d{4}[A-Z]\b")
_INDEX_HEADING = re.compile(r"^### (.+?): (.+)$")
_INDEX_REFERENCE = re.compile(r"^- \*\*IBM Reference\*\*: (\S+)")
_EXAMPLE = re.compile(r"User:\s*(?P<input>.+?)\s*System:\s*(?P<output>.*?)(?=\bUser:|\Z)", re.DOTALL)
_PREFIX = re.compile(r"^[A-Z0-9]+/(?=Z)")
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL)
_SHORTDESC = re.compile(r'<p class="shortdesc">(.*?)</p>', re.DOTALL)
_H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.DOTALL)
_PRE = re.compile(r"<pre[^>]*>(.*?)</pre>", re.DOTALL)
_TAGS = re.compile(r"<[^>]+>")
_SOURCE_LINE = re.compile(r"^Source: .*?(https?://\S+)\s*$", re.MULTILINE)

KEPT_SECTIONS = ("Requirements and restrictions", "Format", "Additional information")
STATE_CHANGE_VERBS = frozenset(
    "ALTER CHANGE START STOP ABORT CANCEL CYCLE DELETE INITIALIZE INIT PURGE RESET LOAD RESTORE ENABLE "
    "DISABLE ACQUIRE ACTIVATE INACTIVATE DEACTIVATE UPDATE MIGRATE DEFINE SET MODIFY RESTART RELEASE CLEAR "
    "DISMOUNT MOUNT REMOVE ADD CREATE COPY SAVE REFRESH FLUSH BYPASS SWITCH DISCARD".split()
)


class IBMDocsError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandEntry:
    command: str
    description: str
    href: str

    @property
    def url(self) -> str:
        return PUBLIC_DOCS + self.href


@dataclass(frozen=True)
class Example:
    input: str
    output: str

    @property
    def message_ids(self) -> list[str]:
        return list(dict.fromkeys(MESSAGE_ID.findall(self.output)))


@dataclass
class IBMPage:
    command: str
    title: str
    summary: str
    url: str
    sections: dict[str, str] = field(default_factory=dict)
    examples: list[Example] = field(default_factory=list)
    from_cache: bool = False

    @property
    def message_ids(self) -> list[str]:
        ids: list[str] = []
        for example in self.examples:
            ids.extend(example.message_ids)
        return list(dict.fromkeys(ids))

    def to_markdown(self) -> str:
        parts = [f"# {self.title}", f"Source: {SOURCE_LABEL} - {self.url}"]
        if self.summary:
            parts.append(f"## Summary\n\n{self.summary}")
        for name, text in self.sections.items():
            parts.append(f"## {name}\n\n{text}")
        if self.examples:
            blocks = [f"```\nUser: {ex.input}\nSystem: {ex.output}\n```" for ex in self.examples]
            parts.append("## Examples\n\n" + "\n\n".join(blocks))
        return "\n\n".join(parts) + "\n"

    def to_dict(self, section_chars: int = 3000, max_examples: int = 8) -> dict:
        return {
            "command": self.command,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": SOURCE_LABEL,
            "sections": {name: text[:section_chars] for name, text in self.sections.items()},
            "examples": [
                {"input": ex.input, "output": ex.output, "message_ids": ex.message_ids}
                for ex in self.examples[:max_examples]
            ],
            "message_ids": self.message_ids,
            "from_cache": self.from_cache,
        }


def normalize(text: str) -> str:
    return " ".join(text.upper().split())


def strip_prefix(text: str) -> str:
    return _PREFIX.sub("", normalize(text))


def _slug(command: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", command.lower()).strip("_") or "command"


def _clean(fragment: str) -> str:
    return " ".join(html.unescape(_TAGS.sub(" ", fragment)).split())


def parse_examples(text: str) -> list[Example]:
    found: list[Example] = []
    for match in _EXAMPLE.finditer(text):
        item = Example(
            " ".join(match.group("input").split()),
            match.group("output").strip()[:MAX_EXAMPLE_CHARS],
        )
        if item.input and item not in found:
            found.append(item)
    return found


def parse_page_html(markup: str, entry: CommandEntry) -> IBMPage:
    title_match = _H1.search(markup)
    title = _clean(title_match.group(1)) if title_match else f"{entry.command}: {entry.description}"
    summary_match = _SHORTDESC.search(markup)
    summary = _clean(summary_match.group(1)) if summary_match else ""

    headings = list(_H2.finditer(markup))
    sections: dict[str, str] = {}
    for index, heading in enumerate(headings):
        name = _clean(heading.group(1))
        if name not in KEPT_SECTIONS:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(markup)
        body = html_to_text(markup[heading.end():end]).strip()
        if body:
            sections[name] = body[:SECTION_LIMIT]

    examples: list[Example] = []
    for block in _PRE.findall(markup):
        for item in parse_examples(html.unescape(_TAGS.sub("", block))):
            if item not in examples:
                examples.append(item)

    return IBMPage(entry.command, title, summary, entry.url, sections, examples)


def parse_page_markdown(text: str, entry: CommandEntry) -> IBMPage:
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else entry.command
    url_match = _SOURCE_LINE.search(text)
    url = url_match.group(1) if url_match else entry.url

    sections: dict[str, str] = {}
    summary = ""
    examples: list[Example] = []
    for chunk in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        name, _, body = chunk.partition("\n")
        name, body = name.strip(), body.strip()
        if name == "Summary":
            summary = body
        elif name == "Examples":
            examples = parse_examples(body.replace("```", ""))
        elif body:
            sections[name] = body
    return IBMPage(entry.command, title, summary, url, sections, examples, from_cache=True)


def load_command_index(path: Path) -> dict[str, CommandEntry]:
    entries: dict[str, CommandEntry] = {}
    if not path.is_file():
        return entries
    pending: tuple[str, str] | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        heading = _INDEX_HEADING.match(line)
        if heading:
            pending = (heading.group(1).strip(), heading.group(2).strip())
            continue
        reference = _INDEX_REFERENCE.match(line)
        if reference and pending:
            entries.setdefault(
                normalize(pending[0]),
                CommandEntry(pending[0], pending[1], reference.group(1).split("?")[0]),
            )
            pending = None
    return entries


def http_fetch(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "curl/8.4.0", "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


class IBMDocs:
    def __init__(self, index_path: Path, cache_dir: Path, enabled: bool = True, timeout: int = 20,
                 fetcher: Callable[[str, int], str] | None = None):
        self.index = load_command_index(Path(index_path))
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        self.timeout = timeout
        self._fetch = fetcher or http_fetch
        self._families: dict[str, list[str]] = {}
        for key in self.index:
            self._families.setdefault(key.split()[0], []).append(key)

    @classmethod
    def from_settings(cls, settings, fetcher: Callable[[str, int], str] | None = None) -> IBMDocs:
        return cls(
            settings.knowledge_dir / COMMAND_INDEX_FILE,
            settings.ibm_docs_dir,
            enabled=settings.ibm_fallback,
            timeout=settings.ibm_timeout,
            fetcher=fetcher,
        )

    def find(self, command: str) -> CommandEntry | None:
        tokens = strip_prefix(command).split()
        if not tokens:
            return None
        for size in range(len(tokens), 0, -1):
            entry = self.index.get(" ".join(tokens[:size]))
            if entry and size > 1:
                return entry
        if len(tokens) > 1:
            wanted = tokens[1].split(",")[0]
            matches = [
                key for key in self._families.get(tokens[0], [])
                if len(key.split()) > 1 and len(wanted) >= 2 and key.split()[1].startswith(wanted)
            ]
            if len(matches) == 1:
                return self.index[matches[0]]
        if len(tokens) == 1 and len(self._families.get(tokens[0], [])) == 1:
            return self.index[self._families[tokens[0]][0]]
        return self.index.get(tokens[0])

    def is_state_change(self, command: str) -> bool:
        entry = self.find(command)
        if entry is None:
            return False
        words = set(re.findall(r"[A-Z]+", f"{entry.command} {entry.description}".upper()))
        return bool(words & STATE_CHANGE_VERBS)

    def _cache_path(self, entry: CommandEntry) -> Path:
        return self.cache_dir / f"{_slug(entry.command)}.md"

    def page(self, command: str, refresh: bool = False) -> IBMPage | None:
        entry = self.find(command)
        if entry is None:
            return None
        cached = self._cache_path(entry)
        if cached.is_file() and not refresh:
            return parse_page_markdown(cached.read_text(encoding="utf-8"), entry)
        if not self.enabled:
            raise IBMDocsError("IBM documentation lookup is turned off (TDRGEN_IBM_FALLBACK).")
        try:
            markup = self._fetch(CONTENT_API + entry.href + "?parsebody=true&lang=en", self.timeout)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise IBMDocsError(f"Could not reach IBM documentation for {entry.command}: {exc}") from exc
        page = parse_page_html(markup, entry)
        if not page.summary and not page.sections and not page.examples:
            raise IBMDocsError(f"IBM returned no readable content for {entry.command}.")
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cached.write_text(page.to_markdown(), encoding="utf-8")
        except OSError:
            pass
        return page

    def resolve_expected(self, command: str) -> dict | None:
        try:
            page = self.page(command)
        except IBMDocsError:
            return None
        if page is None:
            return None
        wanted = strip_prefix(command)
        exact = [ex for ex in page.examples if strip_prefix(ex.input) == wanted and ex.message_ids]
        if exact:
            return {
                "expected": exact[0].message_ids[:1],
                "status": "ibm-example",
                "note": f"IBM example for this exact command ({page.title.split(':')[0]}).",
            }
        sample = next((ex for ex in page.examples if ex.message_ids), None)
        if sample:
            return {
                "expected": sample.message_ids[:1],
                "status": "ibm-candidate",
                "note": f"Taken from the IBM example '{sample.input}'; your parameters differ, so confirm it.",
            }
        return {
            "expected": [],
            "status": "ibm-no-example",
            "note": f"IBM documents {page.command} but shows no response message; add one from a runbook.",
        }
