# Backlog

Working queue. The next unchecked item is the one being built. An item stays
unchecked and picks up a `status:` note if it spans more than one working
session — finishing something half-built takes priority over starting the next
one.

Rules of thumb applied to every item:

- one job per tool, done properly, rather than a suite of half-features
- standard library unless a dependency earns its place
- tests that assert a real property, not that the code ran
- a README that says what the tool is *not* for
- any published factor, threshold or rate gets a citation and a vintage

---

## Done

- [x] **001 — provenance** · Complete retrieval record with a canonical SHA-256 fingerprint, lineage that merges as a set union through arithmetic, UTC-normalised timestamps, and a CLI that reports sources, licences, staleness and missing URLs or queries. 54 tests, no network.

## Queue

- [ ] **002 — units** · Normalise units across sources — GJ against MWh, kt against t, CO2 against CO2e — and refuse ambiguous conversions rather than guessing.
- [ ] **003 — fixtures** · Recording harness: capture a live response once, replay it forever, so tests are deterministic and offline.
- [ ] **004 — grid-intensity** · Grid carbon intensity by country and, where published, by hour.
- [ ] **005 — ets-prices** · EU and UK ETS allowance price series.
- [ ] **006 — degree-days** · Heating and cooling degree days from public weather data, with the base temperature as an explicit argument.
- [ ] **007 — country-inventories** · National greenhouse gas inventories as reported to the UNFCCC.
- [ ] **008 — emission-factors** · A factor registry that tracks vintage and supersession, so a restated factor does not quietly change last year's answer.
- [ ] **009 — cache** · Local caching with explicit expiry, because most of these sources update annually and should not be hit on every run.
- [ ] **010 — cli** · Fetch and export from the terminal, with provenance included in every output.
