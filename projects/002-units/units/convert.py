"""Convert a value between atomic units, refusing what it cannot know.

Two failure modes get folded into one function on purpose: an energy unit
converted against a mass unit is a mistake nobody meant to make, and a gas
species converted against a different one is a mistake the caller might mean
to make but has not supplied enough information for. Both come back as a
raised exception rather than a number, because a wrong number that looks right
is worse than no number.
"""

from fractions import Fraction

from .registry import UnknownUnit, resolve

__all__ = ["convert", "UnknownUnit", "IncompatibleUnits", "AmbiguousConversion"]


class IncompatibleUnits(ValueError):
    """The two units belong to different dimensions -- energy against mass."""


class AmbiguousConversion(ValueError):
    """Two mass units carry different gas species with no factor to relate them.

    CO2 and CO2e are the one pair this library treats as identical: a tonne of
    CO2 has a global warming potential of 1 by definition, so a tonne of CO2 is
    a tonne of CO2e exactly, with no external factor involved. Every other pair
    of species -- CH4 against CO2e, N2O against CO2, or a plain mass against
    either -- needs a GWP, and GWPs differ by IPCC assessment report and by the
    gas's atmospheric lifetime. This library does not keep that table: a value
    picked from memory here is exactly the "plausible-looking figure" the rest
    of this repository refuses to fabricate. Supply the factor yourself, cited,
    or convert through a project that keeps one.
    """


def convert(value, from_unit, to_unit):
    """Convert ``value`` from ``from_unit`` to ``to_unit``, exactly where possible.

    Both units must resolve to the same family (:mod:`units.registry`), and if
    that family is mass, their gas species must be compatible -- equal, or one
    of the two spellings of carbon dioxide against the other. The scale factor
    is exact (an integer ratio of the two units' base-unit weights); the only
    source of error is whatever ``value`` already carried as a float.
    """
    from_family, from_factor, from_species = resolve(from_unit)
    to_family, to_factor, to_species = resolve(to_unit)
    if from_family != to_family:
        raise IncompatibleUnits(
            "%r is %s %s unit, %r is %s %s unit -- cannot convert between them"
            % (from_unit, _article(from_family), from_family,
               to_unit, _article(to_family), to_family)
        )
    if from_family == "mass":
        _check_species(from_species, to_species, from_unit, to_unit)
    ratio = Fraction(from_factor, to_factor)
    return float(Fraction(value) * ratio)


def _check_species(a, b, from_unit, to_unit):
    if a == b or _canonical_species(a) == _canonical_species(b):
        return
    raise AmbiguousConversion(
        "%r and %r carry different gas species (%s against %s) -- converting "
        "between them needs an explicit, cited global warming potential, which "
        "this library does not keep. See AmbiguousConversion.__doc__."
        % (from_unit, to_unit, a or "no species", b or "no species")
    )


def _canonical_species(species):
    return "CO2" if species in ("CO2", "CO2e") else species


def _article(family):
    return "an" if family == "energy" else "a"
