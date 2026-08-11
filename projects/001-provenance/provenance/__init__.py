"""The record every value in this library is wrapped in.

A climate or energy figure without a provenance cannot be defended six months
later, and by then the source has usually restated it. So provenance is not a
side table here: it is attached to the value, it survives arithmetic, and it is
a precondition of construction rather than a field someone remembers to fill.
"""

from .lineage import Lineage
from .record import Provenance, ProvenanceError, canonical, fingerprint
from .value import Cited, UnitMismatch

__all__ = [
    "Provenance",
    "ProvenanceError",
    "canonical",
    "fingerprint",
    "Lineage",
    "Cited",
    "UnitMismatch",
]

__version__ = "0.1.0"
