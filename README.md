# open-climate-data

[![tests](https://github.com/Keremozdemirra/open-climate-data/actions/workflows/tests.yml/badge.svg)](https://github.com/Keremozdemirra/open-climate-data/actions/workflows/tests.yml)

Public climate and energy data is abundant and almost uniformly painful to
consume: a dozen portals, a dozen schemas, units that disagree, and figures
that get silently restated between vintages.

This library gives those sources one Python interface. Every value it returns
carries its provenance — which source, which dataset version, retrieved when —
because a number without a vintage cannot be defended six months later.

**Two design commitments.** Nothing is fabricated: if a source is unreachable,
the call fails loudly rather than returning a plausible-looking figure. And
every client works offline against recorded fixtures, so the test suite never
depends on a third party being up, and neither does your CI.

Each tool lives in its own folder with its own README and its own tests, and
leans on the Python standard library unless a dependency genuinely earns its
place.

## Layout

```
projects/
  NNN-project-name/
    README.md          what it does, how to run it, what it is not
    <package>/         the implementation
    tests/             python3 -m unittest discover -s tests -t .
    examples/          a working input file
    pyproject.toml     dependencies, if any
```

## Projects

| # | Project | What it does |
| --- | --- | --- |
| 001 | [provenance](projects/001-provenance) | The record every value is wrapped in — source, dataset, version, retrieval instant, licence and the exact query — carried through arithmetic so a derived figure still admits to everything that went into it. |
| 002 | [units](projects/002-units) | Exact conversion between energy and mass units — GJ against MWh, kt against t — and a refusal rather than a guess when a mass unit's gas species is ambiguous, as with CO2 against everything but CO2e. |

## Roadmap

See [BACKLOG.md](BACKLOG.md).

## Licence

MIT, per project. See [LICENSE](LICENSE).
