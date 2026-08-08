# K7 H1 lifecycle caller-pinned local-Git provenance V1

Status: Contract `2.0.59-A`, caller-pinned construction provenance only.

This contract freezes the Contract-`2.0.58-D` migration seed in an exact local
Git history and independently replays its declarative transition and branch
semantics. It deliberately does **not** call that result source authority: the
expected anchor ID still comes from the caller, the registered component set
is not a transitive dependency closure, and no fresh-exec byte binding exists.

## Non-circular K -> C record

`K` contains the producer, independent verifier, central domains, an immutable
program snapshot, and twelve explicitly registered component blobs. It does
not contain the final preregistration. Its single-parent child `C` must add
exactly one `100644` file:

`specs/K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1.json`.

The document freezes `expected_parent_commit_id = K`, every registered Git
mode/blob/SHA-256/extent, the program-snapshot ID, program ID and independently
derivable branch-analysis ID. It contains no `C` ID, so there is no Git-ID
cycle. The verifier disables replace objects, requires SHA-1 object format,
checks object types, rejects shallow repositories, selects the first qualifier
on local `main`, proves the
single-parent/ancestor relation, proves the exact one-file `K..C` diff, and
rechecks the final mode/blob and all registered blobs at current local `main`.

## Independent snapshot replay

The verifier does not import the lifecycle-candidate module. From the frozen
snapshot bytes it independently verifies and derives:

- the program content ID;
- 62 ordered and state-contiguous transitions;
- operation-specific failure-edge documents;
- 143 declared failure edges;
- nine resource-prefix partitions for every first-failure prefix;
- 144 branch documents and the branch-analysis content ID;
- the snapshot content ID.

This proves the exact declarative snapshot and its internal derivations. It
does not prove that the snapshot is a complete production lifecycle or that
the twelve registered files are a complete semantic dependency closure. The
source-manifest, topology and output-DAG IDs inside the snapshot are pinned
content-ID-shaped references, not independently rederived dependency
bindings: `snapshot_dependency_semantic_binding_complete=false`.

## Caller-pinned inspection boundary

The only positive inspection API is:

```python
inspect_h1_caller_pinned_lifecycle_provenance_v1(
    repository_root,
    expected_anchor_id=caller_argument,
)
```

It compares the explicit caller argument with the independently derived local
anchor and performs one instantaneous worktree equality observation. The
result explicitly records:

- `external_expected_anchor_binding_present = false`;
- `source_authority_present = false`;
- `fresh_import_self_mint_prevented = false`;
- `worktree_execution_bytes_verified = false`;
- `toctou_exclusion_present = false`;
- `usable_as_execution_source = false`.

Thus the K -> C record disables a zero-argument self-mint path and supplies
stable local provenance, but a later activation/RouteDecisionContext must bind
the expected anchor ID before execution, and a fresh-exec mechanism must pin
the actually loaded bytes. A one-time path read is never persisted as source
authority.

The source registry is exactly an
`EXPLICIT_NON_TRANSITIVE_PINNED_BOUNDARY`. Its twelve rows are complete for
that declared set; transitive dependencies, loaded modules and the test source
are not claimed complete.

## Remaining boundary

The snapshot remains a migration seed. It lacks live broker/worker/business
dispatch, complete post-failure cleanup, owner V3 exact settlement,
attempt-wide one-shot rejection, output-DAG leaf joins, common multiplicities,
native extents/physical identities, numeric operands, formal V7 routing,
CounterRecords, WorkVector, ComparisonVector and terminal/campaign closure.

The user-required no-push workflow also means `remote_published=false`.
Official execution, scalar/break-even, workload economics, Counter
Completeness and sample-efficiency remain locked or `NOT_RUN`.

## Attack coverage

- K without C is `NOT_READY`;
- wrong parent, merge-like ancestry or any extra `C` tree change fails;
- final mode changes and registered-blob drift fail;
- Git replace refs cannot influence replay; shallow and non-SHA-1 repositories fail;
- snapshot field/transition mutation fails even after coherent re-signing;
- unknown final fields, caller-ID substitution and private-object mutation fail;
- worktree mutation fails the instantaneous inspection;
- zero-argument source-authority factories fail closed.
