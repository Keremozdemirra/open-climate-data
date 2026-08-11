"""One retrieval, described completely enough to repeat it."""

import datetime as _dt
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

REQUIRED = ("source", "dataset", "version", "retrieved_at", "licence")

_FIELDS = (
    "source", "dataset", "version", "retrieved_at", "licence", "query", "url", "note",
)


class ProvenanceError(ValueError):
    """A provenance record is incomplete, or describes something impossible."""


def parse_timestamp(raw, where="retrieved_at"):
    """Parse an ISO-8601 timestamp and normalise it to UTC.

    Two things are refused outright. A naive timestamp, because "2025-03-04
    09:00" is not a moment in time and comparing two of them across sources is a
    silent error. And a timestamp in the future, because that is always a clock
    or a typo, and it would make every staleness check read as fresh forever.
    """
    if isinstance(raw, _dt.datetime):
        stamp = raw
    elif isinstance(raw, str) and raw.strip():
        text = raw.strip()
        # datetime.fromisoformat only learned to accept a trailing Z in 3.11.
        if text.endswith("Z") or text.endswith("z"):
            text = text[:-1] + "+00:00"
        try:
            stamp = _dt.datetime.fromisoformat(text)
        except ValueError:
            raise ProvenanceError(
                "%s: %r is not an ISO-8601 timestamp (e.g. 2025-11-30T09:14:00Z)" % (where, raw)
            )
    else:
        raise ProvenanceError("%s is required and must be an ISO-8601 timestamp" % where)

    if stamp.tzinfo is None or stamp.tzinfo.utcoffset(stamp) is None:
        raise ProvenanceError(
            "%s: %s has no timezone. A retrieval time without an offset is not a "
            "moment in time; use Z or an explicit offset." % (where, stamp.isoformat())
        )
    return stamp.astimezone(_dt.timezone.utc)


@dataclass(frozen=True)
class Provenance:
    """Where one value came from, and how to get it again.

    ``query`` is the part people leave out and then regret: the parameters that
    produced this value. Two figures from the same dataset and version are still
    different numbers if the country code differed, and the fingerprint has to
    reflect that.

    The query is held as a canonical JSON string rather than a dict. That keeps
    the record hashable and frozen, and it removes the round-trip ambiguity you
    get from freezing a mapping into tuples -- an empty dict and an empty list
    are indistinguishable once both are ``()``. Use :attr:`params` for the
    parsed form.
    """

    source: str
    dataset: str
    version: str
    retrieved_at: _dt.datetime
    licence: str
    query: str = "{}"
    url: str = ""
    note: str = ""

    def __post_init__(self):
        for name in ("source", "dataset", "version", "licence"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ProvenanceError(
                    "%s is required. If the source states none, record that "
                    "explicitly (e.g. licence='unstated') rather than leaving it blank."
                    % name
                )
            object.__setattr__(self, name, value.strip())
        object.__setattr__(self, "retrieved_at", parse_timestamp(self.retrieved_at))
        object.__setattr__(self, "query", _canonical_query(self.query))
        for name in ("url", "note"):
            value = getattr(self, name)
            if value is None:
                object.__setattr__(self, name, "")
            elif not isinstance(value, str):
                raise ProvenanceError("%s must be a string" % name)

    def check_not_future(self, now=None):
        """Raise if this record claims to have been retrieved after ``now``."""
        now = now or _dt.datetime.now(_dt.timezone.utc)
        if self.retrieved_at > now:
            raise ProvenanceError(
                "retrieved_at %s is in the future relative to %s"
                % (self.retrieved_at.isoformat(), now.isoformat())
            )
        return self

    def age_days(self, now=None):
        now = now or _dt.datetime.now(_dt.timezone.utc)
        return (now - self.retrieved_at).total_seconds() / 86400.0

    def is_stale(self, max_age_days, now=None):
        return self.age_days(now) >= max_age_days

    @property
    def params(self):
        """The query parameters as an ordinary dict."""
        return json.loads(self.query)

    @property
    def fingerprint(self):
        """A stable identifier for this exact retrieval.

        Equal fingerprints mean the same dataset version answered the same query
        at the same instant under the same licence -- so two values can be
        compared, or deduplicated, without comparing free text.
        """
        return fingerprint(self)

    def to_dict(self):
        return {
            "source": self.source,
            "dataset": self.dataset,
            "version": self.version,
            "retrieved_at": self.retrieved_at.isoformat().replace("+00:00", "Z"),
            "licence": self.licence,
            "query": self.params,
            "url": self.url,
            "note": self.note,
        }


def from_dict(raw, where="provenance"):
    if not isinstance(raw, dict):
        raise ProvenanceError("%s: expected an object, got %s" % (where, type(raw).__name__))
    unknown = set(raw) - set(_FIELDS)
    if unknown:
        raise ProvenanceError("%s: unknown field(s) %s" % (where, ", ".join(sorted(unknown))))
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        raise ProvenanceError("%s: missing required field(s) %s" % (where, ", ".join(missing)))
    return Provenance(
        source=raw["source"],
        dataset=raw["dataset"],
        version=raw["version"],
        retrieved_at=raw["retrieved_at"],
        licence=raw["licence"],
        query=raw.get("query") if raw.get("query") is not None else {},
        url=raw.get("url", "") or "",
        note=raw.get("note", "") or "",
    )


def canonical(record):
    """The record as a canonical JSON string: sorted keys, no insignificant space.

    Canonicalisation is what makes the fingerprint independent of how the
    dictionary happened to be built.
    """
    return json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def fingerprint(record):
    return hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()


def _canonical_query(query):
    """Normalise a query to a canonical JSON object string.

    Sorting happens at every depth, so two dicts that differ only in insertion
    order canonicalise identically -- which is what makes the fingerprint a
    property of the query rather than of how it was assembled.
    """
    if query is None:
        return "{}"
    if isinstance(query, str):
        try:
            parsed = json.loads(query)
        except json.JSONDecodeError:
            raise ProvenanceError("query string is not valid JSON: %r" % query)
    elif isinstance(query, dict):
        parsed = query
    else:
        raise ProvenanceError("query must be a mapping of parameters, got %s"
                              % type(query).__name__)
    if not isinstance(parsed, dict):
        raise ProvenanceError("query must be a JSON object, got %s" % type(parsed).__name__)
    for key in parsed:
        if not isinstance(key, str):
            raise ProvenanceError("query keys must be strings, got %r" % (key,))
    try:
        return json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError):
        raise ProvenanceError("query values must be JSON-representable")
