"""The units this library knows, and what an atomic unit string means.

Two families, each an exact power-of-ten ladder against a base unit: energy
against the joule, mass against the gram. Both ladders are SI-derived
definitions, not measured factors, so neither carries a citation -- a joule is
by definition 3600ths of a watt-hour, in the way that a published emission
factor is not by definition anything.

A mass unit may carry a gas species suffix -- ``tCO2e``, ``ktCH4`` -- glued
directly onto the unit with no separator, matching how this repository's own
example documents write unit strings (``gCO2e/kWh`` in
``001-provenance/examples``). The species is not looked up here; it is carried
through so :mod:`units.convert` can decide whether two species are compatible.
"""

import re

ENERGY = {
    "J": 1,
    "kJ": 10**3,
    "MJ": 10**6,
    "GJ": 10**9,
    "TJ": 10**12,
    "Wh": 3600,
    "kWh": 3600 * 10**3,
    "MWh": 3600 * 10**6,
    "GWh": 3600 * 10**9,
}

MASS = {
    "g": 1,
    "kg": 10**3,
    "t": 10**6,
    "kt": 10**9,
    "Mt": 10**12,
}

# Ordered so no alternative is a prefix of another that sorts before it --
# "kg" and "kt" share a first character but diverge on the second, so trying
# them in any order still matches the whole mass token before the species
# suffix is considered.
_MASS_UNIT = re.compile(
    "^(%s)([A-Z][A-Za-z0-9]*)?$" % "|".join(re.escape(u) for u in MASS)
)


class UnknownUnit(ValueError):
    """A unit string is not one this library recognises."""


def resolve(unit):
    """Return ``(family, factor, species)`` for an atomic unit string.

    ``factor`` is the exact integer number of base units (joules, or grams)
    one of ``unit`` is worth. ``species`` is the gas suffix on a mass unit, or
    ``None`` for a plain mass or for any energy unit.
    """
    if not isinstance(unit, str) or not unit:
        raise UnknownUnit("unit must be a non-empty string, got %r" % (unit,))
    if unit in ENERGY:
        return "energy", ENERGY[unit], None
    match = _MASS_UNIT.match(unit)
    if match:
        return "mass", MASS[match.group(1)], match.group(2)
    raise UnknownUnit(
        "%r is not a unit this library knows. Energy units: %s. Mass units: %s, "
        "each optionally followed by a gas species glued on, e.g. 'tCO2e'."
        % (unit, ", ".join(sorted(ENERGY)), ", ".join(sorted(MASS)))
    )
