# units

`provenance`'s own `Cited` type compares units as exact strings on purpose --
`MWh` and `GJ` will not add -- and its docstring says real conversion is the
next item in this repository's queue. This is that item.

`units` converts a value between the energy and mass units this repository's
clients actually return: `GJ` against `MWh`, `kt` against `t`. Both ladders are
exact powers of ten against an SI base unit, so the conversion is a rational
multiplication, not an approximation.

It also draws a line most unit libraries paper over. `tCO2` and `tCO2e` convert
at a factor of exactly 1, because a tonne of CO2 has a global warming potential
of 1 by definition. Every other pair of gas species -- `tCH4` against `tCO2e`,
a plain `t` against either -- needs a published global warming potential to
relate them, and GWPs differ by IPCC assessment report and by the gas's
atmospheric lifetime. This library does not keep that table, so it raises
rather than picks a number: a wrong GWP silently baked into a conversion is
exactly the "plausible-looking figure" the rest of this repository refuses to
fabricate.

No dependencies beyond the Python standard library. Nothing in this project
touches the network.

## What this is not

It is not a general dimensional-analysis engine. It converts one atomic unit to
another -- `GJ` to `MWh`, `tCO2e` to `ktCO2e` -- and nothing compound: it does
not parse `tCO2e/MWh` or `MWh*tCO2e/MWh`, the composite unit strings `Cited`'s
own multiplication and division already produce. Converting a compound unit
means converting its parts and is left to the caller.

It does not maintain a global warming potential table. Anyone who needs one has
to cite it -- source, IPCC assessment report, vintage -- the way
`source-check` requires of any published factor. `unitguard`'s own queue
carries that item (`004 — carbon-units`) separately, because a GWP table is a
cited-data problem, not a units-conversion problem, and the two should not be
allowed to blur.

It does not wrap or reference `provenance.Cited` -- the two projects are
independent, and the composition is two lines the caller writes:

```python
converted_value = convert(cited.value, cited.unit, "MWh")
cited = Cited(converted_value, "MWh", cited.lineage)
```

## Install

```bash
cd projects/002-units
pip install -e .
```

## Use

```python
from units import convert, AmbiguousConversion

convert(3.6, "GJ", "MWh")            # 1.0
convert(1000, "tCO2", "tCO2e")       # 1000.0 -- exact, by definition
convert(12.5, "tCH4", "tCO2e")       # raises AmbiguousConversion
```

The CLI runs a document of conversions and reports which succeeded and which
were refused:

```bash
python3 -m units.cli examples/conversions.json
```

```
Worked example: energy and mass conversions this repository's clients actually need, including two the tool refuses
==============================================================================

  grid intensity source states G          3.6 GJ       ->            1 MWh
  a portal reports MWh, the CLI             1 MWh      ->      3.6e+09 J
  national inventory in kt, a co            1 kt       ->        1,000 t
  CO2 measured in tonnes stated         1,000 tCO2     ->        1,000 tCO2e
  REFUSED: a plain tonne has no  REFUSED: 't' and 'tCO2e' carry different gas species (no species against CO2e) -- converting between them needs an explicit, cited global warming potential, which this library does not keep. See AmbiguousConversion.__doc__.
  REFUSED: methane to CO2e needs REFUSED: 'tCH4' and 'tCO2e' carry different gas species (CH4 against CO2e) -- converting between them needs an explicit, cited global warming potential, which this library does not keep. See AmbiguousConversion.__doc__.
  REFUSED: energy and mass are n REFUSED: 'MWh' is an energy unit, 't' is a mass unit -- cannot convert between them

  Converted   4
  Refused     3
```

Flags: `--format text|json` and `--strict`, which exits 1 if anything was
refused -- meant for CI, the same way `provenance --strict` is.

## Input format

A JSON object with a `document` label and a `conversions` list, each item
`{"label": ..., "value": ..., "from_unit": ..., "to_unit": ...}`. See
`examples/conversions.json` for a complete, runnable one.

## Method

**Two ladders, each an exact power of ten against a base unit.** Energy against
the joule: `J`, `kJ`, `MJ`, `GJ`, `TJ`, `Wh`, `kWh`, `MWh`, `GWh`. Mass against
the gram: `g`, `kg`, `t`, `kt`, `Mt`. These are SI definitions, not measured
factors -- a joule is 3600ths of a watt-hour by definition, the way a published
emission factor is not by definition anything -- so neither ladder carries a
citation.

**The scale factor is computed as an exact `Fraction`, not a chain of float
multiplications.** `Fraction(from_factor, to_factor)` is exact because both
factors are integers; only the final cast back to `float` can round. That is
why converting out and back through any pair of units this library supports
returns the original value to float precision, which the round-trip tests
sweep over every pair in both ladders rather than checking the one pair that
happened to get written by hand.

**A mass unit may carry a gas species, glued on with no separator** --
`tCO2e`, `ktCH4` -- matching how this repository's own example documents
already write them (`gCO2e/kWh` in `001-provenance/examples`). Two mass units
convert only if their species match, or if both are one of `CO2`/`CO2e`; any
other pair -- including a plain mass against either -- raises
`AmbiguousConversion` rather than assuming an identity that has not been
earned.

**Energy against mass raises `IncompatibleUnits`.** An unrecognised token --
including a real-world unit this library has not been taught, like `BTU` --
raises `UnknownUnit` rather than being silently treated as dimensionless.

## Assumptions and limits

Assumes a caller who has already separated a compound unit into its atomic
parts; assumes species suffixes are written as this repository's own examples
write them (`CO2e`, not `co2e` or `CO2-eq`); assumes any downstream user of a
converted value re-attaches its own provenance, since this project carries
none.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

20 tests, zero dependencies: known real-world constants (1 MWh = 3.6 GJ),
the CO2/CO2e identity, every refusal the tool claims to make, and an exact
round-trip identity swept over every unit pair in both ladders.

## Licence

MIT. See the repository [LICENSE](../../LICENSE).
