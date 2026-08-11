# provenance

A grid intensity figure is 412 gCO2e/kWh. Six months later someone asks where
that came from, and the honest answer is usually a shrug: the number was copied
out of a portal, the portal has since restated it, and the parameters that
produced it are gone.

`provenance` is the record that stops that happening, and it is the foundation
every other client in this repository is built on. It holds the source, the
dataset, the dataset *version*, the retrieval instant, the licence, and the
exact query — and it survives arithmetic. Divide one cited value by another and
the result still knows about both retrievals.

No dependencies beyond the Python standard library. Nothing in this project
touches the network.

## Install

```bash
git clone <this repo>
cd projects/001-provenance
python3 -m unittest discover -s tests -t .   # 54 tests, no deps needed
```

## Use

```python
from provenance import Cited, Provenance

record = Provenance(
    source="Example Agency",
    dataset="annual-grid-intensity",
    version="2024-edition",
    retrieved_at="2025-03-04T09:14:00Z",
    licence="CC-BY-4.0",
    query={"country": "AA", "year": 2024, "basis": "location"},
    url="https://example.invalid/annual-grid-intensity",
)

a = Cited.from_source(412.0, "gCO2e/kWh", record)
b = Cited.from_source(188.0, "gCO2e/kWh", other_record)

ratio = a / b
ratio.value                    # 2.1914...
ratio.unit                     # '' -- identical units cancel
ratio.lineage.sources()        # both agencies, in first-seen order
ratio.lineage.licences()       # ('CC-BY-4.0', 'ODbL-1.0')
record.fingerprint             # sha256 of the canonical record
```

Five fields are mandatory: `source`, `dataset`, `version`, `retrieved_at`,
`licence`. A record will not construct without them. If a source states no
licence, record `licence="unstated"` — the point is that the gap is written
down, not that the field is filled in.

The CLI inspects a document of cited values:

```bash
python3 -m provenance.cli examples/synthetic-grid-intensity.json --now 2026-08-11T00:00:00Z
```

```
Synthetic example: two grid intensity figures and a derived ratio
==============================================================================

  grid intensity, country A                             412 gCO2e/kWh
      Example Agency (synthetic) / annual-grid-intensity @ 2024-edition  (525 days old)  STALE
  grid intensity, country B                             188 gCO2e/kWh
      Example Statistics Office (synthetic) / electricity-emissions @ r3  (1156 days old)  STALE
  ratio A over B                                      2.191
      Example Agency (synthetic) / annual-grid-intensity @ 2024-edition  (525 days old)  STALE
      Example Statistics Office (synthetic) / electricity-emissions @ r3  (1156 days old)  STALE

  Distinct retrievals   2
  Sources               Example Agency (synthetic), Example Statistics Office (synthetic)
  Licences              CC-BY-4.0, ODbL-1.0
  Oldest retrieval      2023-06-11T20:00:00Z  (1156 days)
  Newest retrieval      2025-03-04T09:14:00Z  (525 days)

  Stale (>= 365 days)     2
  Without a URL         1
  Without a query       1

  ! This document mixes 2 licences. Whether they may be combined in a published
    figure is a legal question with a jurisdiction attached, and this tool does not
    answer it.
```

Three retrieval entries, two distinct retrievals: the derived ratio inherits
both leaves and the second record deduplicates against the first occurrence.
The `+02:00` offset in the second record has been normalised to `20:00Z`.

Flags: `--max-age DAYS`, `--now TIMESTAMP`, `--format text|json`, and
`--strict`, which exits 1 if anything is stale, has no URL, or records no
query. `--strict` is meant for CI: a repository of derived figures should fail
its build when its inputs age out, not when someone eventually re-reads them.

## Method

**Identity is the fingerprint.** A record's identity is the SHA-256 of its
canonical JSON form — sorted keys at every depth, no insignificant whitespace,
timestamp normalised to UTC. Two records fingerprint the same exactly when they
describe the same retrieval, regardless of how the dictionary was assembled or
which offset the timestamp was written in. The query is part of that identity:
same dataset, same version, same instant, different country code means two
different numbers, and they must not deduplicate against each other.

**Lineage is set union.** A `Lineage` is an ordered, fingerprint-deduplicated
collection of records, and `merge` is union. That makes it commutative,
associative and idempotent, with the empty lineage as identity. Those laws are
tested directly, because they are what guarantees that the *order* in which you
combine values cannot change which sources the answer admits to.

The central invariant — no operation can drop a source — is swept over 400
randomly generated arithmetic expression trees over a pool of eight sourced
values. For each, the resulting lineage must be exactly the set of leaves that
contributed, and the resulting magnitude must equal the same expression
computed on plain floats.

**Two things are refused outright.** A naive timestamp, because
`2025-03-04T09:00:00` is not a moment in time and two of them from different
sources cannot be ordered. And a retrieval time in the future, which is always
a clock or a typo and would make every staleness check read as fresh forever.

**The query is stored as canonical JSON, not as a frozen mapping.** An earlier
approach froze dicts into nested tuples to keep the record hashable, which
cannot distinguish an empty object from an empty list on the way back out. The
canonical string round-trips exactly and is hashable for free.

**Units are compared as exact strings.** `MWh` and `GJ` will not add. That is a
deliberate refusal, not a conversion feature: real unit handling — GJ against
MWh, kt against t, CO2 against CO2e — is the next item in this repository's
queue, and guessing here would be worse than refusing here.

**What this is not.** It is not a client: it fetches nothing and validates no
figure against any source. It does not interpret licences — it tells you which
ones you are carrying and leaves the compatibility question, which has a
jurisdiction attached, to you. It cannot tell you a number is *right*, only
where it came from and how old that is. And it will not stop you attaching an
impeccable record to a value you typed in wrongly.

## The example

`examples/synthetic-grid-intensity.json` is synthetic and says so in its own
`note` field. The source names, dataset names, versions and figures are
invented to show what a complete record looks like; none of them is a real
published value and none should be cited. The second record deliberately omits
both a URL and a query so that `--strict` has something to complain about.

No live data source was contacted in building or testing this project, and none
needs to be: it is the record type, not a client.

## Licence

MIT.
