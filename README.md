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

The root `DECISION_LEDGER.md` and the nine files in `specs/` are normative.
The long conversations in `markdown/` are rationale and history.  The
`reference/` archive contains every external reference from those conversations,
with hashes and provenance-pinned shallow clones for repositories that could be
matched without guessing.

## Quick start

```bash
python3 -m pip install -e '.[test]'
python3 -m pytest
python3 scripts/build_reference_manifest.py
acfqp-phase05 --output artifacts/phase05
python3 scripts/verify_phase05.py artifacts/phase05
acfqp-exact-d4 --output artifacts/exact_d4
python3 scripts/verify_d4_baseline.py artifacts/exact_d4
python3 third_party/laplace_smdp_940598d/experiments/run_gridworld_bellman_kron.py \
  --out-dir artifacts/legacy_gate_actual
python3 scripts/check_legacy_gate.py --actual-dir artifacts/legacy_gate_actual
```

The Phase 0.5 command writes complete JSON artifacts and a SHA-256 manifest for
both tiny benchmark fixtures.  Fallback is an explicit algorithmic outcome and
is charged in the artifact rather than hidden.

The exact-`D4` command writes the separate safe-chain positive-control bundle.
Its verifier reconstructs the registered group profile, orbit/action quotient,
distinct-action concretizers, zero-width model, lifted policy, and J0 equality;
that profile contains no CEGAR split or fallback artifact.

## Scope

Phase 0.5 contains no neural encoder, learned model, MCTS, option, first-hit
reduction, POMDP adapter, or vision component.  Those remain gated extensions.
The inherited Laplace snapshot in `third_party/` is isolated and checked by the
legacy gate; it is not silently imported as if its spatial abstraction were a
semantic quotient proof.

Construction established that the original tiny G2048 query is ground-infeasible
at every registered positive risk threshold.  It is retained as the explicit
soundness/fallback regression, while a separately keyed safe-chain fixture now
provides the feasible positive-test route.  The answered decisions and exact
regression values are recorded in
[`markdown/GPT_followup_questions.md`](markdown/GPT_followup_questions.md) and
normatively frozen as `V0-019` through `V0-023` in `DECISION_LEDGER.md`. Its abstract
positive-control profile is separately frozen as an exact known-symmetry `D4`
state/action quotient in
[`markdown/GPT_d4_quotient_decision.md`](markdown/GPT_d4_quotient_decision.md) and
ledger `V0-024`. That baseline performs no CEGAR split and is not evidence of automatic
symmetry or predicate discovery.

The query-owned initial-support implementation and coverage-specific build identity are
frozen by ledger `V0-025`; resolved `V0-RISK-003` is no longer an open construction
blocker.
