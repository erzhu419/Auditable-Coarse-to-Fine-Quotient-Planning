# Auditable Coarse-to-Fine Quotient Planning

This repository turns the Laplace-semi-MDP follow-on discussion into a finite,
auditable quotient-planning prototype.  V0 deliberately targets finite-state,
finite-horizon, fully observable symbolic kernels.  Its reusable artifact is a
nominal abstract planning model plus an independently computed exact sound
envelope; a policy graph belongs to a query, not to the reusable model.

Phase 0.5 builds are explicitly coverage-limited. `rho0` belongs to `QuerySpec`; the
builder closes its declared positive-mass support under every legal action and outcome,
records the coverage mode/support hash/state count in `build_id`, and forbids RAPM or
certificate reuse outside that closure. This is an auditable scoped-build contract, not
a claim of unrestricted reuse across arbitrary initial distributions.

The construction order is:

```text
authoritative benchmark kernel
→ exact reachable enumeration and constrained J0 oracle
→ deliberately coarse hard partition
→ nominal quotient proposal + exact sound audit
→ deterministic counterexample-guided split
→ certified lifted plan or charged constrained ground fallback
```

The root `DECISION_LEDGER.md` and the nine files in `specs/` are the published
normative contract. The local `markdown/` discussion history and `reference/`
literature/repository archive are provenance inputs, are intentionally ignored by Git,
and are not part of the public checkout.

## Quick start

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest
acfqp-phase05 --output artifacts/phase05
python3 scripts/verify_phase05.py artifacts/phase05
acfqp-exact-d4 --output artifacts/exact_d4
python3 scripts/verify_d4_baseline.py artifacts/exact_d4
acfqp-aliased-cegar --output artifacts/aliased_cegar
python3 scripts/verify_aliased_cegar.py artifacts/aliased_cegar
python3 third_party/laplace_smdp_940598d/experiments/run_gridworld_bellman_kron.py \
  --out-dir artifacts/legacy_gate_actual
python3 scripts/check_legacy_gate.py --actual-dir artifacts/legacy_gate_actual
```

On a development machine where the ignored `markdown/` and complete `reference/`
corpus have been restored, `python3 scripts/build_reference_manifest.py` rebuilds the
optional local provenance manifests. The artifact runners bind both manifests when
both exist; a public checkout with neither manifest records an empty mapping. A
half-present manifest pair is rejected.

The Phase 0.5 command writes complete JSON artifacts and a SHA-256 manifest for
both tiny benchmark fixtures.  Fallback is an explicit algorithmic outcome and
is charged in the artifact rather than hidden.

The exact-`D4` command writes the separate safe-chain positive-control bundle.
Its verifier reconstructs the registered group profile, orbit/action quotient,
distinct-action concretizers, zero-width model, lifted policy, and J0 equality;
that profile contains no CEGAR split or fallback artifact.

Ledger `V0-026` additionally freezes a separate safe-chain aliased CEGAR profile.
It keeps the same ground structural key and query, but uses a ten-cell histogram base
partition, order-dependent `canonical:first/last` actions, and a preregistered six-atom
action-frame geometry grammar. Exact counterexamples and the standard candidate ranking
must select two local four-bit splits before the run certifies with no fallback. This is
a deliberate action/partition-aliasing positive control; it is not the exact-`D4`
baseline and is not evidence of automatic predicate or symmetry discovery. Its runner
and independent verifier use their own profile key and multi-iteration artifact bundle;
the two commands shown above generate and independently recompute that bundle.

## Scope

Phase 0.5 contains no neural encoder, learned model, MCTS, option, first-hit
reduction, POMDP adapter, or vision component.  Those remain gated extensions.
The inherited Laplace snapshot in `third_party/` is isolated and checked by the
legacy gate; it is not silently imported as if its spatial abstraction were a
semantic quotient proof.

Construction established that the original tiny G2048 query is ground-infeasible
at every registered positive risk threshold. It is retained as the explicit
soundness/fallback regression, while a separately keyed safe-chain fixture provides
the feasible positive-test route. The resulting decisions and exact regression values
are published normatively as ledger entries `V0-019` through `V0-024`; the ignored
discussion files are historical provenance, not required public documentation. The
`V0-024` baseline performs no CEGAR split and is not evidence of automatic symmetry or
predicate discovery.

The query-owned initial-support implementation and coverage-specific build identity are
frozen by ledger `V0-025`; resolved `V0-RISK-003` is no longer an open construction
blocker. The executable aliased refinement contract and its narrow claim boundary are
frozen separately by ledger `V0-026`.
