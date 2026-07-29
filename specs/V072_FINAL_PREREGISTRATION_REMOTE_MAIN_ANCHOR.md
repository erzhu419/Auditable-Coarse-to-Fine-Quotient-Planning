# V0-072 Final Preregistration and Remote-Main Anchor

Status: implemented schema and nonauthorizing semantic verifier; registered
execution remains locked.

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

The fixed production source recipe is not yet present at its tracked path and
has not been replayed into the exact source/archive/component identity graph.
The execution manifest therefore cannot be finalized, the final
preregistration factory fails closed, and the remote-main anchor authority
cannot construct.

Current registered outcome:

```text
source_reconstruction_recipe_id = null
final_manifest_id = null
final_preregistration_id = null
remote_main_anchor_id = null
target_execution_allowed = false
registered_observer_calls = 0
```

No V0-072 target law, seed, draw schedule or stopping rule is changed by this
slice.
