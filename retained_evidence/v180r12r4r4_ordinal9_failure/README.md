# V180r12r4r4 ordinal9 failure freeze

This directory preserves the seven exact ordinal9 prelaunch artifacts copied
read-only from `jtl110gpu2` after the consumed formal attempt.  Materialization
succeeded and the outer systemd service acquired its delegated unit, but the
source-bound child stopped before it wrote a campaign-attempt artifact.
Consequently there are no campaign ledger events, CounterRecords, WorkVector,
ComparisonVector, replay receipt, scientific terminal, or executed gates.

`source_conformance_postmortem.json` is explicitly a postmortem forensic read,
not an artifact emitted by the failed runtime.  It records stable before/after
properties for the exact source that raised the exception.  The bytes, SHA-256,
Git blob, regular-file type, link count, and size matched; only the working-tree
mode differed (`0664` observed versus frozen `0644` expected).  All 23 frozen
source roots had mode `0664`.  The successor therefore adds a pre-campaign
source-property conformance gate with typed per-field diagnostics.

The ordinal9 identity is consumed and must never be retried or mutated.
