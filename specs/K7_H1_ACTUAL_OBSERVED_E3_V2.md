# K7 H1 Actual-Observed E3 V2 Staged Contract

Status: normative construction specification only; implementation slice 1
absent.

Proposed contract: `2.0.59-E-C-E5B-B2`.

Profile key: `construction_k7_h1_actual_observed_e3_v2`.

Readiness: `SPECIFICATION_ONLY`.

## Exact current boundary

This document freezes the complete construction target that must replace the
internally launched process topology of E3 V1 before H1 can claim actual
route-wide process and working-set observations.  V15 only reserves disjoint
content domains for that target.  There is no V2 profile object, runtime
lease successor, guardian executor, E3 V2 completion, E4 V2 continuation,
route-wide actual-peak artifact, or positive runtime fixture in this slice.

The first implementation slice named below has **not** been implemented.
Consequently this specification and its domain registry are not evidence that
any process was born, placed, observed, released, terminated or reaped.  They
issue no `process.launches` value and no one may instantiate a reserved V15
domain with a caller-authored mapping and call it an issued object.

The final construction success target is one live, source-closed supervisor
route with exactly five registered route births, all individually permitted
and observed by the same external guardian:

1. `SUPERVISOR`;
2. `PIDFD_PROBE`;
3. `BROKER`;
4. `WORKER`;
5. `BUSINESS`.

The successful supervisor must retain the exact V2 E3 completion in-process,
continue directly into E4 V2 without another process birth, and remain alive
until its E4 V2 result and same-process authority are frozen.  Only after all
five processes are dead and consume-reaped, all three route leaves are empty,
and the E4 V2 output is complete may the guardian read the retained E5A outer
`memory.peak` OFD and close the runtime lease.

This is still a construction target.  Even after all implementation slices
pass, production FQ11 receipts and the formal
`CounterRecord -> WorkVector -> ComparisonVector` projection remain a
separate downstream Gate.

## Non-relabeling rules

The following predecessors remain frozen and cannot be silently upgraded:

- E3 V1 (`construction_k7_h1_exclusive_native_resource_broker_v1`) retains
  its V10 types, domains and claims.  It internally creates its capability
  probe, broker, WORKER and BUSINESS processes.  Wrapping that runner in a new
  supervisor would preserve those four internal births and therefore is not
  E3 V2.
- E4 V1 and E5B-A remain bound to exact E3 V1/E4 V1 runtime types and V10/V11
  identities.  Their outputs cannot be renamed as E3 V2 or E4 V2 artifacts.
- E5A remains a prelaunch-only V12 lease.  A V2 route must consume the exact
  issuer-owned live E5A lease through the explicit runtime successor defined
  below; serialized E5A documents and private-field introspection are not
  runtime authority.
- External Process Journal V1 is a nonauthoritative V14 structural reference.
  Its permit is not a launch gate, its cgroup identity is opaque, and it has no
  guardian-read PID cell.  Neither its record order nor a re-signed V14 object
  is acceptable V2 birth evidence.

V2 may reuse reviewed algorithms from E3 V1 and E4 V1 only behind new source
closures, exact V15 runtime types and independent V15 content domains.  It
must not mutate an old module, old artifact or historical claim.

## Exact successful topology

The external guardian is an already-running trusted controller and E5A lease
issuer, not one of the five registered route births.  If a future campaign
starts a separate guardian process inside an occurrence, that additional OS
launch must be charged separately; this specification cannot then imply a
formal `process.launches = 5` result by omission.

On the registered route, the five birth edges are exactly:

| Birth ordinal | Slot | Exact creator | E5A leaf | Required predecessor |
|---:|---|---|---|---|
| 1 | `SUPERVISOR` | external guardian | `CONTROL` | runtime lease `RUNNING` |
| 2 | `PIDFD_PROBE` | live supervisor | `CONTROL` | supervisor READY and E4 V2 context prepared |
| 3 | `BROKER` | live supervisor | `CONTROL` | probe death and creator reap complete |
| 4 | `WORKER` | live broker | `WORKER` | broker READY and E3 V2 payloads prepared |
| 5 | `BUSINESS` | live broker | `BUSINESS` | worker death and creator reap complete |

No successful route may create an extra admission probe, broker wrapper,
output writer, shell, Python helper, process monitor or cleanup process.  The
single `PIDFD_PROBE` slot is the capability probe consumed by this attempt;
running E3 V1's probe in addition is a sixth registered route birth and must
invalidate this five-slot completion.  E4 V2 executes in the supervisor and
has birth count zero.

The exact maximum planned concurrent route population is three:

- `SUPERVISOR + PIDFD_PROBE` in `CONTROL`, then the probe is reaped;
- `SUPERVISOR + BROKER` in `CONTROL`;
- while the broker is live, exactly one of `WORKER` or `BUSINESS` in its own
  leaf.

This schedule matches E5A's frozen `CONTROL=2`, `WORKER=1`, `BUSINESS=1` and
outer `pids.max=3` limits.  A later birth never overlaps the predecessor whose
creator-reap Gate it depends on.

## Execution-source closure and threat boundary

Before the runtime lease can enter `RUNNING`, one V15 execution-source closure
must bind the exact guardian protocol implementation and the sealed
interpreter, native launch trampoline and source images used by SUPERVISOR,
PIDFD_PROBE, BROKER, WORKER and BUSINESS.  It binds bytes, extents,
device/inode identities, immutable memfd seal sets, bootstrap argv/environment,
seccomp/no-new-privileges/capability policy, the V15 stage plan, all V10--V15
profile/domain dependencies, and the complete legal SCM/FD-transfer grammar.

The supervisor and broker launch paths must be single-threaded at every birth
Gate.  Their sandbox denies `fork`, `vfork`, `clone` and arbitrary `clone3`;
only the registered native trampoline and exact registered `clone3` arguments
may issue the one permitted birth.  The trampoline consumes a one-shot permit,
uses the slot-specific cgroup grant and shared PID cell, closes those grants,
and cannot be invoked a second time for the same slot.  Every child starts in
a minimal release stub and cannot enter role code before the guardian ACK.

The authority is conditional on this source-closed execution model, the Linux
kernel, cgroup v2, pidfd/`clone3`/`waitid`, `/proc`, SCM credential delivery and
the registered guardian.  It does not claim resistance to root, kernel/eBPF
injection, hostile native code outside the source closure, arbitrary mutation
of private Python state, machine power loss, or a compromised guardian.

## E5A runtime lease successor

The first executable prerequisite is a purpose-built successor that consumes
one exact, live, issuer-owned E5A
`H1RouteWideWorkingSetCgroupLeaseV1` in the same guardian process.  Content
documents, copied objects, a lease from another PID, a cleanup-pending lease,
or an independently opened look-alike cgroup are invalid.  Issuance must be an
explicit E5A-owned bridge; reading E5A private fields from an unrelated caller
does not transfer authority.

The normal one-way state chain is exactly:

```text
ACTIVE -> RUNNING -> PEAK_READ -> CLOSED
```

Failure may divert `RUNNING` or `PEAK_READ` into a retryable
`CLEANUP_PENDING`, but can never return to `ACTIVE` or `RUNNING`.  The bridge
must make the original E5A lease unavailable for independent verification or
cleanup while its successor is live.

Before `RUNNING`, the guardian repeats E5A topology, identity, cap, empty-leaf,
retained-`memory.peak`-OFD and baseline checks; freezes the source closure and
guardian session; pins an outer `cgroup.kill` control for failure cleanup; and
prepares no process.  Transition to `RUNNING` happens before the first birth
intent and is irreversible.

The guardian retains every canonical parent/outer/leaf/peak descriptor.  A
creator receives only a one-shot, slot-bound duplicate sufficient for its
registered `CLONE_INTO_CGROUP` trampoline.  It receives no parent cgroup,
outer `memory.max`, outer `memory.peak`, outer `cgroup.kill`, or reusable leaf
management authority.  The grant is closed by the creator immediately after
the clone transition and independently retired by the guardian after the
birth receipt.  No cgroup control descriptor survives into the child.

## Guardian-gated actual-birth protocol

Every one of the five slots must execute the following complete protocol in
ordinal order.  The same protocol and fields apply even when the guardian is
also the direct creator of `SUPERVISOR`.

### 1. Frozen pre-birth snapshot

The guardian verifies the exact runtime lease, expected live creator PID and
pidfd, expected full population of all three E5A leaves, all earlier death and
reap Gates, and the absence of every later slot.  It allocates a fresh
slot/attempt nonce, a child release channel, one one-shot cgroup grant and one
fresh shared PID cell.  It persists an exact birth intent before making the
permit available.

### 2. One-shot permit and kernel transition

The permit binds the intent, stage/slot/creator/cgroup identities, expected
pre-birth population, source closure, runtime lease and shared PID cell.  The
source-closed creator consumes that permit and invokes exactly one:

```text
clone3(
  CLONE_PIDFD |
  CLONE_PARENT_SETTID |
  CLONE_CLEAR_SIGHAND |
  CLONE_INTO_CGROUP
)
```

The child executes only the registered release stub.  It sends a credentialed
`CHILD_GATE_READY` packet and blocks.  It cannot exec the role image, receive
payload authority or perform business work before guardian release.

### 3. Guardian-read shared PID cell

The shared PID cell is a guardian-created, one-slot sealable memfd with exact
size and identity.  It is zero before permit.  The creator maps the registered
integer writable only for `CLONE_PARENT_SETTID`; the guardian retains its own
read-only mapping.  `CLONE_VM` is forbidden, but the child branch still
inherits the creator's writable `MAP_SHARED` mapping and descriptor.  The
source-closed native trampoline therefore has two mandatory pre-READY paths:
the parent branch unmaps and closes every creator-writable reference after
`clone3`, and the child release-stub branch unmaps and closes every inherited
writable mapping/descriptor before sending `CHILD_GATE_READY`.  The guardian
must observe both withdrawal acknowledgements and successfully add the final
`F_SEAL_WRITE`/immutable seal set before reading the cell directly from its
retained read-only mapping or persisting birth authority.  `F_SEAL_WRITE`
returning `EBUSY` is a protocol failure.  A sender-reported PID is never a
substitute for that read.

The frozen cell value must equal the clone return PID, pidfd `fdinfo` PID,
`CHILD_GATE_READY` SCM PID and registered slot PID.  The sealed trampoline is
part of the trusted boundary because a malicious creator could write a shared
mapping before it is finally sealed; V2 does not describe the cell as a
hardware-untamperable kernel log.

### 4. PIDFD escrow and live cgroup membership

Before release, the creator transfers exactly one `CLOEXEC` pidfd over its
prebound `SOCK_SEQPACKET`/`SO_PASSCRED` channel.  The guardian rejects missing,
extra, truncated or unknown ancillary data and closes every installed right
on rejection.  It binds SCM PID/UID/GID, pidfd identity and `fdinfo` PID,
process start ticks and the source-closed creator identity.

While the child remains live and blocked, the guardian reads membership from
the exact retained E5A leaf FD and `/proc/<pid>/cgroup`.  It repeats pidfd,
start-tick, leaf-directory and full `cgroup.procs` observations before and
after the read.  The expected leaf contains the new PID and the complete
three-leaf population equals the slot-specific frozen population; no opaque
cgroup ID or creator testimony may replace those observations.

### 5. Birth observation, ACK and release

Only after the cell, pidfd, child credentials, start identity and cgroup
membership all agree may the guardian persist
`ACTUAL_PROCESS_BIRTH_OBSERVED`.  It then persists an ACK preparation, freezes
the retained journal/FD inventory, sends the ACK, and records ACK sent.  The
creator may release the child only after receiving that exact ACK.  Release
failure or a child that executes before ACK is a protocol failure, never a
successful birth.

For each slot, accepted birth authority therefore means a real blocked child
was observed after a one-shot permit under the registered source-closed
creator program.  It is not inferred from record order, a PID number, a hash,
`pids.current`, or cgroup membership alone.

## Slot-specific ordering and liveness

After the supervisor is released, its exact preparer thread creates and
retains the E4 V2 continuation context before requesting the probe birth.  The
context is prebound into the later broker genesis and E3 V2 completion.

`PIDFD_PROBE` performs the single registered pidfd/clone/cgroup capability
probe.  Its death observation and supervisor consume-reap must finish before
the guardian can prepare the BROKER intent.  There is no second probe hidden
inside E3 V2.

The BROKER remains live while it creates the ten fresh target resources and
launches roles.  WORKER must close its channels/resources, die and be
consume-reaped by the broker before the BUSINESS intent exists.  BUSINESS
then follows the same path.  The broker performs the V2 equivalents of E3
ordinals 41--52 only after both role reaps, channel EOF, cgroup emptiness and
target-OFD inventory are complete.

The supervisor remains alive throughout probe, broker, both roles, broker
reap and E4 V2.  A supervisor exit before E4 V2 same-process completion is a
protocol failure even if portable files happen to exist.

## Death observation and creator reap authority

The guardian retains all five pidfds until their terminal protocol is closed.
Pidfd readiness supplies a non-consuming death observation; closing a pidfd,
seeing an empty cgroup or receiving EOF is not a reap.

Normal consume-reap ownership is exact:

| Slot | Normal consuming reaper |
|---|---|
| `SUPERVISOR` | external guardian |
| `PIDFD_PROBE` | supervisor |
| `BROKER` | supervisor |
| `WORKER` | broker |
| `BUSINESS` | broker |

For a nested child, the source-closed creator first performs
`waitid(P_PIDFD, WEXITED | WNOWAIT)`, reports the exact status over its
credentialed channel, then performs the consuming
`waitid(P_PIDFD, WEXITED)` and reports completion.  The guardian joins both
reports to its retained pidfd, death observation, creator PID/start identity
and source closure.  Because Linux does not allow a nonparent guardian to
consume-reap an arbitrary live creator's child, this is explicitly a
trusted creator-reap attestation, not a claim that the guardian independently
called `waitid`.

The guardian is a subreaper before the first birth.  If a creator dies, every
known orphan is killed through its retained pidfd and consume-reaped by the
guardian after reparenting.  That can close a failure cleanup but can never be
relabelled as the normal creator-reap chain or a successful V2 completion.

## E3 V2 semantic preservation

E3 V2 must preserve, under new V15 types and source closure, all substantive
E3 V1 target-resource obligations:

- ten broker-created target memfds in the same registered role/ordinal map;
- sealed immutable source-to-distinct-target copying;
- role-specific, non-overlapping legal transfer sets;
- SCM credentials, exact EOF and no unknown `SCM_RIGHTS`;
- exact WORKER and BUSINESS death/creator-reap evidence;
- broker inventory and `kcmp(KCMP_FILE)` last-legal-reference closure;
- normal cleanup barrier covering ordinals 41--52; and
- typed noncertificate closure on every incomplete/failure path.

The difference is architectural, not cosmetic: the guardian observes and
gates the already-registered BROKER, WORKER and BUSINESS births.  E3 V2 cannot
call the public E3 V1 runner or any helper that internally launches those
processes.

After both roles and the broker are exactly closed, the still-live supervisor
verifies the V2 native barrier and broker result, consume-reaps the broker, and
issues an exact process-local `ActualObservedE3V2Completion`.  This object
binds all five birth/death/reap chains, the runtime lease and source closure,
the E4 V2 context prebinding, the ten target closures and ordinals 41--52.  A
portable mapping, V10 completion or guardian-reconstructed clone is invalid.

## Live supervisor continuation to E4 V2

E4 V2 is a new exact-runtime-type adapter, not a relabelled E4 V1 completion.
It may reuse the reviewed V1 ordinal/fixed-point/writer algorithm, but it must
bind the V15 E3 V2 profile, source closure, exact retained E4 V2 context and
exact process-local V2 completion.

In the same supervisor process and preparer thread that retained the context,
E4 V2 must:

1. authoritatively reverify the exact E3 V2 completion and context prebinding;
2. produce the eight durable construction roles at ordinals 53--60;
3. close the exact joint output/read fixed point and ordinals 61--62;
4. perform the in-supervisor authoritative verification before releasing the
   retained context; and
5. persist/send a V15 in-supervisor completion while the supervisor pidfd is
   still live.

The guardian may then perform complete structural and persisted-file replay,
but cannot recreate the exact same-process call after supervisor death.  The
supervisor is released to exit only after the guardian has retained the E4 V2
completion and ACKed its exact bytes.  E4 V2 launches no process.

E4 V2 durable outputs remain construction witnesses until a later production
schema and semantic verifier consume them.  Names such as `COUNTER_RECORD_SET`,
`WORK_VECTOR` or `COMPARISON_VECTOR` inside the eight-role construction
fixture do not make those files formal artifacts.

## Route-wide peak and lease closure

After E4 V2 ACK, the supervisor closes and the guardian directly
consume-reaps it.  The guardian then requires:

- all five pidfds have terminal observations and exact normal creator-reap
  chains;
- `CONTROL`, `WORKER` and `BUSINESS` are empty and `populated 0`;
- the outer cgroup is empty;
- the E5A cap, hierarchy identity, peak baseline and retained peak OFD remain
  exact; and
- every one-shot cgroup grant, PID cell mapping, child gate, creator channel
  and escrow duplicate is closed or held in explicit cleanup quarantine.

Only then may the runtime successor transition `RUNNING -> PEAK_READ` and read
the retained outer `memory.peak` OFD exactly once for the route result.  The
observation binds the E5A baseline, final current, raw peak, cap, all five
birth/reap chains and E4 V2 completion.  It is never reconstructed from the
maximum of E3 V1 child leaves and never used to retroactively set the
prelaunch allowed-cap envelope.

Normal cleanup uses E5A's pinned hierarchy identities and retained peak OFD,
removes the exact child/outer names, closes every descriptor, and transitions
`PEAK_READ -> CLOSED`.  A close/removal failure enters retryable quarantine;
no closure is issued while a canonical or witness descriptor remains live.

## Failure and recovery boundary

Any protocol, source, permit, PID-cell, pidfd, credential, cgroup, ordering,
reap, E3, E4, peak or cleanup mismatch suppresses all normal V2 completion
claims.  The guardian retains the immutable primary failure, stops releases,
kills every known live descendant through pidfds and outer `cgroup.kill`,
drains channels, obtains creator or subreaper cleanup reaps, verifies cgroup
emptiness, records actual work already performed, and attempts retryable lease
cleanup.

Crash cleanup facts are a typed construction noncertificate.  They do not
mint ordinals 41--62, a plan certificate, infeasibility, process-count
authority, actual-peak authority or formal accounting.  Failure to prove
complete cleanup stays `CLEANUP_PENDING`/noncertificate and fails closed.

The external guardian may recover supervisor/broker/role process death while
it remains alive.  This contract does not promise restart recovery after the
guardian or machine dies, power-loss durability, or cleanup by an unregistered
daemon.

## Frozen implementation slices

Implementation must proceed in the following additive order; a later slice
cannot infer an earlier authority from portable bytes:

1. `RUNTIME_LEASE_AND_SUPERVISOR_BIRTH_SLICE`: implement the exact E5A runtime
   successor, source closure, guardian session, one real gated SUPERVISOR
   birth, shared-cell read, cgroup membership, direct guardian reap, peak read
   and cleanup in a bounded fixture.
2. `FIVE_BIRTH_TOPOLOGY_SLICE`: implement all five gated birth/death/reap
   paths and every ordering/failure attack with inert sealed role programs.
3. `E3_V2_SEMANTIC_SLICE`: replace E3 V1's four internal births with the
   registered guardian/creator edges while preserving target-resource and
   ordinals 41--52 semantics.
4. `E4_V2_AND_ROUTE_CLOSURE_SLICE`: keep the supervisor live through the new
   E4 V2 context/completion, then read the route-wide peak and close the lease.
5. `FORMAL_SHARED_RESOURCE_PROJECTION_SLICE`: separately convert verified
   production-native receipts into the registered FQ11 `CounterRecord`,
   `WorkVector`, `ComparisonVector` and actual-projection chain.

At the date of this specification:

```text
implementation_slice_1_present = false
implementation_slice_2_present = false
implementation_slice_3_present = false
implementation_slice_4_present = false
implementation_slice_5_present = false
actual_observed_e3_v2_execution_present = false
```

V15 domain registration is not slice 1.

## V15 content domains

V15 reserves 22 disjoint construction domains for:

1. profile;
2. staged plan;
3. execution-source closure;
4. E5A runtime lease successor;
5. guardian session genesis;
6. birth intent;
7. birth permit;
8. shared PID cell binding;
9. V2 pidfd escrow receipt;
10. cgroup membership observation;
11. actual birth observation;
12. guardian birth ACK;
13. creator release;
14. process death observation;
15. creator-reap attestation;
16. E3 V2 native cleanup barrier;
17. E3 V2 completion;
18. E4 V2 live-supervisor context;
19. E4 V2 in-supervisor completion;
20. route-wide actual-peak observation;
21. runtime lease closure; and
22. protocol-failure closure.

Every future issued object must use
`SHA256(domain-tag || 0x00 || canonical-json)` and reconstruct its complete
expected payload under an exact semantic verifier.  A content hash is not a
signature.  Caller-authored or coherently re-signed mappings remain
nonauthoritative without the exact live runtime chain required above.

## Required future acceptance and attack tests

Each implementation slice must add real-kernel positive fixtures and attacks
for at least:

1. exact V10--V15 domain separation and caller-minted object rejection;
2. copied/foreign/cleanup-pending E5A lease and private-field bridge rejection;
3. cap/topology/peak-OFD changes before `RUNNING` and before `PEAK_READ`;
4. birth before permit, duplicate trampoline call, reordered slot, early role
   execution and release-before-ACK;
5. sender-reported PID substitution, parent- or child-branch writable-cell
   retention, inherited child `MAP_SHARED`/FD leakage, `F_SEAL_WRITE` `EBUSY`,
   PID reuse, changed start ticks and crossed slot cells;
6. wrong/opaque cgroup, transient membership, hidden population, crossed
   leaf, leaked creator grant and inherited child control FD;
7. missing/extra SCM rights, wrong credentials, pidfd replacement and child
   READY from another PID;
8. probe/broker overlap, worker/business overlap, repeated capability probe
   and any sixth route birth;
9. close-without-reap, nonparent guardian wait misclaim, forged creator report,
   creator death before reap and subreaper cleanup without success relabelling;
10. use of E3 V1 public runner, V10 completion, V14 record or E5B-A attestation
    on a V2 authority path;
11. supervisor death before E4 V2 authority, foreign-thread continuation,
    extra output process and portable guardian replay substituted for
    same-process verification;
12. peak read before all reaps/emptiness, different peak OFD, child-peak
    relabelling, second reset and post-run peak used as the prelaunch upper;
13. failure after each birth, each reap, every E3 close ordinal and every E4
    output ordinal, with bounded pidfd/cgroup cleanup and immutable primary
    failure; and
14. fork/exec FD inheritance, close failure, numeric FD reuse, quarantine retry
    and no success/closure while any registered descriptor remains live.

Passing a partial slice proves only the exact bounded mechanism named by that
slice.  It cannot set any later-slice or formal flag.

## Locked current claims

All of the following are false, null or `NOT_RUN` in the current repository
state:

```text
e5a_runtime_lease_successor_present = false
guardian_gated_five_actual_births_present = false
guardian_read_shared_pid_cell_authority_present = false
guardian_verified_cgroup_membership_authority_present = false
creator_reap_authority_present = false
actual_observed_e3_v2_completion_present = false
live_supervisor_e4_v2_completion_present = false
route_wide_actual_peak_authority_present = false
production_shared_resource_receipts_present = false
fq11_counter_completeness_present = false
formal_counter_records_issued = false
formal_work_vector_issued = false
formal_comparison_vector_issued = false
formal_actual_projection_proof_issued = false
current_access_authority_present = false
formal_v7_authority_present = false
terminal_or_campaign_authority_present = false
complete_bundle_authority_present = false
official_execution_allowed = false
official_scalar_cost = null
official_N_break_even = null
COUNTER_COMPLETENESS_GATE = NOT_RUN
WORKLOAD_ECONOMICS_GATE = NOT_RUN
```

The only present result introduced here is a reviewed staged specification and
an additive domain registry.  It advances the construction plan without
claiming that the plan has executed.
