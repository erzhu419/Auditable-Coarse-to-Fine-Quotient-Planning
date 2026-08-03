# K7 Production Shared-Cap Engine V2 — Preproduction Lock

Status: preproduction scaffold; no production execution authority.

Proposed contract: `2.0.49`

Profile key: `production_shared_cap_engine_v2_preproduction_locked`

## Frozen boundary

The successor shared-cap family is separate from the construction V1 family.
It has distinct schemas, local domain-tag candidates and issuer registries.
The only activation state which this revision can issue is:

```text
V7_AUTHORITY_PENDING
```

It is not a formal route decision. It does not accept a construction
prerequisite. It cannot activate production execution.

The public engine is an exact immutable tuple capability with no reachable
mutable backing object. Each reserved owner name is paired only with the
non-callable `V7_AUTHORITY_PENDING` sentinel; this revision exposes no callback
method. Tuple subclasses do exist, but the verifier requires `type(value) is
tuple` plus exact live issuer identity, so neither a subclass nor a caller-
created exact tuple is an authority. `gc.get_referents` reaches only immutable
tuple/string members. No private live owner kernel exists; the private issuance
name also fails unconditionally.

## Nine embedded owner boundaries

Each reserved owner name fixes its own path and site key. No API accepts a
caller-selected counter path, and none of the names is callable in this
revision.

1. `record_hash_invocation` → `common.hash_invocations` / `shared.hash`
2. `record_integrity_check` → `common.integrity_checks` / `shared.integrity`
3. `record_protocol_check` → `common.protocol_checks` / `shared.protocol`
4. `open_mounted_payload` → `io.mounted_bytes_peak` / `shared.mount`
5. `begin_route_output` → `io.output_bytes` / `shared.output`
6. `read_registered_payload` → `io.read_bytes` / `shared.read`
7. `stage_registered_payload` → `io.staged_bytes` / `shared.stage`
8. `bind_working_hierarchy` → `memory.working_bytes_peak` / `shared.memory`
9. `launch_registered_role` → `process.launches` / `shared.launch`

The engine document freezes the complete site table and required semantics.
Executable methods may appear only in a future isolated and authenticated V7
adapter.

## Successor V7 obligations

Before any method can execute, a new V7 adapter must independently verify and
bind all of the following:

- a formal FALLBACK route decision and V7 aggregate cap upper;
- an atomic cap-receipt plus semantic-event commit authority;
- full conservative charge and `PROTOCOL_FAILURE` on callback or journal
  exception;
- a whole-route output fixed point reserved before the first launch and a
  trusted exact-output finalizer;
- positive native launch edge plus matching pidfd, trusted no-child evidence,
  and ambiguous-launch full charge;
- distinct mounted-payload identities, child-visibility intervals, trusted
  descendant reap and cleanup after failure;
- a memory hierarchy cap bound before launch and a retained same-OFD
  `memory.peak` read after trusted descendant reap;
- close-time proof that no output reservation, mount or working binding remains;
- formal CounterRecord materialization and independent replay.

Caller booleans, content-ID strings, byte counts and launch outcome enums are
not trusted substitutes for those authorities.

## Claims that remain false

```text
formal_v7_route_decision_authority_present = false
production_execution_authorized = false
production_owner_sites_wired = false
source_site_manifest_semantically_verified = false
formal_actual_compliance_eligible = false
official_execution_allowed = false
```

The receipt/event/pair domain strings in the module are registration candidates
only. The local identity helper explicitly rejects all three domains; this
revision mints no receipt, semantic event or atomic pair.
