import tempfile
import unittest
from pathlib import Path

from tdrgen.config import Settings
from tdrgen.engine import load_catalog
from tdrgen.feedback import feedback_for_command, record_feedback, recent_feedback
from tdrgen.knowledge import KnowledgeBase, catalog_passages, split_passages, tokenize


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "nested" / "feedback.db"

    def tearDown(self):
        self._tmp.cleanup()

    def test_needs_review_record(self):
        row_id = record_feedback(self.db, {"command": "zstat  dacs", "expected_response": "STAT0007I",
                                           "result": "needs_review"})
        self.assertEqual(row_id, 1)
        rows = feedback_for_command(self.db, "ZSTAT DACS")
        self.assertEqual(rows[0]["command"], "ZSTAT DACS")

    def test_verified_requires_evidence(self):
        with self.assertRaises(ValueError) as ctx:
            record_feedback(self.db, {"command": "ZDSYS", "expected_response": "X", "result": "verified"})
        self.assertIn("reviewer", str(ctx.exception))

    def test_verified_with_evidence(self):
        record_feedback(self.db, {
            "command": "ZDSYS", "expected_response": "X", "result": "verified", "actual_response": "X OK",
            "reviewer": "alice", "system_name": "TPF1", "ztpf_release": "1.1", "environment": "test",
        })
        self.assertEqual(len(recent_feedback(self.db)), 1)

    def test_invalid_result(self):
        with self.assertRaises(ValueError):
            record_feedback(self.db, {"command": "ZDSYS", "expected_response": "X", "result": "approved"})


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "runbook.md").write_text(
            "# Restart\n\nAfter IPL run ZDSYS and confirm the system is in NORM state.\n\n"
            "# Network\n\nUse ZINET DISPLAY to check the internet daemon servers.\n",
            encoding="utf-8",
        )
        (self.root / "notes.txt").write_text("STAT0007I is returned by ZSTAT DACS on TPF1.", encoding="utf-8")
        (self.root / "image.png").write_bytes(b"\x89PNG")

    def tearDown(self):
        self._tmp.cleanup()

    def test_tokenize_keeps_message_ids_and_paths(self):
        tokens = tokenize("Check STAT0007I for z/TPF")
        self.assertIn("stat0007i", tokens)
        self.assertIn("z/tpf", tokens)
        self.assertIn("tpf", tokens)
        self.assertNotIn("for", tokens)

    def test_split_by_heading(self):
        passages = split_passages((self.root / "runbook.md").read_text(), "runbook.md")
        self.assertEqual([p.heading for p in passages], ["Restart", "Network"])

    def test_long_block_is_split(self):
        text = "\n".join(f"C:ZCMD{i}" for i in range(500))
        passages = split_passages(text, "big.tdr", max_chars=500)
        self.assertGreater(len(passages), 5)
        self.assertTrue(all(len(p.text) <= 600 for p in passages))

    def test_search_ranks_relevant_passage(self):
        kb = KnowledgeBase.from_directory(self.root)
        self.assertEqual(kb.sources, ["notes.txt", "runbook.md"])
        self.assertEqual(kb.skipped, ["image.png"])
        hits = kb.search("what does ZINET display show?")
        self.assertEqual(hits[0].passage.heading, "Network")
        hits = kb.search("STAT0007I")
        self.assertEqual(hits[0].passage.source, "notes.txt")

    def test_search_with_no_match(self):
        kb = KnowledgeBase.from_directory(self.root)
        self.assertEqual(kb.search("recoup"), [])

    def test_missing_directory(self):
        kb = KnowledgeBase.from_directory(self.root / "missing")
        self.assertEqual(kb.passages, [])


class CatalogSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_catalog(Settings().catalog_path)
        cls.kb = KnowledgeBase.from_directory(Path(tempfile.gettempdir()) / "no_such_dir", cls.rows)

    def test_every_catalog_command_is_indexed(self):
        indexed = "\n".join(p.text for p in self.kb.passages)
        for row in self.rows:
            command = " ".join(row["command"].split()).upper()
            self.assertIn(command, indexed, command)

    def test_message_id_search_cites_catalog(self):
        hit = self.kb.search("CORE0397I")[0]
        self.assertEqual(hit.passage.source, "response_catalog.csv")
        self.assertIn("ZTPLF", hit.passage.text)
        self.assertIn("observed", hit.passage.text)
        self.assertNotIn(".tdr", hit.passage.text)

    def test_command_search_finds_family(self):
        hit = self.kb.search("ZTTCP INACT ALL")[0]
        self.assertEqual(hit.passage.heading, "ZTTCP")
        self.assertIn("TTCP0188I", hit.passage.text)

    def test_blank_rows_skipped(self):
        passages = catalog_passages([{"command": "", "observed_expected_response": "X"},
                                     {"command": "ZDSYS", "observed_expected_response": ""}])
        self.assertEqual(passages, [])


if __name__ == "__main__":
    unittest.main()
