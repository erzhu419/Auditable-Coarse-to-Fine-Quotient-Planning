# K7 H1 Shared-Resource Catalogue Candidate V1

Status: Contract 2.0.58-C registered-template candidate. This profile does
**not** close a production structural source authority and does not issue a
numeric operand, route upper, route decision, execution authority, receipt,
CounterRecord, WorkVector, ComparisonVector, terminal certificate, or Gate
result.

Implementation:
`src/acfqp/construction_k7_h1_shared_resource_catalogues_v1.py`.

## What is actually frozen

The candidate binds the current H1 BROKER/WORKER/BUSINESS topology, V6 counter
registry, DIRECT_FALLBACK stage profile, and the preregistered serializer
template's 10 contexts and 90 leaves. It enumerates candidate common, I/O,
mount, memory, and launch sites and gives every template leaf a total partition
over those candidate sites.

This is useful as a finite hypothesis space and for omission/identity attacks.
It is not production lifecycle evidence. The serializer branch table itself is
not production-derived, so its site activation and failure prefixes cannot
authorize zeros or exact multiplicities.

The module freezes these status flags:

```text
predecision_structural_authority = false
predecision_structural_catalogue_candidate_present = true
production_branch_program_authority_present = false
numeric_shared_operand_issued = false
```

## Typed-unbound production blockers

Production promotion requires all of the following source-owned authorities:

- native common source-symbol multiplicities rather than one invented event per
  template anchor;
- per-admission I/O success, rejection, callback-failure, and ambiguity
  prefixes;
- mount-open intervals before first child visibility and mount-close intervals
  after trusted descendant reap, as required by shared-cap owner V2;
- native COPY physical identities from actual bytes/FD/occurrence evidence;
- native BIND inode and open-file-description replay;
- both WORKER and BUSINESS launch-existence ambiguity branches;
- preexecution extents, cgroup caps, `pids.max`, and outer membership evidence;
- the joint output/read fixed point;
- a post-run same-OFD memory-peak receipt, kept separate from preexecution upper
  evidence.

Until those exist, all derived formulae and branch prefixes are candidate-only.
In particular, the current `SHARED_CAP_EXHAUSTED_PRE_BUSINESS` template cannot
prove that staging and mount work is zero: a real rejection can occur after an
`n-1` successful admission prefix.

## COPY and BIND identity boundary

The public `derive_copy_structural_target_slot_id_v1` derivation demonstrates
that target and ordinal distinctions prevent equal-content deduplication. The
registered catalogue has no native bytes or FD at build time, however, so its
COPY rows contain only target-distinct structural slots. They are not
physical-instance evidence. The legacy `derive_copy_physical_instance_id_v1`
name is retained only as a fail-closed compatibility entry point and never
returns an ID.

The sealed runtime archive has a typed BIND alias *candidate* covering WORKER
and BUSINESS, but its inode/OFD replay is `REQUIRED_UNBOUND`. The two target
rows therefore retain distinct `BIND_UNRESOLVED_TARGET` slots. Calling the BIND
sharing derivation fails closed until a later native evidence authority exists.
The alias candidate exposes only `candidate_shared_instance_slot_id`; its
legacy `physical_instance_id` property fails closed. Content equality never
authorizes sharing.

The handwritten mount interval sweep remains a mathematical candidate only.
It is explicitly marked `owner_lifecycle_compatible = false`: some input rows
close before descendant reap, while output-role rows open after launch. Both
orders are rejected by shared-cap owner V2 and are covered by cross-module
negative tests.

## Memory evidence phases

The memory object is `H1MemoryScopeCandidateV1`, uses schema
`acfqp.h1_memory_scope_candidate.v1`, is content-addressed in the
`memory-scope-candidate` domain, and exposes only
`h1_memory_scope_candidate_id`. The candidate plan requires BROKER, WORKER,
and BUSINESS to share
one continuous scope. It requires the BROKER to retain the memory-peak OFD
while the two descendants are reaped and then read that same OFD. These are
plan obligations, not claims that native membership or retained-OFD evidence
already exists.

Evidence is split by phase:

- preexecution numeric blockers: memory hard cap, outer route-wide cap, BROKER,
  WORKER, and BUSINESS caps, plus outer `pids.max`;
- preexecution evidence blocker: outer cgroup PID membership replay;
- post-run actual blocker: retained same-OFD memory-peak readback.

The post-run actual may not authorize a preexecution upper. The candidate PID
membership floor of three is not authoritative until both `pids.max` and
membership evidence are bound.

## Launch and output admissions

The launch object is `H1LaunchCatalogueCandidateV1`, uses schema
`acfqp.h1_launch_catalogue_candidate.v1`, is content-addressed in the
`launch-catalogue-candidate` domain, and exposes only
`h1_launch_catalogue_candidate_id`. The registered child-site order is WORKER
then BUSINESS, with an upper of two
launches. It is not a production launch-prefix authority. The serializer
template has a WORKER ambiguity context but no BUSINESS launch-existence
ambiguity context, so ambiguity coverage is explicitly incomplete.

Every template branch records output and memory admissions as intervals
`[0, 1]`, not exact multiplicity one. In particular, a memory-first rejection
can leave output admission at zero.

## Future-state separation

The recursive guard rejects later DecisionPoint, RouteDecisionContext, route
upper envelope, formal V7 route upper/decision, selected route, freeze
attestation, post-run result, and actual WorkVector/ComparisonVector identities.
Re-signing a document after injection does not bypass exact canonical replay.

The only successful public accessors use `registered_*_candidate_v1` names.
Previous `official_*` accessors and the unsuffixed verifier fail closed and
never return a candidate. Likewise, the legacy memory, launch, and inode/OFD
alias authority constructors and `authority_id` properties fail closed; they
cannot alias the candidate classes or candidate IDs.

## Acceptance boundary

The focused suite establishes only:

1. exact replay of the registered candidate bytes and all 90 template leaves;
2. total partitions relative to the candidate site universe, never production
   reachability;
3. target-distinct COPY slots and unresolved BIND slots;
4. fail-closed BIND sharing while inode/OFD evidence is absent;
5. separation of preexecution memory blockers from the post-run peak receipt;
6. explicit missing BUSINESS ambiguity and production-prefix flags;
7. direct negative demonstrations that the handwritten mount schedule violates
   shared-cap owner V2 lifecycle rules;
8. future-field, branch-omission, wildcard, and missing-as-zero attacks fail.
9. memory and launch class/schema/domain/ID identities are candidate-specific,
   while every legacy official or authority-shaped API fails closed.

## Locked state

```text
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
WORKLOAD_ECONOMICS_GATE_NOT_RUN
COUNTER_COMPLETENESS_GATE_NOT_RUN
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```
