import datetime as dt
import unittest

from provenance.lineage import EMPTY, Lineage
from provenance.record import ProvenanceError
from provenance.value import Cited, UnitMismatch, total

from tests.support import BASE, rec, rng_for


class MergeIsAMonoid(unittest.TestCase):
    """Merge has to behave like set union, or the order you combine values in
    could change which sources the answer admits to."""

    def setUp(self):
        self.a = Lineage.of(rec(1))
        self.b = Lineage.of(rec(2))
        self.c = Lineage.of(rec(3), rec(4))

    def test_empty_is_the_identity(self):
        for x in (self.a, self.b, self.c, EMPTY):
            self.assertEqual(x.merge(EMPTY).fingerprints, x.fingerprints)
            self.assertEqual(EMPTY.merge(x).fingerprints, x.fingerprints)

    def test_merge_is_associative(self):
        left = self.a.merge(self.b).merge(self.c)
        right = self.a.merge(self.b.merge(self.c))
        self.assertEqual(left.fingerprints, right.fingerprints)

    def test_merge_is_commutative_as_a_set(self):
        self.assertEqual(self.a.merge(self.b).fingerprints,
                         self.b.merge(self.a).fingerprints)

    def test_merge_is_idempotent(self):
        self.assertEqual(self.c.merge(self.c).fingerprints, self.c.fingerprints)
        self.assertEqual(len(self.c.merge(self.c)), len(self.c))

    def test_ordering_is_first_seen(self):
        merged = self.b.merge(self.a)
        self.assertEqual([r.source for r in merged], ["Source 2", "Source 1"])

    def test_duplicates_collapse_on_fingerprint_not_identity(self):
        # Two separately constructed but identical records are one retrieval.
        lineage = Lineage.of(rec(1), rec(1))
        self.assertEqual(len(lineage), 1)

    def test_records_with_the_same_dataset_but_different_queries_do_not_collapse(self):
        lineage = Lineage.of(rec(1, query={"country": "AA"}),
                             rec(1, query={"country": "BB"}))
        self.assertEqual(len(lineage), 2)

    def test_only_provenance_records_may_enter(self):
        with self.assertRaises(ProvenanceError):
            Lineage.of("Eurostat")
        with self.assertRaises(ProvenanceError):
            Lineage.of(rec(1)).merge(rec(1))


class LineageSummaries(unittest.TestCase):
    def test_licences_are_listed_and_not_interpreted(self):
        lineage = Lineage.of(rec(1, licence="CC-BY-4.0"),
                             rec(2, licence="ODbL-1.0"),
                             rec(3, licence="CC-BY-4.0"))
        self.assertEqual(lineage.licences(), ("CC-BY-4.0", "ODbL-1.0"))

    def test_oldest_and_newest_pick_the_extremes(self):
        lineage = Lineage.of(rec(5), rec(1), rec(3))
        self.assertEqual(lineage.oldest().retrieved_at, BASE + dt.timedelta(days=1))
        self.assertEqual(lineage.newest().retrieved_at, BASE + dt.timedelta(days=5))
        self.assertIsNone(EMPTY.oldest())

    def test_stale_selects_by_age(self):
        lineage = Lineage.of(rec(0), rec(300))
        now = BASE + dt.timedelta(days=400)
        self.assertEqual(len(lineage.stale(365, now)), 1)
        self.assertEqual(len(lineage.stale(1, now)), 2)


class ArithmeticKeepsTheReceipts(unittest.TestCase):
    def test_no_operation_can_drop_a_source(self):
        """The invariant, swept over random expression trees.

        Every leaf that contributed to a value must appear in that value's
        lineage, and nothing else may. Dimensionless values are used so that
        every operator is legal on every pair.
        """
        rng = rng_for(4242)
        pool = [Cited.from_source(rng.uniform(1.0, 100.0), "", rec(i)) for i in range(8)]
        for _ in range(400):
            expr, expected_value, used = _random_expression(rng, pool, depth=4)
            self.assertEqual(expr.lineage.fingerprints,
                             frozenset(r.fingerprint for r in used))
            self.assertEqual(expr.value, expected_value)

    def test_a_bare_number_contributes_no_source_and_removes_none(self):
        a = Cited.from_source(10.0, "MWh", rec(1))
        for derived in (a * 2, 2 * a, a + 1.0, a - 1.0, a / 4.0):
            self.assertEqual(derived.lineage.fingerprints, a.lineage.fingerprints)

    def test_addition_requires_identical_unit_strings(self):
        a = Cited.from_source(1.0, "MWh", rec(1))
        b = Cited.from_source(1.0, "GJ", rec(2))
        with self.assertRaises(UnitMismatch):
            a + b
        with self.assertRaises(UnitMismatch):
            a - b

    def test_multiplication_and_division_compose_unit_strings(self):
        e = Cited.from_source(10.0, "MWh", rec(1))
        f = Cited.from_source(0.4, "tCO2e/MWh", rec(2))
        self.assertEqual((e * f).unit, "MWh*tCO2e/MWh")
        self.assertEqual((e / e).unit, "")            # same unit cancels
        self.assertEqual((e / f).unit, "MWh/tCO2e/MWh")
        self.assertEqual((e * 2).unit, "MWh")

    def test_dividing_by_a_cited_zero_raises(self):
        a = Cited.from_source(1.0, "", rec(1))
        z = Cited.from_source(0.0, "", rec(2))
        with self.assertRaises(ZeroDivisionError):
            a / z

    def test_subtraction_is_antisymmetric_and_keeps_both_sources(self):
        a = Cited.from_source(10.0, "MWh", rec(1))
        b = Cited.from_source(4.0, "MWh", rec(2))
        self.assertEqual((a - b).value, -(b - a).value)
        self.assertEqual((a - b).lineage.fingerprints, (b - a).lineage.fingerprints)

    def test_total_sums_and_unions(self):
        parts = [Cited.from_source(float(i), "t", rec(i)) for i in range(1, 5)]
        summed = total(parts)
        self.assertEqual(summed.value, 10.0)
        self.assertEqual(len(summed.lineage), 4)

    def test_total_refuses_an_empty_sequence(self):
        # Returning 0.0 with no lineage would be the exact failure this library exists to stop.
        with self.assertRaises(ProvenanceError):
            total([])

    def test_a_value_must_be_a_real_number(self):
        for bad in ("412", None, True, complex(1, 1)):
            with self.assertRaises(ProvenanceError, msg=repr(bad)):
                Cited(bad, "", Lineage.of(rec(1)))

    def test_a_single_record_may_be_passed_where_a_lineage_is_expected(self):
        c = Cited(1.0, "", rec(1))
        self.assertEqual(len(c.lineage), 1)


def _random_expression(rng, pool, depth):
    """Build a random arithmetic expression, returning (Cited, float, [records])."""
    if depth == 0 or rng.random() < 0.3:
        leaf = rng.choice(pool)
        return leaf, leaf.value, list(leaf.lineage)
    left, lv, lr = _random_expression(rng, pool, depth - 1)
    right, rv, rr = _random_expression(rng, pool, depth - 1)
    op = rng.choice(("+", "-", "*", "/"))
    if op == "+":
        return left + right, lv + rv, lr + rr
    if op == "-":
        return left - right, lv - rv, lr + rr
    if op == "*" or rv == 0.0:
        # x - x lands on exactly zero often enough to matter; division by it is
        # a separate, deliberately raising case tested on its own.
        return left * right, lv * rv, lr + rr
    return left / right, lv / rv, lr + rr


if __name__ == "__main__":
    unittest.main()
