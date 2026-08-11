"""A number that keeps its receipts through arithmetic."""

import numbers
from dataclasses import dataclass
from typing import Union

from .lineage import Lineage
from .record import Provenance, ProvenanceError


class UnitMismatch(ValueError):
    """Two cited values carry different unit strings.

    Compared as exact strings on purpose. Real conversion -- GJ against MWh, kt
    against t, CO2 against CO2e -- is a separate concern with its own failure
    modes, and it is the next item in this repository's queue. Guessing here
    would be worse than refusing here.
    """


@dataclass(frozen=True)
class Cited:
    """A magnitude, a unit, and every retrieval that contributed to it.

    Arithmetic returns ``Cited`` values whose lineage is the union of the
    operands'. The invariant the tests pin is simple and absolute: no operation
    can drop a source. A derived figure always admits to everything that went
    into it.
    """

    value: float
    unit: str = ""
    lineage: Lineage = Lineage()

    def __post_init__(self):
        if isinstance(self.value, bool) or not isinstance(self.value, numbers.Real):
            raise ProvenanceError("value must be a real number, got %s"
                                  % type(self.value).__name__)
        object.__setattr__(self, "value", float(self.value))
        if self.unit is None:
            object.__setattr__(self, "unit", "")
        elif not isinstance(self.unit, str):
            raise ProvenanceError("unit must be a string")
        if isinstance(self.lineage, Provenance):
            object.__setattr__(self, "lineage", Lineage.of(self.lineage))
        elif not isinstance(self.lineage, Lineage):
            raise ProvenanceError("lineage must be a Lineage or a Provenance")

    @classmethod
    def from_source(cls, value, unit, record):
        return cls(value=value, unit=unit, lineage=Lineage.of(record))

    # -- arithmetic ------------------------------------------------------

    def _combine(self, other, op, unit):
        if isinstance(other, Cited):
            return Cited(op(self.value, other.value), unit,
                         self.lineage.merge(other.lineage))
        if isinstance(other, bool) or not isinstance(other, numbers.Real):
            return NotImplemented
        # A bare number is a constant the caller supplied; it has no source to
        # inherit, so the lineage passes through unchanged.
        return Cited(op(self.value, float(other)), unit, self.lineage)

    def _same_unit(self, other):
        if isinstance(other, Cited) and other.unit != self.unit:
            raise UnitMismatch("cannot combine %r with %r"
                               % (self.unit or "dimensionless", other.unit or "dimensionless"))
        return self.unit

    def __add__(self, other):
        return self._combine(other, lambda a, b: a + b, self._same_unit(other))

    __radd__ = __add__

    def __sub__(self, other):
        return self._combine(other, lambda a, b: a - b, self._same_unit(other))

    def __rsub__(self, other):
        result = self.__sub__(other)
        if result is NotImplemented:
            return NotImplemented
        return Cited(-result.value, result.unit, result.lineage)

    def __mul__(self, other):
        unit = _mul_unit(self.unit, other.unit if isinstance(other, Cited) else "")
        return self._combine(other, lambda a, b: a * b, unit)

    __rmul__ = __mul__

    def __truediv__(self, other):
        if isinstance(other, Cited) and other.value == 0:
            raise ZeroDivisionError("division by a cited zero")
        unit = _div_unit(self.unit, other.unit if isinstance(other, Cited) else "")
        return self._combine(other, lambda a, b: a / b, unit)

    def __neg__(self):
        return Cited(-self.value, self.unit, self.lineage)

    def __abs__(self):
        return Cited(abs(self.value), self.unit, self.lineage)

    def __float__(self):
        return self.value

    def __repr__(self):
        return "Cited(%r, %r, %d source(s))" % (self.value, self.unit, len(self.lineage))

    def to_dict(self):
        return {"value": self.value, "unit": self.unit, "lineage": self.lineage.to_list()}


def _mul_unit(left, right):
    if not left:
        return right
    if not right:
        return left
    return "%s*%s" % (left, right)


def _div_unit(left, right):
    if not right:
        return left
    if left == right:
        return ""
    return "%s/%s" % (left or "1", right)


def total(values):
    """Sum a sequence of Cited values, preserving every source.

    ``sum()`` works too, because ``__radd__`` accepts the integer 0 it starts
    from, but this spells the intent out and rejects an empty sequence rather
    than silently returning a sourceless zero.
    """
    values = list(values)
    if not values:
        raise ProvenanceError("cannot total an empty sequence: the result would "
                              "be a zero with no provenance")
    out = values[0]
    for v in values[1:]:
        out = out + v
    return out
