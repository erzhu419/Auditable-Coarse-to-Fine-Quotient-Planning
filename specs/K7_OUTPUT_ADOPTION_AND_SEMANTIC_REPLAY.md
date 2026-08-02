# K7 production output adoption and nine-path semantic replay

Status: construction contract `2.0.20` (`V0-110B-2E-10`).

## Production first-role adoption

The output source no longer invents or copies a labelled
`business_result.json`. It adopts the exact worker V1
`operational-output.json` inode as the first registered `BUSINESS_RESULT`
role, without renaming or duplicating it. Adoption requires:

- one exact authenticated `PARENT_OUTPUT` observation and binding;
- exact request replay through the worker V1 output verifier;
- matching authenticated byte count and SHA-256;
- one fresh output directory containing only that inode; and
- one-shot consumption of the observation identity.

After both children are reaped, the broker pins the same inode, changes mode
from `0600` to `0400`, fsyncs the file and directory, and rechecks identity and
bytes before writing the seven broker-owned suffix roles. The fixed point sums
the exact eight new inode extents. The construction-only synthetic first-role
API remains available for negative/control tests but is explicitly ineligible
for a live source or exact semantic replay.

## Fixed semantic replay

Each of the nine official V6 shared-resource paths has one fixed catalogue
dispatch. The verifier recomputes the central component IDs and raw SHA-256,
checks exact component order/schema, source identity, local start/cutoff,
required provenance and official reducer, then invokes only the registered
raw replayer. It returns an issuer-owned source-local exact integer for:

- the three common-work sums;
- read/staged byte sums and mounted-byte maximum;
- the adopted eight-role output-byte sum;
- same-OFD working-byte maximum; and
- two exact process launches.

Reported values, caller callbacks, synthetic output promotion, incomplete
failure prefixes and cross-path verifier substitution are rejected. Semantic
verifier identities use a centrally registered domain.

## Claim boundary

All nine source families can now be replayed exactly, but the results remain
source-local and do not issue `CounterRecord`s. Contract `2.0.21` supplies the
honest nine-source identity join without forcing equal local event intervals.
A successor must bind each exact replay result to that V3 join and then combine
it with the other 193 required V6 records before any `WorkVector`,
`ComparisonVector`, terminal, certificate or official Gate can move.
