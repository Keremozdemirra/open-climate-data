import datetime as dt
import unittest

from provenance.record import (
    Provenance, ProvenanceError, canonical, fingerprint, from_dict, parse_timestamp,
)

from tests.support import BASE, rec


class Completeness(unittest.TestCase):
    def test_each_required_field_is_actually_required(self):
        for name in ("source", "dataset", "version", "licence"):
            with self.assertRaises(ProvenanceError, msg=name):
                rec(1, **{name: "   "})
        with self.assertRaises(ProvenanceError):
            rec(1, retrieved_at=None)

    def test_from_dict_names_every_missing_field(self):
        with self.assertRaises(ProvenanceError) as ctx:
            from_dict({"source": "s"})
        message = str(ctx.exception)
        for name in ("dataset", "version", "retrieved_at", "licence"):
            self.assertIn(name, message)

    def test_unknown_fields_are_rejected(self):
        payload = rec(1).to_dict()
        payload["provenance"] = "recursive"
        with self.assertRaises(ProvenanceError):
            from_dict(payload)


class Timestamps(unittest.TestCase):
    def test_a_naive_timestamp_is_refused(self):
        # "2025-03-04 09:00" is not a moment in time, and two of them from
        # different sources cannot be ordered.
        with self.assertRaises(ProvenanceError) as ctx:
            parse_timestamp("2025-03-04T09:00:00")
        self.assertIn("no timezone", str(ctx.exception))
        with self.assertRaises(ProvenanceError):
            parse_timestamp(dt.datetime(2025, 3, 4, 9, 0))

    def test_z_and_explicit_offsets_land_on_the_same_instant(self):
        z = parse_timestamp("2023-06-11T22:00:00Z")
        plus_two = parse_timestamp("2023-06-12T00:00:00+02:00")
        self.assertEqual(z, plus_two)
        self.assertEqual(plus_two.tzinfo, dt.timezone.utc)
        self.assertEqual(plus_two.hour, 22)

    def test_a_lowercase_z_is_accepted(self):
        self.assertEqual(parse_timestamp("2023-06-11T22:00:00z"),
                         parse_timestamp("2023-06-11T22:00:00Z"))

    def test_garbage_is_reported_not_guessed(self):
        for bad in ("last Tuesday", "2023-13-01T00:00:00Z", "", "   "):
            with self.assertRaises(ProvenanceError, msg=bad):
                parse_timestamp(bad)

    def test_a_future_retrieval_is_refused_when_checked(self):
        future = rec(1, retrieved_at=BASE + dt.timedelta(days=3650))
        with self.assertRaises(ProvenanceError):
            future.check_not_future(now=BASE)
        rec(1).check_not_future(now=BASE + dt.timedelta(days=400))

    def test_age_and_staleness(self):
        r = rec(0)   # retrieved at BASE
        now = BASE + dt.timedelta(days=365)
        self.assertAlmostEqual(r.age_days(now), 365.0, places=6)
        self.assertTrue(r.is_stale(365, now))     # inclusive at the threshold
        self.assertFalse(r.is_stale(366, now))


class Fingerprints(unittest.TestCase):
    def test_construction_order_does_not_change_the_fingerprint(self):
        a = rec(1, query={"b": 2, "a": {"z": 1, "y": [1, 2]}})
        b = rec(1, query={"a": {"y": [1, 2], "z": 1}, "b": 2})
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, b)

    def test_an_equivalent_timestamp_written_differently_fingerprints_the_same(self):
        a = rec(1, retrieved_at="2023-06-11T22:00:00Z")
        b = rec(1, retrieved_at="2023-06-12T00:00:00+02:00")
        self.assertEqual(a.fingerprint, b.fingerprint)

    def test_changing_any_single_field_changes_the_fingerprint(self):
        base = rec(1)
        variants = {
            "source": {"source": "Other"},
            "dataset": {"dataset": "other"},
            "version": {"version": "v99"},
            "retrieved_at": {"retrieved_at": BASE + dt.timedelta(seconds=1)},
            "licence": {"licence": "ODbL-1.0"},
            "query": {"query": {"country": "BB", "year": 2025}},
            "url": {"url": "https://example.invalid/other"},
            "note": {"note": "restated"},
        }
        seen = {base.fingerprint}
        for name, override in variants.items():
            fp = rec(1, **override).fingerprint
            self.assertNotIn(fp, seen, "%s did not affect the fingerprint" % name)
            seen.add(fp)

    def test_the_query_is_part_of_the_identity(self):
        # Same dataset, same version, same instant -- different country. These
        # are different numbers and must not deduplicate against each other.
        a = rec(1, query={"country": "AA"})
        b = rec(1, query={"country": "BB"})
        self.assertNotEqual(a.fingerprint, b.fingerprint)

    def test_canonical_form_is_sorted_and_compact(self):
        text = canonical(rec(1))
        self.assertNotIn(", ", text)
        keys = [k for k in ("dataset", "licence", "note", "query", "retrieved_at",
                            "source", "url", "version")]
        positions = [text.index('"%s":' % k) for k in keys]
        self.assertEqual(positions, sorted(positions))

    def test_fingerprint_is_a_sha256_hex_digest(self):
        fp = fingerprint(rec(1))
        self.assertEqual(len(fp), 64)
        int(fp, 16)


class RoundTrip(unittest.TestCase):
    def test_to_dict_then_from_dict_is_the_identity(self):
        for n in range(5):
            original = rec(n)
            self.assertEqual(from_dict(original.to_dict()), original)

    def test_the_parsed_query_survives_nesting(self):
        query = {"country": "AA", "years": [2020, 2021], "flags": {"raw": True, "n": None}}
        r = rec(1, query=query)
        self.assertEqual(r.params, query)
        self.assertEqual(from_dict(r.to_dict()).params, query)

    def test_an_empty_query_round_trips_as_an_empty_object(self):
        # It round-trips as {}, not [] -- which is exactly what a tuple-freezing
        # implementation gets wrong.
        r = rec(1, query={})
        self.assertEqual(r.params, {})
        self.assertEqual(from_dict(r.to_dict()).params, {})

    def test_a_query_that_is_not_an_object_is_refused(self):
        for bad in ([1, 2], "not json", 7):
            with self.assertRaises(ProvenanceError, msg=repr(bad)):
                rec(1, query=bad)

    def test_non_string_query_keys_are_refused(self):
        with self.assertRaises(ProvenanceError):
            rec(1, query={2024: "year"})


if __name__ == "__main__":
    unittest.main()
