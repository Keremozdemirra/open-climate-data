"""Convert a document of values, reporting what converted and what was refused."""

import argparse
import json
import sys

from .convert import AmbiguousConversion, IncompatibleUnits, convert
from .registry import UnknownUnit

_TOP = {"document", "conversions"}
_ITEM = {"label", "value", "from_unit", "to_unit"}


def _load(path):
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raise ValueError("%s: expected a JSON object at the top level" % path)
    unknown = set(raw) - _TOP
    if unknown:
        raise ValueError("%s: unknown top-level field(s) %s" % (path, ", ".join(sorted(unknown))))
    items = raw.get("conversions")
    if not isinstance(items, list) or not items:
        raise ValueError("%s: 'conversions' must be a non-empty list" % path)
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("%s: conversions[%d] must be an object" % (path, i))
        missing = _ITEM - {"label"} - set(item)
        if missing:
            raise ValueError("%s: conversions[%d] missing %s"
                             % (path, i, ", ".join(sorted(missing))))
        extra = set(item) - _ITEM
        if extra:
            raise ValueError("%s: conversions[%d] has unknown field(s) %s"
                             % (path, i, ", ".join(sorted(extra))))
    return raw.get("document", path), items


def _run(items):
    """Convert every item, returning (results, failures) without stopping at the first."""
    results, failures = [], []
    for item in items:
        label = item.get("label", "%s %s -> %s" % (item["value"], item["from_unit"], item["to_unit"]))
        try:
            out = convert(item["value"], item["from_unit"], item["to_unit"])
            results.append((label, item, out))
        except (UnknownUnit, IncompatibleUnits, AmbiguousConversion) as exc:
            failures.append((label, item, exc))
    return results, failures


def _report_text(document, results, failures):
    lines = [document, "=" * 78, ""]
    for label, item, out in results:
        lines.append("  %-30s %12s %-8s -> %12s %s"
                     % (label[:30], _fmt(item["value"]), item["from_unit"], _fmt(out), item["to_unit"]))
    for label, item, exc in failures:
        lines.append("  %-30s REFUSED: %s" % (label[:30], exc))
    lines.append("")
    lines.append("  Converted   %d" % len(results))
    lines.append("  Refused     %d" % len(failures))
    return "\n".join(lines)


def _report_json(document, results, failures):
    return json.dumps({
        "document": document,
        "converted": [
            {"label": label, "value": item["value"], "from_unit": item["from_unit"],
             "to_unit": item["to_unit"], "result": out}
            for label, item, out in results
        ],
        "refused": [
            {"label": label, "value": item["value"], "from_unit": item["from_unit"],
             "to_unit": item["to_unit"], "reason": str(exc)}
            for label, item, exc in failures
        ],
    }, indent=2, sort_keys=True)


def _fmt(number):
    return "{:,.6g}".format(number)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="units",
        description="Convert a document of values between atomic units, reporting "
                     "what converted and what was refused.")
    parser.add_argument("input", help="JSON document (see examples/)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero if any conversion was refused")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        document, items = _load(args.input)
    except (ValueError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("error: cannot read %s (%s)" % (args.input, exc.strerror), file=sys.stderr)
        return 2

    results, failures = _run(items)
    render = _report_text if args.format == "text" else _report_json
    print(render(document, results, failures))

    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
