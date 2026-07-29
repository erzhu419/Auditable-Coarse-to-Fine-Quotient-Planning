# V0-072 Final Preregistration and Remote-Main Anchor

Status: two chains anchored; both attempts failed as protocol
noncertificates; V0-072 attempt authority is exhausted.

## Dependency direction

The identity graph is strictly one-way:

```text
source reconstruction recipe
    -> final confirmatory execution manifest binding recipe_id
        -> final preregistration binding manifest_id
            -> remote-main anchor binding all three IDs and Git objects
```

The manifest contains neither `preregistration_id` nor
`final_preregistration_id`. Its boolean
`final_preregistration_id_embedded=false` records that invariant but is not an
embedded identity. The final preregistration is the frozen V0-072 draft with
only these pre-anchor changes:

- `confirmatory_execution_manifest_id = <non-null manifest ID>`;
- `confirmatory_profile_finalized = true`;
- `anchor_commit_id = null`;
- `target_execution_allowed = false`.

Every law, seed domain, context, arm, schedule, threshold, confidence
allocation, cap, terminal code and endpoint remains byte-identical to the
draft authority. The logical verifier recomputes both content IDs and rejects
any other change. Its attestation is nonauthorizing and records zero registered
observer calls.

## Tracked artifact locations

The future triple has these fixed repository-relative paths:

```text
specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json
specs/V072_CONFIRMATORY_EXECUTION_MANIFEST.json
specs/V072_FINAL_PREREGISTRATION.json
```

They are intentionally outside ignored `artifacts/` storage. Tests require
`git check-ignore` to report all three paths as trackable and require all three
blobs to appear in `git ls-tree` for the same qualifying commit.

## Anchor claim

An untrusted anchor claim binds:

- repository URL and branch `main`;
- commit, tree and exactly one parent commit;
- all three repository paths and blob object IDs;
- source recipe, final manifest and final preregistration IDs;
- verification scope.

The claim is never an execution authority.

## Independent Git replay

The independent verifier is read-only and invokes no network operation. It
requires:

1. a clean worktree whose `HEAD` is attached to `refs/heads/main`;
2. `HEAD`, local `main`, and `refs/remotes/origin/main` all equal the claimed
   commit;
3. exact origin fetch and push URLs;
4. real commit, tree, parent and blob objects matching every claimed ID;
5. canonical JSON bytes from all three committed blobs, not the worktree;
6. independent source-recipe validation of its fixed constructor, verifier,
   contexts, checkpoints, randomness, six output IDs, compact identity graph,
   five Merkle commitments/counts and completeness/blocker logic;
7. exact equality between the committed `recipe_id`, the manifest global
   recipe binding, claim and attestation;
8. independent recomputation of the one-way manifest/preregistration pair;
9. a parent that lacks both recipe and final-preregistration IDs;
10. no earlier addition or removal of either ID in the parent ancestry.

The last condition rejects remove/re-add attempts even when the immediate
parent lacks the ID.

For offline tests,
`DEVELOPMENT_LOCAL_BARE_REMOTE_NONAUTHORIZING` additionally resolves the local
bare remote directly and verifies its `refs/heads/main`. This proves the Git
semantics without network access, but it cannot attest the real GitHub remote.
The returned semantic attestation always has:

```text
executable_anchor_minted = false
target_execution_allowed = false
registered_observer_calls = 0
```

Attack tests reject detached HEAD, recipe/manifest dirty-worktree
substitution, wrong remote, local-only commits, stale remote heads, recipe
semantic mutations with recomputed IDs, recipe/manifest binding substitution,
later commits whose parent contains an anchored ID, and remove/re-add histories
for both recipe and final preregistration.

## Current lock

The first chain was anchored at commit
`b711cc52001419cfb0962e2a94af91cc03c5ffc2`, and its authority-only replay
passed with zero source reconstruction and target access. Attempt 1 later
failed closed at the first K7 matched-direct 2,048 checkpoint because the
independent row-work verifier omitted the registered
`MATCHED_DIRECT_CHECKPOINT` enum case. No campaign result or endpoint was
written. The tracked historical record is
`specs/V072_ANCHORED_ATTEMPT_1_FAILURE.json`.

Ledger amendment 1.34.7 permitted exactly one exhaustive-enum and durable-
journal repair.  That replacement was anchored at commit
`63cc0f5f78f64b7845319d1c1a5856212e3b8097` with:

```text
replacement_source_reconstruction_recipe_id = 7f6cebc1edf2bf007ae63a165866b8a3e6c6c4cb47b23a120eb1fa874be1e1d1
replacement_final_manifest_id = 2af044753017e6aeb1295408db23a2f8e923fbd7acdd207029e21371e7f09865
replacement_final_preregistration_id = 966c6631db568851829dfec0079b73920f0a980f8583d65d9eb6c14e23278e26
replacement_remote_main_anchor_id = 1c123268407d609ea853452c0145d21153e87251dfe8de61802264ccd6203474
replacement_campaign_result_id = null
SAMPLE_EFFICIENCY_GATE_NOT_RUN
```

Attempt 2 durably completed four occurrences and failed during the fifth
occurrence's exact lift.  It closed
`ATTEMPT_CLOSURE_NONCERTIFICATE.PROTOCOL_FAILURE`; no campaign result or
endpoint was written.  Its canonical record is
`specs/V072_ANCHORED_ATTEMPT_2_FAILURE.json`, ID
`cfcc4173e05f7e1ae0354849c40ae72aef5b80ca1dbd747de185e5e1dabdb64e`.

No V0-072 target law, seed, draw schedule, stopping rule or endpoint changed.
There is no remaining V0-072 retry.  The exact-lift repair and lossless
parallel/source-archive construction have a new proposed contract in
`specs/PARTIAL_SUPPORT_TOTAL_LIFT_AND_PARALLEL_EXECUTION.md`; any scientific
rerun requires a separate preregistration, manifest and anchor plus fresh
target identities/tapes and genuinely fresh held-out occurrences.
