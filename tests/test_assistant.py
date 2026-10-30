import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from tdrgen.assistant import Assistant, AssistantError
from tdrgen.config import Settings
from tdrgen.knowledge import KnowledgeBase, Passage
from tdrgen.tools import TOOL_DEFINITIONS, Toolbox


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_block(block_id, name, arguments):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=arguments)


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self._responses.pop(0)


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.settings = replace(
            Settings(),
            api_key="",
            feedback_db=Path(self._tmp.name) / "fb.db",
            ibm_fallback=False,
            ibm_docs_dir=Path(self._tmp.name) / "ibm_docs",
        )
        knowledge = KnowledgeBase([Passage("runbook.md", "DACS", "ZSTAT DACS shows DACS status; expect STAT0007I.")])
        self.toolbox = Toolbox(self.settings, knowledge=knowledge)

    def tearDown(self):
        self._tmp.cleanup()

    def test_tool_definitions_are_well_formed(self):
        names = [tool["name"] for tool in TOOL_DEFINITIONS]
        self.assertEqual(len(names), len(set(names)))
        for tool in TOOL_DEFINITIONS:
            self.assertEqual(tool["input_schema"]["type"], "object")
            self.assertTrue(tool["description"])

    def test_every_tool_runs(self):
        spec = {"steps": [{"command": "ZDSYS", "expected": ["X"], "timeout": 120}]}
        calls = {
            "search_knowledge": {"query": "DACS"},
            "lookup_command": {"command": "ZSTAT DACS"},
            "lookup_ibm_documentation": {"command": "ZSTAT"},
            "validate_tdr_spec": {"spec": spec},
            "render_tdr_script": {"spec": spec},
            "inspect_tdr_script": {"content": "C:ZDSYS\nE:X\n"},
            "generate_tdr_from_entries": {"commands": ["ZDSYS"]},
            "list_knowledge_sources": {},
        }
        self.assertEqual(set(calls), {tool["name"] for tool in TOOL_DEFINITIONS})
        for name, arguments in calls.items():
            result, is_error = self.toolbox.run(name, arguments)
            self.assertFalse(is_error, f"{name}: {result}")

        result, _ = self.toolbox.run("lookup_command", {"command": "ZSTAT DACS"})
        self.assertEqual(result["historical_observations"][0]["response"], "STAT0007I")
        result, _ = self.toolbox.run("render_tdr_script", {"spec": spec})
        self.assertIn("C:ZDSYS", result["tdr"])

    def test_tool_errors_are_reported_not_raised(self):
        result, is_error = self.toolbox.run("search_knowledge", {})
        self.assertTrue(is_error)
        result, is_error = self.toolbox.run("nope", {})
        self.assertTrue(is_error)
        result, is_error = self.toolbox.run("render_tdr_script", {"spec": {"steps": []}})
        self.assertFalse(is_error)
        self.assertFalse(result["rendered"])

    def test_tool_use_loop(self):
        client = FakeClient([
            SimpleNamespace(stop_reason="tool_use", content=[
                text_block("Checking the catalog."),
                tool_block("t1", "lookup_command", {"command": "ZSTAT DACS"}),
                tool_block("t2", "search_knowledge", {"query": "ZSTAT DACS"}),
            ]),
            SimpleNamespace(stop_reason="end_turn", content=[text_block("Expect STAT0007I (response catalog).")]),
        ])
        assistant = Assistant(self.settings, self.toolbox, client=client)
        reply = assistant.ask("What does ZSTAT DACS return?", history=[
            {"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"},
        ])

        self.assertFalse(reply.offline)
        self.assertEqual(reply.text, "Expect STAT0007I (response catalog).")
        self.assertEqual([c.name for c in reply.tool_calls], ["lookup_command", "search_knowledge"])

        first, second = client.requests
        self.assertEqual(first["model"], self.settings.model)
        self.assertEqual(len(first["messages"]), 3)
        tool_results = second["messages"][-1]["content"]
        self.assertEqual([r["tool_use_id"] for r in tool_results], ["t1", "t2"])
        self.assertTrue(all(r["type"] == "tool_result" for r in tool_results))

    def test_loop_limit(self):
        looping = SimpleNamespace(stop_reason="tool_use", content=[tool_block("t", "list_knowledge_sources", {})])
        client = FakeClient([looping] * 20)
        with self.assertRaises(AssistantError):
            Assistant(self.settings, self.toolbox, client=client).ask("loop")

    def test_offline_reply_is_labelled(self):
        reply = Assistant(self.settings, self.toolbox).ask("Explain ZSTAT DACS")
        self.assertTrue(reply.offline)
        self.assertIn("not configured", reply.text)
        self.assertIn("runbook.md", reply.text)
        self.assertIn("STAT0007I", reply.text)

    def test_empty_question(self):
        with self.assertRaises(AssistantError):
            Assistant(self.settings, self.toolbox).ask("   ")

    def test_offline_reply_generates_tdr_for_command_entries(self):
        reply = Assistant(self.settings, self.toolbox).ask("Generate TDR for:\nZDSYS\nZSTAT DACS")
        self.assertTrue(reply.offline)
        self.assertIn("### Generated .TDR Script", reply.text)
        self.assertIn("C:ZDSYS", reply.text)
        self.assertIn("C:ZSTAT DACS", reply.text)
        self.assertIn("STAT0007I", reply.text)


if __name__ == "__main__":
    unittest.main()
