"""Tests for units.

The repo rule: a test asserts a real property, not that the code ran. Most of
these are either a known real-world constant (1 MWh is exactly 3.6 GJ) or a
round-trip identity swept over every pair this library claims to support --
so a test would fail if `convert` were replaced by `return value`.
"""

import itertools
import random
import unittest

from units.convert import AmbiguousConversion, IncompatibleUnits, convert
from units.registry import ENERGY, MASS, UnknownUnit, resolve


class KnownAnswers(unittest.TestCase):
    """Conversions with a hand-checkable answer, not just an assertion that it ran."""

    def test_one_megawatt_hour_is_3_6_gigajoules(self):
        # 1 MWh = 1e6 W * 3600 s = 3.6e9 J = 3.6 GJ. The textbook constant.
        self.assertAlmostEqual(convert(1.0, "MWh", "GJ"), 3.6)
        self.assertAlmostEqual(convert(3.6, "GJ", "MWh"), 1.0)

    def test_one_kilotonne_is_a_thousand_tonnes(self):
        self.assertEqual(convert(1, "kt", "t"), 1000.0)
        self.assertEqual(convert(1000, "t", "kt"), 1.0)

    def test_one_megatonne_is_a_million_tonnes(self):
        self.assertEqual(convert(1, "Mt", "t"), 1_000_000.0)

    def test_base_units_are_the_identity(self):
        self.assertEqual(convert(412.0, "J", "J"), 412.0)
        self.assertEqual(convert(412.0, "g", "g"), 412.0)

    def test_co2_and_co2e_convert_at_a_factor_of_exactly_one(self):
        # A tonne of CO2 has a global warming potential of 1 by definition, so
        # it equals a tonne of CO2e with no external factor -- the one case in
        # this repository's queue item this library is allowed to resolve.
        self.assertEqual(convert(1000.0, "tCO2", "tCO2e"), 1000.0)
        self.assertEqual(convert(1000.0, "tCO2e", "tCO2"), 1000.0)

    def test_gas_species_scales_like_any_other_mass(self):
        self.assertEqual(convert(1, "ktCO2e", "tCO2e"), 1000.0)


class WhatItRefuses(unittest.TestCase):
    """The refusal is part of the contract: each claim gets a test that it holds."""

    def test_energy_against_mass_is_incompatible(self):
        with self.assertRaises(IncompatibleUnits):
            convert(1.0, "MWh", "t")
        with self.assertRaises(IncompatibleUnits):
            convert(1.0, "kg", "GJ")

    def test_different_gas_species_are_ambiguous_without_a_gwp(self):
        with self.assertRaises(AmbiguousConversion):
            convert(1.0, "tCH4", "tCO2e")
        with self.assertRaises(AmbiguousConversion):
            convert(1.0, "tN2O", "tCO2")

    def test_a_plain_mass_cannot_assume_a_species(self):
        with self.assertRaises(AmbiguousConversion):
            convert(500.0, "t", "tCO2e")
        with self.assertRaises(AmbiguousConversion):
            convert(500.0, "tCO2e", "t")

    def test_unknown_units_are_refused_not_guessed(self):
        for bad in ("lbs", "BTU", "tonnes", "", "kt CO2e"):
            with self.assertRaises(UnknownUnit, msg=repr(bad)):
                convert(1.0, bad, "t")

    def test_unknown_unit_is_refused_regardless_of_which_side(self):
        with self.assertRaises(UnknownUnit):
            convert(1.0, "GJ", "BTU")


class RegistryParsing(unittest.TestCase):
    def test_energy_units_carry_no_species(self):
        family, factor, species = resolve("MWh")
        self.assertEqual(family, "energy")
        self.assertEqual(factor, ENERGY["MWh"])
        self.assertIsNone(species)

    def test_plain_mass_has_no_species(self):
        family, factor, species = resolve("kt")
        self.assertEqual((family, factor), ("mass", MASS["kt"]))
        self.assertIsNone(species)

    def test_a_gas_suffix_is_captured_exactly(self):
        self.assertEqual(resolve("tCO2e"), ("mass", MASS["t"], "CO2e"))
        self.assertEqual(resolve("ktCH4"), ("mass", MASS["kt"], "CH4"))

    def test_kg_and_kt_do_not_collide(self):
        # Both share a first character; the regression this guards is the
        # shorter alternative swallowing the longer one's second letter.
        self.assertEqual(resolve("kg")[:2], ("mass", MASS["kg"]))
        self.assertEqual(resolve("kt")[:2], ("mass", MASS["kt"]))


class RoundTripIsExact(unittest.TestCase):
    """Converting out and back through any pair this library supports returns
    the original value -- swept over every unit pair in each family, not just
    the one or two the other tests happen to exercise."""

    def test_energy_round_trip(self):
        rng = random.Random(1729)
        for a, b in itertools.permutations(ENERGY, 2):
            value = rng.uniform(0.1, 1e6)
            there = convert(value, a, b)
            back = convert(there, b, a)
            self.assertAlmostEqual(back, value, places=6, msg="%s <-> %s" % (a, b))

    def test_mass_round_trip_without_a_species(self):
        rng = random.Random(2027)
        for a, b in itertools.permutations(MASS, 2):
            value = rng.uniform(0.1, 1e6)
            there = convert(value, a, b)
            back = convert(there, b, a)
            self.assertAlmostEqual(back, value, places=6, msg="%s <-> %s" % (a, b))

    def test_mass_round_trip_with_a_matching_species(self):
        rng = random.Random(99)
        for a, b in itertools.permutations(MASS, 2):
            value = rng.uniform(0.1, 1e6)
            there = convert(value, a + "CO2e", b + "CO2e")
            back = convert(there, b + "CO2e", a + "CO2e")
            self.assertAlmostEqual(back, value, places=6, msg="%s <-> %s" % (a, b))

    def test_composing_through_an_intermediate_energy_unit_agrees_with_direct(self):
        rng = random.Random(7)
        for _ in range(50):
            value = rng.uniform(0.1, 1e6)
            direct = convert(value, "GJ", "kWh")
            via = convert(convert(value, "GJ", "MJ"), "MJ", "kWh")
            self.assertAlmostEqual(direct, via, places=6)


class InputValidation(unittest.TestCase):
    def test_resolve_rejects_non_string_and_empty(self):
        for bad in (None, 3, "", ()):
            with self.assertRaises(UnknownUnit, msg=repr(bad)):
                resolve(bad)


if __name__ == "__main__":
    unittest.main()
