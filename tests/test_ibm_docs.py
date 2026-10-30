import tempfile
import unittest
from pathlib import Path

from tdrgen.config import Settings
from tdrgen.engine import generate_tdr_from_commands, parse_entries
from tdrgen.ibm_docs import (
    CommandEntry,
    IBMDocs,
    IBMDocsError,
    load_command_index,
    parse_examples,
    parse_page_html,
    parse_page_markdown,
    strip_prefix,
)
from tdrgen.tools import Toolbox


SAMPLE_INDEX_MD = "\n".join([
    "# IBM z/TPF Commands Catalog",
    "",
    "### ZAURS DURT: Display unit record status table",
    "- **IBM Reference**: SSB23S_2025/gtpo1/cmd_zaursdurt.html",
    "- **Command Family**: ZAURS",
    "",
    "### ZCYCL NORM: Cycle system to normal state",
    "- **IBM Reference**: SSB23S_2025/gtpo1/cmd_zcyclnorm.html",
    "- **Command Family**: ZCYCL",
    "",
    "### ZTTCP DISPLAY: Display TCP/IP information",
    "- **IBM Reference**: SSB23S_2025/gtpo1/cmd_zttcpdisp.html",
    "- **Command Family**: ZTTCP",
])

SAMPLE_HTML = """\
<html>
<head><title>ZAURS DURT</title></head>
<body>
<h1>ZAURS DURT: Display unit record status table</h1>
<p class="shortdesc">Use this command to display status of unit record devices.</p>
<h2 class="sectiontitle">Requirements and restrictions</h2>
<p>Operator console authority is required.</p>
<h2 class="sectiontitle">Format</h2>
<p>ZAURS DURT [PR1|ALL]</p>
<h2 class="sectiontitle">Examples</h2>
<pre class="pre screen"><code>User: ZAURS DURT PR1,PR2

System: AURS0050I 11.05.33 UNIT RECORD STATUS
         NAME DEV  ADR STATUS
          PR1 3211 00E
</code></pre>
<pre class="pre screen"><code>User: ZAURS DURT ALL

System: AURS0050I 00.17.46 ALL RECORD STATUS
</code></pre>
</body>
</html>
"""

SAMPLE_NO_MSG_HTML = """\
<html>
<body>
<h1>ZCYCL NORM: Cycle system to normal state</h1>
<p class="shortdesc">Cycles system from 1052 to NORM state.</p>
<h2 class="sectiontitle">Format</h2>
<p>ZCYCL NORM</p>
<h2 class="sectiontitle">Examples</h2>
<pre class="pre screen"><code>User: ZCYCL NORM

System: SYSTEM IS CYCLING TO NORM
</code></pre>
</body>
</html>
"""


class IBMDocsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.index_path = self.tmp_path / "ztpf_commands_catalog.md"
        self.index_path.write_text(SAMPLE_INDEX_MD, encoding="utf-8")
        self.cache_dir = self.tmp_path / "ibm_docs"

    def tearDown(self):
        self._tmp.cleanup()

    def test_strip_prefix(self):
        self.assertEqual(strip_prefix("WP/ZDSYS"), "ZDSYS")
        self.assertEqual(strip_prefix("1A/ZSTAT DACS"), "ZSTAT DACS")
        self.assertEqual(strip_prefix("ZSTAT DACS"), "ZSTAT DACS")

    def test_load_command_index(self):
        entries = load_command_index(self.index_path)
        self.assertIn("ZAURS DURT", entries)
        self.assertIn("ZCYCL NORM", entries)
        self.assertIn("ZTTCP DISPLAY", entries)
        self.assertEqual(entries["ZAURS DURT"].href, "SSB23S_2025/gtpo1/cmd_zaursdurt.html")

    def test_find_with_prefix_and_abbreviation(self):
        docs = IBMDocs(self.index_path, self.cache_dir)
        self.assertEqual(docs.find("ZAURS DURT PR1,PR2").command, "ZAURS DURT")
        self.assertEqual(docs.find("WP/ZAURS DURT").command, "ZAURS DURT")
        self.assertEqual(docs.find("ZTTCP DIS ALL").command, "ZTTCP DISPLAY")
        self.assertEqual(docs.find("ZCYCL").command, "ZCYCL NORM")
        self.assertIsNone(docs.find("UNKNOWN CMD"))

    def test_is_state_change(self):
        docs = IBMDocs(self.index_path, self.cache_dir)
        self.assertTrue(docs.is_state_change("ZCYCL NORM"))
        self.assertFalse(docs.is_state_change("ZAURS DURT"))

    def test_parse_examples(self):
        text = "User: ZSTAT\n\nSystem: STAT0001I OK\nUser: ZDSYS\nSystem: CSMP0001I ACTIVE"
        examples = parse_examples(text)
        self.assertEqual(len(examples), 2)
        self.assertEqual(examples[0].input, "ZSTAT")
        self.assertEqual(examples[0].message_ids, ["STAT0001I"])

    def test_parse_page_html_and_markdown(self):
        entry = CommandEntry("ZAURS DURT", "Display unit record status table", "cmd_zaursdurt.html")
        page = parse_page_html(SAMPLE_HTML, entry)
        self.assertEqual(page.command, "ZAURS DURT")
        self.assertIn("Requirements and restrictions", page.sections)
        self.assertEqual(len(page.examples), 2)
        self.assertEqual(page.message_ids, ["AURS0050I"])

        md = page.to_markdown()
        self.assertIn("# ZAURS DURT", md)
        self.assertIn("AURS0050I", md)

        roundtrip = parse_page_markdown(md, entry)
        self.assertEqual(roundtrip.title, page.title)
        self.assertEqual(roundtrip.summary, page.summary)
        self.assertEqual(len(roundtrip.examples), 2)

    def test_page_fetch_and_caching(self):
        calls = []

        def fake_fetcher(url: str, timeout: int) -> str:
            calls.append(url)
            return SAMPLE_HTML

        docs = IBMDocs(self.index_path, self.cache_dir, fetcher=fake_fetcher)
        page1 = docs.page("ZAURS DURT")
        self.assertFalse(page1.from_cache)
        self.assertEqual(len(calls), 1)

        page2 = docs.page("ZAURS DURT")
        self.assertTrue(page2.from_cache)
        self.assertEqual(len(calls), 1)

    def test_disabled_docs_with_and_without_cache(self):
        docs_enabled = IBMDocs(
            self.index_path, self.cache_dir, fetcher=lambda url, timeout: SAMPLE_HTML
        )
        docs_enabled.page("ZAURS DURT")

        docs_disabled = IBMDocs(self.index_path, self.cache_dir, enabled=False)
        cached_page = docs_disabled.page("ZAURS DURT")
        self.assertIsNotNone(cached_page)

        with self.assertRaises(IBMDocsError):
            docs_disabled.page("ZCYCL NORM")

    def test_resolve_expected(self):
        docs = IBMDocs(
            self.index_path,
            self.cache_dir,
            fetcher=lambda url, timeout: SAMPLE_HTML if "zaurs" in url else SAMPLE_NO_MSG_HTML,
        )

        exact = docs.resolve_expected("ZAURS DURT PR1,PR2")
        self.assertEqual(exact["status"], "ibm-example")
        self.assertEqual(exact["expected"], ["AURS0050I"])

        cand = docs.resolve_expected("ZAURS DURT OTHER")
        self.assertEqual(cand["status"], "ibm-candidate")
        self.assertEqual(cand["expected"], ["AURS0050I"])

        no_msg = docs.resolve_expected("ZCYCL NORM")
        self.assertEqual(no_msg["status"], "ibm-no-example")
        self.assertEqual(no_msg["expected"], [])

    def test_parse_entries(self):
        plain_text = "ZDSYS\nZSTAT DACS\nZAURS DURT -> AURS0050I; STAT0001I"
        entries, unexp = parse_entries(plain_text)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["command"], "ZDSYS")
        self.assertEqual(entries[0]["expected"], [])
        self.assertEqual(entries[2]["command"], "ZAURS DURT")
        self.assertEqual(entries[2]["expected"], ["AURS0050I", "STAT0001I"])

        tdr_text = "GU:NOT AUTH\nC:ZDSYS\nT:120\nE:SYS0001I\nC:ZSTAT\nE:STAT0001I\n"
        entries, unexp = parse_entries(tdr_text)
        self.assertEqual(unexp, ["NOT AUTH"])
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["command"], "ZDSYS")
        self.assertEqual(entries[0]["expected"], ["SYS0001I"])

    def test_generate_tdr_with_ibm_fallback(self):
        docs = IBMDocs(
            self.index_path,
            self.cache_dir,
            fetcher=lambda url, timeout: SAMPLE_HTML if "zaurs" in url else SAMPLE_NO_MSG_HTML,
        )
        catalog = [{"command": "ZDSYS", "observed_expected_response": "CSMP0001I", "observed_count": "10"}]

        entries = ["ZDSYS", "ZAURS DURT PR1,PR2", "ZCYCL NORM", "ZUNKNOWN"]
        tdr_text, report, details = generate_tdr_from_commands(entries, catalog, default_timeout=120, ibm=docs)

        self.assertTrue(report["valid"])
        self.assertEqual(details[0]["status"], "catalog-exact")
        self.assertEqual(details[0]["source"], "Response catalog")

        self.assertEqual(details[1]["status"], "ibm-example")
        self.assertEqual(details[1]["source"], "IBM z/TPF documentation")
        self.assertIn("E:AURS0050I", tdr_text)

        self.assertEqual(details[2]["status"], "unresolved")
        self.assertTrue(details[2]["is_state_change"])
        self.assertIn("CAUTION: state-changing command", tdr_text)

        self.assertEqual(details[3]["status"], "unresolved")
        self.assertIn("<EXPECTED_RESPONSE>", tdr_text)

    def test_toolbox_ibm_tools(self):
        docs = IBMDocs(
            self.index_path,
            self.cache_dir,
            fetcher=lambda url, timeout: SAMPLE_HTML,
        )
        settings = Settings(
            api_key="",
            catalog_path=self.tmp_path / "catalog.csv",
            knowledge_dir=self.tmp_path,
            feedback_db=self.tmp_path / "fb.db",
            ibm_docs_dir=self.cache_dir,
        )
        toolbox = Toolbox(settings, catalog=[], ibm=docs)

        res, is_err = toolbox.run("lookup_ibm_documentation", {"command": "ZAURS DURT"})
        self.assertFalse(is_err)
        self.assertTrue(res["found"])
        self.assertEqual(res["command"], "ZAURS DURT")

        res, is_err = toolbox.run("lookup_command", {"command": "ZAURS DURT"})
        self.assertFalse(is_err)
        self.assertIn("ibm_documentation", res)
        self.assertTrue(res["ibm_documentation"]["found"])


if __name__ == "__main__":
    unittest.main()
