"""Reading and writing documents of cited values."""

import json

from .lineage import Lineage
from .record import ProvenanceError, from_dict as record_from_dict
from .value import Cited

_TOP = {"document", "note", "values"}
_VALUE = {"name", "value", "unit", "lineage"}


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return loads(fh.read(), where=path)


def loads(text, where="<string>"):
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProvenanceError("%s: not valid JSON (%s)" % (where, exc))
    return parse(raw, where=where)


def parse(raw, where="<input>"):
    """Return ``(document_name, {name: Cited})``."""
    if not isinstance(raw, dict):
        raise ProvenanceError("%s: expected a JSON object at the top level" % where)
    unknown = set(raw) - _TOP
    if unknown:
        raise ProvenanceError("%s: unknown top-level field(s) %s"
                             % (where, ", ".join(sorted(unknown))))
    if "values" not in raw or not isinstance(raw["values"], list):
        raise ProvenanceError("%s: 'values' must be a list" % where)
    if not raw["values"]:
        raise ProvenanceError("%s: 'values' is empty" % where)

    out = {}
    for i, item in enumerate(raw["values"]):
        label = "%s: values[%d]" % (where, i)
        if not isinstance(item, dict):
            raise ProvenanceError("%s: expected an object" % label)
        unknown = set(item) - _VALUE
        if unknown:
            raise ProvenanceError("%s: unknown field(s) %s" % (label, ", ".join(sorted(unknown))))
        for required in ("name", "value", "lineage"):
            if required not in item:
                raise ProvenanceError("%s: missing required field %r" % (label, required))
        name = item["name"]
        if name in out:
            raise ProvenanceError("%s: duplicate value name %r" % (label, name))
        if not isinstance(item["lineage"], list) or not item["lineage"]:
            raise ProvenanceError(
                "%s: 'lineage' must be a non-empty list. A value with no "
                "provenance has no business in this document." % label)
        records = [record_from_dict(r, where="%s lineage[%d]" % (label, j))
                   for j, r in enumerate(item["lineage"])]
        out[name] = Cited(value=item["value"], unit=item.get("unit", ""),
                          lineage=Lineage(tuple(records)))
    return raw.get("document", where), out


def dumps(document, values, indent=2):
    payload = {
        "document": document,
        "values": [dict(cited.to_dict(), name=name) for name, cited in values.items()],
    }
    return json.dumps(payload, indent=indent, sort_keys=True, ensure_ascii=False)
