"""Exact conversion between the energy and mass units the other clients in
this repository return, and a refusal rather than a guess when a mass unit's
gas species cannot be related without an external factor."""

from .convert import AmbiguousConversion, IncompatibleUnits, UnknownUnit, convert
from .registry import ENERGY, MASS

__all__ = [
    "convert",
    "UnknownUnit",
    "IncompatibleUnits",
    "AmbiguousConversion",
    "ENERGY",
    "MASS",
]
