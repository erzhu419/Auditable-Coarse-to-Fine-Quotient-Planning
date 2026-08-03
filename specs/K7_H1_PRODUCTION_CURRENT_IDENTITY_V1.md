# K7 H1 Production Current-Identity Candidate V1

Status: construction-only Contract 2.0.52 slice 1
Profile: `construction_k7_h1_production_current_identity_v1`

This slice supplies a production current-identity candidate for the canonical
H1 direct-fallback recipe. It closes a construction identity boundary only. It
does not authorize a V7 route upper, route decision, execution, accounting
artifact, terminal certificate, or Gate transition.

The candidate is not a production current-identity authority. Route-time call
counts are typed `UNOBSERVED`; the profile records only a forbidden-API
declaration until an observed access log exists. That access evidence remains
pending.

## Frozen result

The candidate is a three-stage A/B/C chain:

1. **A — independent current source.** Build/evaluation work first compares the
   selected Phase-0.5 output with preregistered proof bytes and identity
   constants, then projects it into separately typed build/kernel and query
   attestations. The semantic verifier receives that frozen current identity
   explicitly; the eight-coordinate current identity is never accepted from
   the selected output.
2. **B — claimant proof match.** A second build/evaluation issuer first
   verifies the exact preexecution candidate bytes, observes the complete
   recipe chain from those bytes, verifies the claimant durable proof against
   A's explicit typed identity, and validates/binds the retained verifier
   handle to the real selected plan. The underlying handle is not revoked.
3. **C — route-time structural join.** The route-time freezer accepts only A,
   B, and the already-issued H1 two-role recipe. It performs an exact structural
   crosswalk and no semantic replay or ground access.

The chain deliberately distinguishes two facts that may have equal values:

- A is the registered current source;
- the durable proof is the claimant.

Byte equality between their canonical proof representations does not collapse
these roles. In particular, the durable verifier's optional
`current_identity=None` self-match path is not used by this profile.

## Stage A: independent current-source fixture

`issue_h1_current_source_fixture_v1` accepts:

- the registered Phase-0.5 bundle root;
- an exact source closure rooted at the current-identity and durable-proof
  modules;
- its deterministic source archive;
- a verified runtime dependency lock;
- the sealed archive compile verification.

It does not accept claimant proof bytes or a claimant identity. Before calling
the semantic verifier it requires the exact preregistered proof ID, SHA-256,
byte count, source-projection ID, and all eight frozen identity coordinates.
Any mismatch closes before semantic replay.

The issuer performs the durable semantic replay in the evaluation lane and
freezes these eight coordinates:

1. `structural_id`;
2. `query_id`;
3. `BuildEpoch_id`;
4. `kernel_id`;
5. `threshold_profile_id`;
6. `reward_profile_id`;
7. `policy_class_id`;
8. `complete_search_profile_id`.

The build/kernel attestation additionally binds the structural, source
projection, kernel and BuildEpoch canonical documents and one caller-supplied,
self-consistent closure/archive/runtime-lock/compile fixture. The query attestation binds
the full QuerySpec, threshold, reward, deterministic-policy and complete-search
profiles.

The V0-075 archive verifier compiles every exact source member without
importing or executing it. A different but fully self-consistent, compilable
archive is also accepted. Therefore the archive proves neither live/current
issuer source nor issuer-code provenance; it is not semantic authority.

## Stage B: durable-proof match

`issue_h1_durable_proof_match_attestation_v1` accepts claimant proof bytes,
the exact preexecution candidate bytes, and the preregistered Contract-2.0.50
recipe only after A exists. It first requires the frozen preexecution SHA-256
and embedded content ID, then invokes the recipe byte verifier and parses the
typed candidate. It must call
the durable verifier with
`current_identity=current_source.identity`; omission is invalid.

The only accepted result is a semantically valid `IDENTICAL_MATCH` whose proof
and current identity IDs equal A's eight-coordinate identity. For the canonical
H1 regression, the exact minimum failure probability is `383/410`.

The recipe ID and its canonical preexecution digest/ID, current-identity
attestation, route context, decision point, cap, cardinality bound,
cardinality evidence, formula, derivation proof, upper, decision, selected
plan, occurrence, and attempt IDs are frozen. The cap, cardinality-bound,
cardinality-evidence, formula, and derivation IDs omitted by the legacy recipe
projection must be read from the exact preexecution bytes. Constants may check
those observed values but may not fill unobserved fields. A process-local
recipe-registry injection cannot substitute for these bytes.

The verified object must then be validated and plan-bound through
`bind_verified_durable_exact_infeasibility_to_plan_v1` for the recipe's actual
`selected_plan_id`. That API validates a retained handle but does not revoke it;
the artifact therefore records `one_shot_revocation = false` and must not claim
consumption. Reconstructing a look-alike result, retaining only a string ID, or
skipping retained-handle validation is invalid.

Stage B remains evaluation work and is not charged as route execution.

## Stage C: zero-ground route-time join

`freeze_h1_production_current_identity_candidate_v1` accepts exactly:

- `current_source`;
- `proof_match_attestation`;
- `recipe`.

It does not accept proof bytes, a bundle root, a caller-provided current
identity, or caller-provided zero counters. It may not invoke:

- `kernel.step`;
- ground outcome enumeration;
- the durable proof producer or verifier;
- J0 or another planner;
- the fallback solver.

The freezer requires exact agreement among A, B, and the recipe for:

- durable proof ID;
- exact infeasibility identity ID;
- selected plan ID;
- structural ID;
- query ID;
- BuildEpoch ID;
- kernel ID;
- threshold profile ID.

The candidate records all eight identity coordinates. Reward, policy-class and
complete-search IDs are fully bound by A and B but marked not applicable to the
legacy recipe because that recipe does not expose those three fields.

No route-time numeric zero is emitted. Instead the candidate records:

```text
route_time_call_counts.kind = UNOBSERVED
route_time_call_counts.reason = OBSERVED_ROUTE_TIME_ACCESS_LOG_PENDING
route_time_forbidden_api_declaration.kind =
    FORBIDDEN_API_DECLARATION_NOT_OBSERVED_COUNTERS
```

`verify_h1_production_current_identity_candidate_bytes_v1` repeats only this
structural join and exact canonical-byte comparison. It has the same no-ground
API boundary. Both documents record
`route_time_access_evidence_status = PENDING_OBSERVED_ACCESS_LOG`; therefore
they set `production_current_identity_candidate = true` and
`production_current_identity_authority = false`.

## Construction integrity and threat boundary

Ordinary public construction paths use generated dataclass initialization,
pending-to-live retention, exact object identity, and canonical payload checks
as defense in depth. The registries, sentinels, and frozen-code references are
mutable private Python module state. This profile therefore makes no
same-process unforgeability claim against an adversary that can mutate private
state. Even a candidate made locally acceptable by such mutation remains
ineligible as a production authority; the production-consumer guard rejects
all V1 candidates. The six schema roles use distinct centrally registered
content-ID domains:

- current build/kernel attestation;
- current query attestation;
- current-source fixture;
- durable-proof match attestation;
- production current-identity candidate;
- production current-identity candidate verification.

## Acceptance tests

The focused suite must establish:

- six unique central domains and Contract 2.0.52 locks;
- exact self-consistent source archive/runtime/compile binding without live
  provenance semantics, including a fully valid alternate archive;
- preregistered current bytes rejected before semantic verification;
- explicit frozen current identity passed to semantic verification;
- all eight independently derived current identity coordinates;
- explicit claimant-versus-current durable verification;
- retained handle validation/plan binding, explicit non-revocation, and exact
  `383/410` regression;
- exact preexecution bytes and all five previously omitted recipe-chain IDs;
- exact-projection registry-injection rejection;
- exact current/proof/recipe crosswalk;
- alternate canonical recipe-chain splice rejection;
- ordinary direct-sentinel constructors and copied-object retention rejected,
  without a private-state adversary claim;
- strict production-consumer rejection of genuine and registry-injected V1
  candidates;
- zero kernel, outcome, planner, J0, fallback and proof replay in Stage C;
- route API absence of proof, bundle, caller identity and zero-counter inputs;
- copied candidate inputs and modified canonical bytes are rejected;
- all execution, counter, economics and sample-efficiency Gates remain locked.

## Explicit non-claims

This slice does not provide:

- a formal V7 route-upper or route-decision authority;
- nine shared-resource receipts or CounterRecord materialization;
- WorkVector or ComparisonVector production;
- an executed H1 business adapter;
- observed route-time access evidence or production current-identity authority;
- live/current issuer source or issuer-code provenance from the compile fixture;
- same-process unforgeability against private-state mutation;
- official production execution;
- scalar or vector workload-economics closure;
- sample-efficiency evidence.

Consequently the official-execution flag remains false and all three named
Gates remain `NOT_RUN`.
