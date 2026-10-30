from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from .policy import CATALOG_FILE

TEXT_SUFFIXES = {".md", ".txt", ".tdr", ".rst", ".csv", ".log", ".json"}
HTML_SUFFIXES = {".html", ".htm"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | HTML_SUFFIXES | {".pdf"}
MAX_PASSAGE_CHARS = 1500
COMMAND_HEADING = re.compile(r"^\s*(?:#+\s*)?(Z[A-Z0-9]{2,7}(?:\s+[A-Z0-9]{2,12}){0,3}):\s+(\S.*?)\s*$")
MIN_COMMAND_SECTIONS = 3

_TOKEN = re.compile(r"[a-z0-9][a-z0-9_/.\-]*")
_SPLIT = re.compile(r"[/.\-_]")
_STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i in is it me of on or show tell "
    "that the this to what when where which who why with you your".split()
)


@dataclass(frozen=True)
class Passage:
    source: str
    heading: str
    text: str


@dataclass(frozen=True)
class SearchHit:
    passage: Passage
    score: float


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        word = raw.strip("./-_")
        if not word or word in _STOPWORDS:
            continue
        tokens.append(word)
        parts = [part for part in _SPLIT.split(word) if part and part not in _STOPWORDS]
        if len(parts) > 1:
            tokens.extend(parts)
    return tokens


class _HTMLText(HTMLParser):
    BLOCK_TAGS = {"p", "div", "br", "li", "tr", "pre", "section", "article", "table", "ul", "ol",
                  "h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP_TAGS = {"script", "style", "head", "nav", "footer", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self.SKIP_TAGS:
            self._skip += 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _HTMLText()
    parser.feed(markup)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def read_document(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix in HTML_SUFFIXES:
        return html_to_text(path.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return None
    return None


def _pieces(block: str, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]
    pieces, current, size = [], [], 0
    for line in block.splitlines():
        if current and size + len(line) > max_chars:
            pieces.append("\n".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        pieces.append("\n".join(current))
    return pieces


def split_passages(text: str, source: str, max_chars: int = MAX_PASSAGE_CHARS) -> list[Passage]:
    passages: list[Passage] = []
    heading = ""
    buffer: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal buffer, size
        body = "\n\n".join(buffer).strip()
        if body:
            passages.append(Passage(source, heading, body))
        buffer, size = [], 0

    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        if block.startswith("#"):
            flush()
            first, _, rest = block.partition("\n")
            heading = first.lstrip("#").strip()
            block = rest.strip()
            if not block:
                continue
        for piece in _pieces(block, max_chars):
            if buffer and size + len(piece) > max_chars:
                flush()
            buffer.append(piece)
            size += len(piece)
    flush()
    return passages


CATALOG_SOURCE = "response_catalog.csv"


def catalog_passages(rows: list[dict[str, str]], max_chars: int = MAX_PASSAGE_CHARS) -> list[Passage]:
    grouped: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        command = " ".join(row.get("command", "").split()).upper()
        response = row.get("observed_expected_response", "").strip()
        if not command or not response:
            continue
        grouped.setdefault(command.split()[0], {}).setdefault(command, {})[response] = (
            f"observed {row.get('observed_count') or 1} time(s)"
        )

    passages: list[Passage] = []
    for family in sorted(grouped):
        lines = [
            f"{command} -> " + "; ".join(f"{resp} ({seen})" for resp, seen in responses.items())
            for command, responses in sorted(grouped[family].items())
        ]
        header = f"Responses observed in past runs for the {family} command family."
        buffer: list[str] = []
        size = 0
        for line in lines:
            if buffer and size + len(line) > max_chars:
                passages.append(Passage(CATALOG_SOURCE, family, header + "\n" + "\n".join(buffer)))
                buffer, size = [], 0
            buffer.append(line)
            size += len(line) + 1
        if buffer:
            passages.append(Passage(CATALOG_SOURCE, family, header + "\n" + "\n".join(buffer)))
    return passages


class KnowledgeBase:
    def __init__(self, passages: list[Passage], skipped: list[str] | None = None, k1: float = 1.5, b: float = 0.75):
        self.passages = passages
        self.skipped = skipped or []
        self._k1 = k1
        self._b = b
        self._term_counts = [Counter(tokenize(f"{p.heading}\n{p.text}")) for p in passages]
        self._lengths = [sum(counts.values()) for counts in self._term_counts]
        self._avg_length = sum(self._lengths) / len(self._lengths) if passages else 0.0

        document_frequency: Counter[str] = Counter()
        for counts in self._term_counts:
            document_frequency.update(counts.keys())
        total = len(passages)
        self._idf = {
            term: math.log(1 + (total - freq + 0.5) / (freq + 0.5))
            for term, freq in document_frequency.items()
        }

    @classmethod
    def from_directory(cls, directory: str | Path, catalog: list[dict[str, str]] | None = None) -> KnowledgeBase:
        root = Path(directory)
        passages: list[Passage] = catalog_passages(catalog) if catalog else []
        skipped: list[str] = []
        if root.is_dir():
            for path in sorted(p for p in root.rglob("*") if p.is_file()):
                relative = path.relative_to(root).as_posix()
                if path.name.startswith("."):
                    continue
                text = read_document(path)
                if text is None:
                    skipped.append(relative)
                    continue
                passages.extend(split_passages(text, relative))
        return cls(passages, skipped)

    @property
    def sources(self) -> list[str]:
        return sorted({passage.source for passage in self.passages})

    def search(self, query: str, limit: int = 5) -> list[SearchHit]:
        terms = set(tokenize(query))
        if not terms or not self.passages:
            return []

        hits: list[SearchHit] = []
        for passage, counts, length in zip(self.passages, self._term_counts, self._lengths):
            score = 0.0
            for term in terms:
                frequency = counts.get(term)
                if not frequency:
                    continue
                norm = 1 - self._b + self._b * length / self._avg_length
                score += self._idf[term] * frequency * (self._k1 + 1) / (frequency + self._k1 * norm)
            if score > 0:
                hits.append(SearchHit(passage, round(score, 3)))

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]
