"""What a derived value inherits from its inputs.

Derived numbers are where provenance usually dies: two sourced values go into a
ratio and a bare float comes out. A :class:`Lineage` is the fix -- an ordered,
deduplicated collection of every retrieval that contributed to a value, merged
on every operation.

Merging is set union under the record fingerprint, which makes it commutative,
associative and idempotent, with the empty lineage as identity. Those are not
decorative properties: they are what guarantee that the order in which you
combine values cannot change which sources the answer admits to.
"""

from dataclasses import dataclass
from typing import Iterable, Tuple

from .record import Provenance, ProvenanceError


@dataclass(frozen=True)
class Lineage:
    """An immutable, order-preserving, fingerprint-deduplicated set of records."""

    records: Tuple[Provenance, ...] = ()

    def __post_init__(self):
        seen = {}
        for r in self.records:
            if not isinstance(r, Provenance):
                raise ProvenanceError("a lineage holds Provenance records, got %s"
                                      % type(r).__name__)
            seen.setdefault(r.fingerprint, r)
        object.__setattr__(self, "records", tuple(seen.values()))

    @classmethod
    def of(cls, *records):
        return cls(tuple(records))

    def merge(self, other):
        """Union of two lineages. First occurrence wins for ordering."""
        if not isinstance(other, Lineage):
            raise ProvenanceError("can only merge a Lineage, got %s" % type(other).__name__)
        return Lineage(self.records + other.records)

    __or__ = merge

    def __len__(self):
        return len(self.records)

    def __iter__(self):
        return iter(self.records)

    def __contains__(self, record):
        return any(r.fingerprint == record.fingerprint for r in self.records)

    @property
    def fingerprints(self):
        return frozenset(r.fingerprint for r in self.records)

    def sources(self):
        """Distinct source organisations, in first-seen order."""
        return _distinct(r.source for r in self.records)

    def datasets(self):
        return _distinct("%s / %s @ %s" % (r.source, r.dataset, r.version)
                         for r in self.records)

    def licences(self):
        """Every licence that touched this value, in first-seen order.

        Deliberately not interpreted. Whether CC-BY-4.0 and ODbL-1.0 may be
        combined in a published figure is a legal question with a jurisdiction
        attached, and this library is not going to pretend to answer it. It
        tells you what you are carrying; you decide what that means.
        """
        return _distinct(r.licence for r in self.records)

    def oldest(self):
        return min(self.records, key=lambda r: r.retrieved_at) if self.records else None

    def newest(self):
        return max(self.records, key=lambda r: r.retrieved_at) if self.records else None

    def stale(self, max_age_days, now=None):
        return tuple(r for r in self.records if r.is_stale(max_age_days, now))

    def to_list(self):
        return [r.to_dict() for r in self.records]


EMPTY = Lineage()


def _distinct(items):
    out = []
    for item in items:
        if item not in out:
            out.append(item)
    return tuple(out)
