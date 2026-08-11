import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from provenance.cli import main
from provenance.record import ProvenanceError
from provenance.serde import dumps, loads, parse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(HERE, "examples", "synthetic-grid-intensity.json")

RECORD = {
    "source": "S", "dataset": "d", "version": "v1",
    "retrieved_at": "2025-01-01T00:00:00Z", "licence": "CC-BY-4.0",
    "query": {"country": "AA"}, "url": "https://example.invalid/d",
}
DOC = {"document": "t", "values": [
    {"name": "x", "value": 1.0, "unit": "t", "lineage": [RECORD]},
]}


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class Serde(unittest.TestCase):
    def test_the_shipped_example_parses(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            name, values = loads(fh.read(), where=EXAMPLE)
        self.assertEqual(len(values), 3)
        # The two leaf records appear in the derived ratio, deduplicated.
        self.assertEqual(len(values["ratio A over B"].lineage), 2)

    def test_the_derived_value_in_the_example_is_arithmetically_consistent(self):
        with open(EXAMPLE, encoding="utf-8") as fh:
            _, values = loads(fh.read())
        a, b = values["grid intensity, country A"], values["grid intensity, country B"]
        self.assertAlmostEqual((a / b).value, values["ratio A over B"].value, places=12)
        # ...and recomputing it reconstructs exactly the recorded lineage.
        self.assertEqual((a / b).lineage.fingerprints,
                         values["ratio A over B"].lineage.fingerprints)

    def test_round_trip_through_dumps_preserves_fingerprints(self):
        _, values = parse(DOC)
        _, again = loads(dumps("t", values))
        self.assertEqual(again["x"].lineage.fingerprints, values["x"].lineage.fingerprints)
        self.assertEqual(again["x"].value, values["x"].value)

    def test_a_value_without_a_lineage_is_refused(self):
        doc = json.loads(json.dumps(DOC))
        doc["values"][0]["lineage"] = []
        with self.assertRaises(ProvenanceError) as ctx:
            parse(doc)
        self.assertIn("no provenance", str(ctx.exception))

    def test_structural_problems_are_reported_precisely(self):
        for mutate, fragment in (
            (lambda d: d.pop("values"), "'values'"),
            (lambda d: d.update(values=[]), "empty"),
            (lambda d: d.update(extra=1), "unknown top-level"),
            (lambda d: d["values"][0].pop("name"), "missing required field"),
            (lambda d: d["values"].append(d["values"][0]), "duplicate"),
            (lambda d: d["values"][0].update(units="t"), "unknown field"),
        ):
            doc = json.loads(json.dumps(DOC))
            mutate(doc)
            with self.assertRaises(ProvenanceError, msg=fragment) as ctx:
                parse(doc)
            self.assertIn(fragment, str(ctx.exception))

    def test_malformed_json_is_reported_as_such(self):
        with self.assertRaises(ProvenanceError):
            loads("{nope")


class CommandLine(unittest.TestCase):
    def test_both_formats_run(self):
        for fmt in ("text", "json"):
            code, out, err = _run([EXAMPLE, "--format", fmt, "--now", "2026-08-11T00:00:00Z"])
            self.assertEqual(code, 0, err)
            self.assertTrue(out.strip())

    def test_json_summary_reports_the_deduplicated_retrievals(self):
        code, out, err = _run([EXAMPLE, "--format", "json", "--now", "2026-08-11T00:00:00Z"])
        self.assertEqual(code, 0, err)
        summary = json.loads(out)["summary"]
        self.assertEqual(summary["retrievals"], 2)
        self.assertEqual(len(summary["licences"]), 2)
        self.assertEqual(len(summary["without_url"]), 1)
        self.assertEqual(len(summary["without_query"]), 1)

    def test_offsets_are_normalised_to_utc_in_the_report(self):
        code, out, _ = _run([EXAMPLE, "--format", "json", "--now", "2026-08-11T00:00:00Z"])
        oldest = json.loads(out)["summary"]["oldest"]
        self.assertEqual(oldest["retrieved_at"], "2023-06-11T20:00:00Z")

    def test_strict_fails_on_the_example_and_says_why(self):
        code, _, err = _run([EXAMPLE, "--strict", "--now", "2026-08-11T00:00:00Z"])
        self.assertEqual(code, 1)
        self.assertIn("without a URL", err)
        self.assertIn("no query", err)

    def test_strict_passes_on_a_complete_document(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(DOC, fh)
            path = fh.name
        try:
            code, _, err = _run([path, "--strict", "--now", "2025-06-01T00:00:00Z"])
            self.assertEqual(code, 0, err)
        finally:
            os.unlink(path)

    def test_bad_arguments_exit_two(self):
        code, _, err = _run(["/nonexistent/doc.json"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)
        code, _, err = _run([EXAMPLE, "--now", "2026-08-11T00:00:00"])   # naive
        self.assertEqual(code, 2)
        self.assertIn("no timezone", err)
        code, _, _ = _run([EXAMPLE, "--max-age", "-1"])
        self.assertEqual(code, 2)

    def test_a_document_with_an_incomplete_record_exits_two(self):
        doc = json.loads(json.dumps(DOC))
        del doc["values"][0]["lineage"][0]["licence"]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
            path = fh.name
        try:
            code, _, err = _run([path])
            self.assertEqual(code, 2)
            self.assertIn("licence", err)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
