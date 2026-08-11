"""Inspect a document of cited values: what it rests on, and how old that is."""

import argparse
import datetime as _dt
import json
import sys

from .lineage import Lineage
from .record import ProvenanceError, parse_timestamp
from .serde import load


def _report_text(document, values, now, max_age_days):
    lines = [document, "=" * 78, ""]
    combined = Lineage()
    for name, cited in values.items():
        combined = combined.merge(cited.lineage)
        unit = (" " + cited.unit) if cited.unit else ""
        lines.append("  %-38s %18s%s" % (name[:38], "{:,.4g}".format(cited.value), unit))
        for r in cited.lineage:
            age = r.age_days(now)
            flag = "  STALE" if r.is_stale(max_age_days, now) else ""
            lines.append("      %s / %s @ %s  (%.0f days old)%s"
                         % (r.source, r.dataset, r.version, age, flag))
    lines.append("")
    lines.append("  Distinct retrievals   %d" % len(combined))
    lines.append("  Sources               %s" % ", ".join(combined.sources()))
    lines.append("  Licences              %s" % ", ".join(combined.licences()))
    oldest, newest = combined.oldest(), combined.newest()
    if oldest is not None:
        lines.append("  Oldest retrieval      %s  (%.0f days)"
                     % (oldest.retrieved_at.isoformat().replace("+00:00", "Z"),
                        oldest.age_days(now)))
        lines.append("  Newest retrieval      %s  (%.0f days)"
                     % (newest.retrieved_at.isoformat().replace("+00:00", "Z"),
                        newest.age_days(now)))
    stale = combined.stale(max_age_days, now)
    no_url = [r for r in combined if not r.url]
    no_query = [r for r in combined if r.params == {}]
    lines.append("")
    lines.append("  Stale (>= %d days)     %d" % (max_age_days, len(stale)))
    lines.append("  Without a URL         %d" % len(no_url))
    lines.append("  Without a query       %d" % len(no_query))
    if len(combined.licences()) > 1:
        lines.append("")
        lines.append("  ! This document mixes %d licences. Whether they may be combined "
                     "in a published" % len(combined.licences()))
        lines.append("    figure is a legal question with a jurisdiction attached, and "
                     "this tool does not")
        lines.append("    answer it.")
    return "\n".join(lines)


def _report_json(document, values, now, max_age_days):
    combined = Lineage()
    for cited in values.values():
        combined = combined.merge(cited.lineage)
    return json.dumps({
        "document": document,
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "values": {name: c.to_dict() for name, c in values.items()},
        "summary": {
            "retrievals": len(combined),
            "sources": list(combined.sources()),
            "licences": list(combined.licences()),
            "oldest": combined.oldest().to_dict() if combined.oldest() else None,
            "newest": combined.newest().to_dict() if combined.newest() else None,
            "stale": [r.fingerprint for r in combined.stale(max_age_days, now)],
            "without_url": [r.fingerprint for r in combined if not r.url],
            "without_query": [r.fingerprint for r in combined if r.params == {}],
        },
    }, indent=2, sort_keys=True)


def build_parser():
    p = argparse.ArgumentParser(
        prog="provenance",
        description="Inspect the provenance of a document of cited values.")
    p.add_argument("input", help="JSON document (see examples/)")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--max-age", type=int, default=365, metavar="DAYS",
                   help="flag retrievals at least this old (default 365)")
    p.add_argument("--now", metavar="TIMESTAMP",
                   help="reference instant, ISO-8601 with an offset (default: now, UTC)")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero if any retrieval is stale, has no URL, or "
                        "records no query")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        now = parse_timestamp(args.now, where="--now") if args.now \
            else _dt.datetime.now(_dt.timezone.utc)
    except ProvenanceError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if args.max_age < 0:
        print("error: --max-age must not be negative", file=sys.stderr)
        return 2

    try:
        document, values = load(args.input)
    except ProvenanceError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("error: cannot read %s (%s)" % (args.input, exc.strerror), file=sys.stderr)
        return 2

    render = _report_text if args.format == "text" else _report_json
    print(render(document, values, now, args.max_age))

    if args.strict:
        combined = Lineage()
        for cited in values.values():
            combined = combined.merge(cited.lineage)
        problems = []
        if combined.stale(args.max_age, now):
            problems.append("%d stale retrieval(s)" % len(combined.stale(args.max_age, now)))
        missing_url = [r for r in combined if not r.url]
        if missing_url:
            problems.append("%d retrieval(s) without a URL" % len(missing_url))
        missing_query = [r for r in combined if r.params == {}]
        if missing_query:
            problems.append("%d retrieval(s) recording no query" % len(missing_query))
        if problems:
            print("strict: " + "; ".join(problems), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
