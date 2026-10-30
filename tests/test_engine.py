import unittest

from tdrgen.config import Settings
from tdrgen.engine import load_catalog, parse_tdr, recommend, render_tdr, validate_spec


class ValidateSpecTests(unittest.TestCase):
    def test_minimal_valid_spec(self):
        report = validate_spec({"steps": [{"command": "ZSTAT DACS", "expected": ["STAT0007I"], "timeout": 120}]})
        self.assertTrue(report["valid"])
        self.assertEqual(report["warnings"], [])

    def test_missing_steps(self):
        self.assertFalse(validate_spec({})["valid"])
        self.assertFalse(validate_spec({"steps": []})["valid"])

    def test_blank_command(self):
        self.assertFalse(validate_spec({"steps": [{"command": "  ", "expected": ["X"]}]})["valid"])

    def test_unset_timeout_is_allowed(self):
        report = validate_spec({"steps": [{"command": "ZDSYS", "expected": ["X"], "timeout": None}]})
        self.assertTrue(report["valid"])

    def test_timeout_must_be_integer(self):
        for value in ("120", 120.5, True):
            report = validate_spec({"steps": [{"command": "ZDSYS", "expected": ["X"], "timeout": value}]})
            self.assertFalse(report["valid"], value)

    def test_timeout_out_of_range_warns(self):
        report = validate_spec({"steps": [{"command": "ZDSYS", "expected": ["X"], "timeout": 30}]})
        self.assertTrue(report["valid"])
        self.assertTrue(any("outside the documented range" in w for w in report["warnings"]))

    def test_timeout_and_timeout_continue_conflict(self):
        step = {"command": "ZDSYS", "expected": ["X"], "timeout": 120, "timeout_continue": 120}
        self.assertFalse(validate_spec({"steps": [step]})["valid"])

    def test_multiline_and_non_ascii_rejected(self):
        self.assertFalse(validate_spec({"steps": [{"command": "ZDSYS\nZSTAT"}]})["valid"])
        self.assertFalse(validate_spec({"steps": [{"command": "ZDSYS", "expected": ["caf\u00e9"]}]})["valid"])

    def test_state_change_warning(self):
        report = validate_spec({"steps": [{"command": "ZINET STOP ALL", "expected": ["OK"]}]})
        self.assertTrue(any("state-changing" in w for w in report["warnings"]))

    def test_placeholder_warning(self):
        report = validate_spec({"steps": [{"command": "ZDSYS", "expected": ["<EXPECTED_RESPONSE>"]}]})
        self.assertTrue(any("placeholder" in w for w in report["warnings"]))


class RenderAndParseTests(unittest.TestCase):
    spec = {
        "global_unexpected": ["CTL-"],
        "steps": [
            {"command": "ZSTAT DACS", "expected": ["STAT0007I"], "timeout": 120, "comment": "DACS status"},
            {"command": "ZDSYS", "expected": ["A", "B"], "unexpected": ["ERR"], "timeout_continue": 300},
        ],
    }

    def test_render(self):
        text = render_tdr(self.spec)
        self.assertTrue(text.isascii())
        self.assertIn("GU:CTL-\n", text)
        self.assertIn("* DACS status\nC:ZSTAT DACS\nT:120\nE:STAT0007I\n", text)
        self.assertIn("C:ZDSYS\nTC:300\nE:A\nE:B\nLU:ERR\n", text)

    def test_render_rejects_invalid(self):
        with self.assertRaises(ValueError):
            render_tdr({"steps": [{"command": ""}]})

    def test_round_trip(self):
        parsed = parse_tdr(render_tdr(self.spec))
        self.assertEqual(parsed["global_unexpected"], ["CTL-"])
        self.assertEqual([s["command"] for s in parsed["steps"]], ["ZSTAT DACS", "ZDSYS"])
        self.assertEqual(parsed["steps"][1]["timeout_continue"], 300)
        self.assertEqual(parsed["steps"][1]["unexpected"], ["ERR"])
        self.assertEqual(parsed["warnings"], [])

    def test_parse_ibm_example(self):
        text = "\\ comment\n* comment\nC:ZDSYS MSG1\nT:120\nE:DSYS01I\n\nC:ZSTAT\nT:10\nE:allocated\nE:STAT081\n"
        parsed = parse_tdr(text)
        self.assertEqual(len(parsed["steps"]), 2)
        self.assertEqual(parsed["steps"][1]["expected"], ["allocated", "STAT081"])

    def test_parse_reports_bad_lines(self):
        parsed = parse_tdr("E:orphan\nC:ZDSYS\nnot a record\n")
        self.assertEqual(len(parsed["warnings"]), 2)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(Settings().catalog_path)

    def test_catalog_loaded(self):
        self.assertGreater(len(self.catalog), 500)

    def test_exact_match_first(self):
        results = recommend("zstat   dacs", self.catalog)
        self.assertEqual(results[0].match_type, "exact")
        self.assertEqual(results[0].response, "STAT0007I")

    def test_family_match_is_candidate_only(self):
        results = recommend("ZSTAT", self.catalog)
        self.assertTrue(results)
        self.assertTrue(all(r.confidence == "candidate-only" for r in results if r.match_type != "exact"))

    def test_empty_query(self):
        self.assertEqual(recommend("   ", self.catalog), [])

    def test_generate_tdr_from_commands_matches_catalog(self):
        from tdrgen.engine import generate_tdr_from_commands
        commands = ["ZDSYS", "ZSTAT DACS"]
        tdr_text, report, details = generate_tdr_from_commands(commands, self.catalog, default_timeout=120)
        self.assertTrue(report["valid"])
        self.assertIn("C:ZDSYS", tdr_text)
        self.assertIn("C:ZSTAT DACS", tdr_text)
        self.assertIn("E:STAT0007I", tdr_text)
        self.assertIn("T:120", tdr_text)
        self.assertEqual(len(details), 2)
        self.assertEqual(details[1]["status"], "catalog-exact")


if __name__ == "__main__":
    unittest.main()
