# Contract 2.0.48: exact nine-path successor-source manifest

Status: implemented construction schema; live owner wiring remains blocked.

Profile key: `construction_k7_direct_fallback_shared_source_manifest_v1`.

## Scope

This slice freezes one content-addressed successor owner site for each of the
nine shared-resource paths.  Every site fixes:

- the official V6 path, reducer and unit;
- the intended cap-admission primitive;
- the successor production owner and the downstream side-effect boundary;
- a contiguous per-operation protocol; and
- cross-site happens-before edges needed by the two-role broker.

The important edges include whole-route output reservation and hierarchy
`memory.max` binding before launch, sandbox ingress before mounted visibility,
mounted visibility before launch, and descendant reap before retained
`memory.peak` observation or mount cleanup.

## Aggregate cap-evidence schema

The manifest also freezes one formula family and required pre-execution
evidence roles per path:

- typed `COUNT × EXTENT` groups for reads and staging, and `COUNT × ONE`
  groups for common events;
- an interval sweep over distinct payload identities for mounted peak;
- a complete route-output fixed point rather than the worker-file limit;
- `min(OUTER_CAP, sum(WORKER_CAP, BUSINESS_CAP))` plus a hierarchy-wide
  same-OFD cgroup peak plan; and
- positive native launch-edge cardinality.

A numerical candidate was removed from this slice.  The schema requires
path-bound group keys and exact typed operand roles, but no operand/evidence
API exists until the corresponding semantic authorities are implemented.
Cross-path operand reuse and shared-admission reuse are forbidden, and zero
multiplicity placeholders cannot satisfy a role.

Every path requires a path-specific `SHARED_ADMISSION_COUNT` operand.  A future
authority must add those counts to the canonical owner-search upper of 56
`control.cap_checks` and provide a failure-path rejection upper.  The former
`56/0` pair is explicitly incomplete.

Output requires exactly eight registered role extents and a verified
fixed-point attestation.  Process launch requires exactly the WORKER and
BUSINESS positive-edge role groups.  No current raw ID or caller-provided
number can satisfy these requirements.

The former V6 stream bound is explicitly not accepted as an aggregate bound
for read, staged or mounted bytes.  The worker output limit is not accepted as
the whole-route output bound, and `memory.max` is not reported as an actual
working-set peak.

## Manifest-bound cap-profile join

The construction slice also exposes one issuer-retained join authority.  Its
public factory accepts the exact canonical manifest bytes, route context,
decision candidate and cap inputs.  It does **not** accept either a manifest ID
or source-site IDs.  The authority independently replays the registered
manifest bytes, strictly parses the ordered nine path/site-ID rows from that
raw canonical document, and retains the resulting immutable binding.  No
manifest object property participates in that derivation.  It invokes the
historical generic cap-profile factory with those derived identities and then
verifies both historical issuer retention and the complete byte-derived
binding before sealing the join.  Exact replay compares the new issuer
manifest's retained raw bytes, not its replaceable `canonical_bytes` property.

Consequently, an exact manifest ID paired with caller-chosen site IDs is not a
manifest-bound join.  A profile minted directly by the historical generic
factory also remains insufficient evidence, even when its values happen to
match.  Consumers of this construction claim must require the exact live
`ManifestBoundSharedCapProfileJoinV1` artifact.

This join proves only identity binding.  It does not make the successor owner
executable, supply aggregate operands, or authorize a route decision.

## Locked claims

Every artifact states:

```text
source_site_manifest_semantically_verified = false
production_owner_sites_wired = false
aggregate_cardinality_evidence_verified = false
numeric_aggregate_cap_candidate_issued = false
formal_v7_route_decision_authority_present = false
formal_actual_compliance_eligible = false
official_execution_allowed = false
construction_only = true
blocker = V7_FORMAL_ROUTE_DECISION_AUTHORITY_MISSING
```

The next implementation slice must create the live cap-aware successor owner,
bind these exact site IDs before each side effect, authenticate child read
receipts, and emit replayable aggregate evidence.  Only a later V7 semantic
authority may consume that result for route selection.
