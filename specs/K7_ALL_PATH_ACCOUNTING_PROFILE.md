# K7 all-path accounting profile

Contract `2.0.33` / V0-110B-2E-23 freezes the finite obligations that every
K7 route and terminal must satisfy before Counter Completeness can run. It
contains the exact FQ9 taxonomy of three terminal classes and ten terminal
codes, five route kinds, ten construction stages, seven accounting families,
and the FQ4/FQ8 attempt/rebuild limits. Every path keeps separate route-segment
WorkVectors and retains all work through its actual failure cutoff.

The profile also replays the current `v075_*.py` source tree and explicitly
classifies all 47 `Terminal`/`Status` enum classes and all 164 members:

```text
MAP_TO_FQ9                 = 22
PROFILE_EXTENSION_REQUIRED = 14
NONTERMINAL                = 128
```

There is no default mapping. A new or changed enum member, omitted stage,
missing accounting family, unknown route, or unregistered evidence authority
invalidates replay. `PROFILE_EXTENSION_REQUIRED` is a typed blocker and cannot
be treated as an executable terminal recipe.

This contract is a profile, not an execution. It issues no CounterRecord,
WorkVector, ComparisonVector, terminal or certificate. The 14 extension rows
and every route-specific production authority must close before the all-path
Counter Completeness Gate can run.
