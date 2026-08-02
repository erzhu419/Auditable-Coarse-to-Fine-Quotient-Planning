# K7 common-work raw journals

**Contract:** `2.0.16`
**Profile:** `construction_shared_resource_common_journal_v2`

This recorder supplies raw V2 components for
`common.hash_invocations`, `common.integrity_checks` and
`common.protocol_checks`. Exact source sites, hash purposes and named
obligations are frozen before the measurement window. Each event receives
recorder-owned broker-global and path-local sequence numbers and binds one
unique authenticated broker observation plus canonical input/output artifact
IDs.

Close emits the shared inclusive cutoff and the exact transcript, registry and
loaded-site component schemas required by the nine-path catalogue. Independent
replay derives all three counts and rejects missing or extra registrations,
events, sites, obligations and cutoff-hidden work. No API accepts a count.

The journals prove internal registry arithmetic, not yet that every operation
in a live production attempt reached the recorder. They remain raw-only until
the complete broker envelope and source-site instrumentation establish that
coverage.
