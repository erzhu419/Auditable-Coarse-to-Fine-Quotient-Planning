# K7 H1 Native Resource Receipt Journal V1

## 1. Status and authority boundary

This document specifies the behavior implemented by
`construction_k7_h1_native_resource_receipt_journal_v1.py` together with the
additive V6 domain registry. The schema version is `1.0.0`, the profile key is
`construction_k7_h1_native_resource_receipt_journal_v1`, and the proposed
contract version is `2.0.59-E-C-NATIVE-A`.

The profile is construction evidence for twelve H1 native-resource sites. It
predeclares their slots before normal ordinal 1, records a durable callback
start before invoking native code, records a typed callback result before the
corresponding normal-site event can be committed, and creates the final
present/absent resolution only after binding that result to the exact durable
normal-site event.

The profile is not kernel or route authority. In particular, all of the
following public claim values are fixed:

| Claim | Value |
| --- | --- |
| Native-resource slot predeclaration present | `true` |
| Native-resource receipt journal present | `true` |
| Exact native cutoff snapshot present | `true`, only in the scope defined in Section 10 |
| Callback replay after durable start forbidden | `true` |
| Callback result before normal event present | `true` |
| Native receipt before normal event present | `false` |
| Same-broker initialization convergence present | `true` |
| Cross-process initialization recovery present | `false` |
| Normal failure-event semantic verification present | `false` |
| V2 transition integration present | `false` |
| Real kernel credential authority present | `false` |
| Native cleanup authority present | `false` |
| Current-access authority present | `false` |
| Production execution authority present | `false` |
| Formal counter records issued | `false` |
| Formal work vector issued | `false` |
| Formal comparison vector issued | `false` |
| Formal V7 route authority present | `false` |
| Official execution allowed | `false` |

No receipt, absence resolution, replay view, or cutoff snapshot may be
interpreted more strongly than those values.

## 2. Domain separation and content identities

The additive V6 registry contains exactly these nine disjoint domain tags:

| Object | Domain tag |
| --- | --- |
| Receipt-journal spec | `acfqp:construction-k7-h1-native-receipt-spec:v1` |
| Slot declaration | `acfqp:construction-k7-h1-native-slot-declaration:v1` |
| Allocation | `acfqp:construction-k7-h1-native-receipt-allocation:v1` |
| Callback start | `acfqp:construction-k7-h1-native-callback-start:v1` |
| Callback result | `acfqp:construction-k7-h1-native-callback-result:v1` |
| Present-resource receipt | `acfqp:construction-k7-h1-native-resource-receipt:v1` |
| Absence resolution | `acfqp:construction-k7-h1-native-absence-resolution:v1` |
| Journal cursor | `acfqp:construction-k7-h1-native-receipt-cursor:v1` |
| Cutoff snapshot | `acfqp:construction-k7-h1-native-cutoff-snapshot:v1` |

For a registered domain `D` and payload `P`, the content identity is

```text
SHA-256(UTF-8(D) || 0x00 || canonical_json_bytes(P))
```

and is represented as one lowercase 64-hex content ID. An unregistered domain,
a non-string domain, or a domain containing NUL fails closed. The hashes are
domain-separated content identities; they are not signatures, secrets, kernel
credentials, or proof that a native resource exists.

The callback-cell nonce commitment and opaque capability identity use their own
fixed SHA-256 labels in the implementation. They are not additional V6 registry
entries and do not change the authority boundary above.

## 3. Frozen context and predeclaration gate

`freeze_h1_native_receipt_journal_spec_v1` accepts one exact issuer-owned H1
normal-prefix handle and an existing receipt-base directory. It resolves and
freezes the base realpath, device, and inode.

Spec creation succeeds only while the bound normal-prefix journal is exactly at
genesis:

- status is `READY`;
- completed-event count is zero;
- next ordinal is 1; and
- there is no dangling normal-site intent.

Spec construction holds the exact normal-prefix journal lock from genesis
validation through construction of the content-addressed spec object. Journal
initialization independently holds that same lock from genesis validation
through receipt allocation and initialization-completion publication. A
concurrent ordinal-1 transition therefore cannot cross either gate; the lock
order is normal journal before receipt-root allocation lock.

The spec binds the receipt journal to the normal-prefix spec, normal-prefix
allocation, genesis snapshot, anchored lifecycle program and handler registry,
logical occurrence, route attempt, decision point, and transaction. Journal
initialization derives the locked normal state again and requires the same
genesis snapshot and zero completed events. Thus, both declaration and
allocation are atomically ordered before normal ordinal 1.

## 4. Exact native-resource slot registry

The profile contains exactly ten OFD slots followed by two PIDFD slots. Every
slot has broker role `BROKER`, is marked as predeclared before normal ordinal 1,
and states that its raw descriptor is not authority.

| Index | Normal ordinal | Normal site key | Resource role | Kind |
| ---: | ---: | --- | --- | --- |
| 1 | 7 | `mount-open:WORKER:sealed_runtime_archive` | `WORKER` | `OFD` |
| 2 | 9 | `mount-open:WORKER:ipc_binding_candidate` | `WORKER` | `OFD` |
| 3 | 11 | `mount-open:WORKER:execution_topology_profile` | `WORKER` | `OFD` |
| 4 | 13 | `mount-open:BUSINESS:sealed_runtime_archive` | `BUSINESS` | `OFD` |
| 5 | 15 | `mount-open:BUSINESS:business_request_candidate` | `BUSINESS` | `OFD` |
| 6 | 17 | `mount-open:BUSINESS:owned_engine_source` | `BUSINESS` | `OFD` |
| 7 | 19 | `mount-open:BUSINESS:owned_engine_authority_document` | `BUSINESS` | `OFD` |
| 8 | 21 | `mount-open:BUSINESS:kernel_replay_document` | `BUSINESS` | `OFD` |
| 9 | 23 | `mount-open:BUSINESS:query_replay_document` | `BUSINESS` | `OFD` |
| 10 | 25 | `mount-open:BUSINESS:fallback_cap_profile` | `BUSINESS` | `OFD` |
| 11 | 26 | `launch:WORKER` | `WORKER` | `PIDFD` |
| 12 | 30 | `launch:BUSINESS` | `BUSINESS` | `PIDFD` |

The exact slot key is `native-slot:<two-digit-index>:<normal-site-key>`. Each
slot declaration has its own domain-separated content ID. Slot keys, slot IDs,
normal ordinals, site keys, resource roles, and capability kinds are replay
invariants. Exported construction-template rows and the module lookup are
read-only mappings. After spec freeze, issuance, cutoff construction, and replay
derive their slot lookup from the declarations sealed into that exact spec,
not from mutable or replaceable module-level containers.

## 5. Allocation and durable filesystem layout

For receipt base `B` and route-attempt ID `R`, initialization uses:

```text
B/.acfqp-k7-h1-native-resource-receipts-v1/
  .allocation.lock
  attempt-R/
    spec.json
    root-anchor.json
    journal.lock
    journal.cursor
    allocation.json
    initialization.complete.json
    cursor-high-water-0000-<cursor-id>
    record-<four-digit-sequence>-<kind>-<record-id>.json
  root-seal-R                                      # hard link to root-anchor.json
  allocation-seal-R                                # hard link to allocation.json
  cursor-seal-R                                    # hard link to journal.cursor
```

The root and attempt directories are mode `0700`. Immutable objects are mode
`0400`; the journal lock and cursor are mode `0600`. The root anchor,
allocation, and cursor must each have exactly the primary name plus its root
hard-link seal. The journal lock and each immutable record/high-water object
must have exactly one link.

The allocation freezes the root, attempt, anchor, lock, and cursor physical
identities; the anchor content hash; the spec ID; route-attempt ID; original
broker process and thread IDs; and the twelve-slot cardinality. A handle also
retains those device/inode identities and is deliberately non-serializable.

Initialization is serialized by the root allocation lock. Repeating
initialization for an exact existing allocation is idempotent. Incomplete
initialization converges only when every recognized already-created object
matches the expected bytes, type, mode, and identity. The implementation has
explicit crash and recovery points after attempt-directory creation, cursor
fsync, allocation publication, and seal-directory fsync. A crossed spec,
allocation, anchor, seal, or initialization marker fails closed.

The first successful allocation publication fixes the broker process/thread
issuer. Opening or reinitializing an existing allocation does not transfer that
issuer role. Recognized crash points converge only in that same process and
thread. A different process or thread must be rejected before it publishes any
recovery seal or initialization-completion marker; process death therefore
consumes the allocation and requires higher-level noncertificate closure rather
than broker takeover.

## 6. Journal representation and replay invariants

Each durable semantic record is one canonical JSON object in a mode-`0400`
immutable file. Record filenames carry a contiguous one-based sequence, one of
the registered record kinds, and the record content ID. The record schema,
filename kind, filename ID, exact field set, domain-separated content ID, frozen
context, and slot binding must all agree.

`journal.cursor` is an append-only canonical-JSON-lines chain. Row 0 is genesis
and binds the spec ID. Every later cursor row binds its sequence, previous
cursor ID, record kind, and record ID. A zero-length immutable high-water object
binds each durable cursor sequence and cursor ID.

Replay reconstructs the expected cursor from immutable records. A cursor that
is an exact byte prefix of that reconstruction, including a truncated final
row, may be completed and fsynced. The high-water chain must be contiguous and
may be at most one record behind the immutable record prefix; the missing
high-water object is then published. A cursor divergence, record gap, record
rollback below immutable high water, changed physical identity, extra hard link
to a sealed or record object, or content/context mismatch fails closed.

Within the semantic record stream:

- callback starts have strictly increasing native-slot normal ordinals;
- an exact normal-site intent is used by at most one native slot;
- a new start is allowed only when every earlier start has an event-bound final
  resolution;
- a callback result, if present, occurs exactly once and immediately after its
  start;
- a present receipt or absence resolution, if present, occurs exactly once and
  immediately after its callback result;
- an exact normal-site event is used by at most one native slot; and
- a cutoff is terminal, so any record after it makes replay fail.

The replay view reports each slot as `NOT_STARTED`, `UNRESOLVED`,
`KNOWN_PRESENT`, or `KNOWN_ABSENT`. A slot with a durable start but without an
event-bound final resolution is `UNRESOLVED`, whether or not a callback-result
record also exists. `callback_replay_forbidden_slots` contains every slot that
has a durable start, including slots that later received a final resolution.

## 7. Broker and normal-journal lock discipline

Semantic-record mutation after allocation requires the exact process and thread
captured by the allocation. A different thread fails closed. A forked process
or forked callback continuation raises
`H1NativeForkedCallbackContinuationV1` and cannot mint a broker record or
callback observation.

The mutation entry points refuse to run inside an already-active normal-prefix
lease because V2 integration is absent. They acquire the bound normal journal
lock first, derive current normal evidence, and then acquire the native journal
lock. Callback execution holds the normal lock across durable start,
user-supplied native callback, and durable callback result. This is the
implemented basis for the result-before-normal-event ordering claim.

Numeric process/thread equality and local issuer sentinels are construction
guards. They are not authenticated kernel credentials, a general process
identity protocol, or resistance to an adversary that can mutate same-process
private state.

## 8. One-shot native callback protocol

`execute_h1_native_resource_callback_once_v1` implements this sequence:

1. Require a known predeclared slot, a callable callback, the allocation's exact
   broker process/thread, and no active unintegrated normal lease.
2. Require the supplied content ID to be the exact current dangling normal-site
   intent: the frozen context, ordinal, site key, completed-event count
   `ordinal - 1`, and non-failed normal state must all match.
3. Under the native lock, require no cutoff, no prior start for the slot, no
   intent reuse, no unresolved earlier start, and no backwards slot order.
4. Generate a 32-byte callback nonce and durably append a `START` record with a
   commitment to that nonce before calling native code. The start state is
   `STARTED_WITHOUT_RESULT` and permanently forbids callback replay.
5. Invoke the callback inside one active callback cell bound to allocation,
   slot, start ID, nonce, process, and thread.
6. Accept only an exact issuer-created, not-yet-consumed typed observation from
   that cell and require its capability kind to equal the predeclared slot kind.
7. Consume the observation once, erase the observation object's raw-descriptor
   reference, and durably append one `CALLBACK_RESULT` with binding status
   `PENDING`.

The callback must return exactly one observation created by one of:

- `observe_h1_native_present_v1(raw_descriptor, capability_kind=...)`, which
  accepts an exact nonnegative integer and produces `KNOWN_PRESENT`; or
- `observe_h1_native_absent_v1(capability_kind=..., reason=...)`, which requires
  a nonempty exact reason string and produces `KNOWN_ABSENT`.

Neither observation function is usable outside the active callback cell. An
observation cannot be reused across callbacks, slots, starts, or allocations.

For `KNOWN_PRESENT`, the durable result contains a fresh opaque capability
identity derived from the start ID and fresh randomness. The implementation
checks non-reuse within the allocation. The opaque identity is not derived from
the descriptor, is not a kernel credential, and is not usable to access or
clean up the resource. For `KNOWN_ABSENT`, the result contains a typed null for
the opaque identity and the callback's nonempty reason.

No raw descriptor value is serialized or retained by the receipt journal. The
journal does not close, reap, validate, duplicate, or otherwise manage the
descriptor. It does not verify that the integer names an open descriptor, that
its kernel type matches `OFD` or `PIDFD`, that it names the expected resource,
or that the callback's absence reason is externally true.

### Crash and exception rule

The durable start is written before callback invocation. Therefore:

- a crash after start fsync invokes no callback and leaves a start without a
  result;
- a callback exception, process failure, or injected crash after callback
  return but before result fsync also leaves a start without a durable result;
  and
- no public API may invoke that slot's callback again.

The uncertain slot is permanently unresolved within the allocation. This is an
intentional at-most-once rule: the profile sacrifices automatic retry rather
than infer that native side effects did or did not occur. A missing durable
result is never converted into `KNOWN_ABSENT`.

## 9. Binding a result to the exact normal event

`bind_h1_native_callback_result_to_normal_event_v1` accepts only an
issuer-created pending result from the same allocation and an issuer-owned
normal-site event commit. The event must:

- match the frozen context, slot ordinal, site key, and original intent ID;
- be durably present in the bound normal journal;
- be the latest durable normal event;
- make the completed-event count equal the slot ordinal; and
- leave no dangling normal intent.

The durable pending document must exactly equal the result stored for that
slot. The slot must have no prior final resolution, the event must not have been
used by another native slot, and no cutoff may exist.

A `KNOWN_PRESENT` result produces an issuer-owned
`H1NativeResourceReceiptV1`. A `KNOWN_ABSENT` result produces an exact absence
resolution document. Both bind the original start and result IDs, creating
process/thread, slot/context, normal intent, and exact normal event. Both state
that the callback result was durable before the normal event and that the final
resolution was created after exact event binding.

The binder does not require the normal event outcome to be `SUCCESS`; it binds
the exact durable event supplied by the normal layer. It does not create a
receipt before that event. If the normal journal advances beyond the event
before binding, immediate-event binding fails closed.

## 10. Exact native cutoff snapshot

`freeze_h1_native_cutoff_snapshot_for_v2_transition_v1` requires an
issuer-owned normal event that is the exact current durable first-failure event:
its context must match, its ordinal must lie inside the normal prefix, its
outcome must not be `SUCCESS`, `declared_first_failure` must be `true`, it must
be the latest event, its ordinal must equal the completed-event count, and the
normal journal must be failed.

The resulting cutoff snapshot binds:

- that primary failure ordinal and event ID;
- the normal spec and allocation;
- the native spec and allocation;
- the native cursor sequence/head immediately before the cutoff record;
- the ordered IDs of every native evidence record before the cutoff; and
- one typed classification for each of the twelve slots plus exact counts.

Slot classification at cutoff ordinal `F` is:

| Condition | Cutoff classification |
| --- | --- |
| Event-bound present receipt exists | `KNOWN_PRESENT`, with receipt ID and opaque identity |
| Event-bound explicit absence resolution exists | `KNOWN_ABSENT`, with callback reason and resolution-record ID |
| Slot ordinal is greater than `F` and no evidence exists | `KNOWN_ABSENT`, reason `SITE_NOT_REACHED_BEFORE_EXACT_CUTOFF`, with typed-null `CONTROL_FLOW_ABSENCE` record ID |
| Slot ordinal is at most `F`, but no event-bound resolution exists and a start exists | `UNRESOLVED`, reason `START_WITHOUT_EVENT_BOUND_RESULT`, with available start/result IDs and replay forbidden |
| Slot ordinal is at most `F`, but no start exists | `UNRESOLVED`, reason `REQUIRED_NATIVE_SITE_EVIDENCE_MISSING`, with typed-null start/result IDs and a false per-slot replay-forbidden flag because no durable start exists |

Evidence for a slot after `F` is inconsistent with the claimed cutoff and fails
closed. The twelve classifications are exhaustive, and their present, absent,
and unresolved counts sum to twelve.

The cutoff record is appended after the evidence prefix it names. Once appended,
it seals the journal against further starts, result bindings, or a second
cutoff; any later record causes replay failure.

`exact_cutoff_for_v2_transition = true` has one deliberately narrow meaning:
the snapshot is an exact, content-bound classification of the native receipt
journal prefix at the bound normal failure. Its declared scope is exactly
`NATIVE_RECEIPT_JOURNAL_PREFIX_ONLY`. It does not independently validate the
semantic truth of the normal layer's failure declaration and is not integrated
into a V2 transition. A future-slot control-flow absence exists only in the
cutoff snapshot; it does not append an absence-resolution record and does not
change the ordinary replay status of that unstarted slot from `NOT_STARTED`.

## 11. Fail-closed cases exercised by the focused suite

The focused tests exercise at least the following boundaries:

- exact 10-OFD plus 2-PIDFD predeclaration at normal-prefix genesis;
- convergence from each explicit initialization crash point;
- out-of-order slot/current-intent rejection without journal mutation;
- present and explicit-absence result/event binding;
- absence of serialized raw descriptor values;
- observation single consumption and allocation/slot/kind binding;
- no replay after start-only or callback-before-result failures;
- unresolved and control-flow-absent cutoff classifications;
- terminal cutoff enforcement;
- cross-allocation pending-result, record, and event rejection;
- forged result/receipt semantic rejection despite recomputed content IDs;
- foreign-thread, forked-broker, and forked-callback rejection;
- strict-prefix cursor repair; and
- rollback, lock replacement, hard-link seal, and record-link attacks failing
  closed.

Passing this suite establishes only the implemented construction protocol and
its tested failure cases. It does not upgrade any explicit `false` claim in
Section 1.

## 12. Explicit nonclaims

This profile does not claim any of the following:

- that a raw descriptor is valid, open, correctly typed, correctly owned,
  credential-bearing, or still live;
- that an opaque capability identity is a kernel capability, credential, file
  descriptor, cleanup token, or current-access token;
- descriptor close, PIDFD reap, native cleanup, or leak freedom;
- atomic integration with the normal-site executor or a V2 transition;
- independent semantic validation of a normal failure declaration;
- production execution, official execution, formal counter/work/comparison
  issuance, or formal V7 route authority;
- cryptographic signer authenticity merely from SHA-256 content identities;
- replay/retry availability after an uncertain native callback start; or
- resistance to a same-process private-state adversary or to hostile mutation
  between validation checkpoints.

These are contract boundaries, not deferred implications. They remain false
until a separately specified and tested successor explicitly supplies them.
