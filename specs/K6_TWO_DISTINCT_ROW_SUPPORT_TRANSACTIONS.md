# K6 Two-Distinct-Row Support Transactions

Status: normative V0-069 bounded-probe contract
Contract: `1.33.0`
Profile: `k6_two_distinct_row_support_transactions_v0`

## Purpose

V0-068 established one causally authorized support promotion, but the
registered K6 quotient remained uncertified at the 8,192-draw checkpoint.
V0-069 asks one narrower question: can a second, genuinely different local
support transaction close that proof frontier without advancing the global
acquisition checkpoint to 16,384?

This is a bounded diagnostic, not a general multi-transaction scheduler and
not a sample-efficiency claim.

## Frozen execution

The only legal execution is:

```text
K6 base closure at validation checkpoint 8,192
  -> V0-068 quotient audit
  -> V0-068 transaction 1 (fresh validation 2,048;
                           new-child validation 8,192)
  -> transaction-1 mixed-model failed audit
  -> freeze SecondSupportTransactionContextV1
  -> recompute selected-policy OTHER counterfactuals on that mixed model
  -> exclude transaction-1 binding and physical evidence
  -> authorize at most one individually causal, different epoch-1 row
  -> promote it with a fresh 2,048-observation validation stream
  -> acquire complete 8,192-observation rows for newly admitted H=1 states
  -> rebuild the quotient model
  -> robustly replan and audit
  -> stop
```

There is no global 16,384 checkpoint and no transaction 3.

## Identity and no-reuse rules

`SecondSupportTransactionContextV1` binds:

- base closure, bridge, audit, and threshold;
- transaction-1 authorization, replacement, consumer, closure, bridge,
  audit, and failed frontier;
- transaction-1 selected binding, promoted row, and physical evidence;
- transaction history and the finite cap profile.

Transaction-2 counterfactuals are newly computed on the transaction-1 mixed
model. Transaction-1 counterfactual artifacts are not reusable. The
transaction-1 binding, its promoted row, and its physical evidence are
ineligible for transaction 2 even if a cheap re-estimate would select them.

`DistinctRowExpansionAuthorizationV2` names exactly one different row. Its
parent must:

- occur on the current selected policy;
- have positive `OTHER` upper mass;
- still be at support epoch 1;
- contain proposal-only novel outcomes;
- make the failed audit certify when only that row's `OTHER` interval is
  changed to zero; and
- be distinct from transaction 1 by binding and physical evidence.

Candidates use the deterministic order:

```text
maximum remaining horizon, then minimum planner-row content ID
```

## Complete second closure

`SecondPromotedH2ClosureV1` must contain exactly two distinct epoch-2 row
bindings: the immutable transaction-1 promotion and the transaction-2
promotion. Every other retained row is byte-identical. Every newly named
nonterminal root outcome receives a complete public action catalogue and a
fresh epoch-1 row for every legal action.

No partial closure may be audited.

## Finite caps

The registered cap profile is:

| Quantity | Hard cap |
|---|---:|
| support transactions | 2 |
| transaction-2 counterfactual rows | 64 |
| transaction-2 row promotions | 1 |
| promoted validation draws | 2,048 |
| new-child validation draws per row | 8,192 |
| new child catalogues | 48 |
| new child action rows | 288 |
| transaction-2 incremental observer draws | 2,379,776 |
| maximum global checkpoint | 8,192 |

Cap exhaustion is a typed noncertificate outcome. It is not infeasibility and
does not authorize a third transaction.

## Terminal outcomes

- `CERTIFIED_AT_8192`
- `FAILED_NEW_FRONTIER`
- `NO_SOUND_DIFFERENT_ROW_COVER`
- `COUNTERFACTUAL_CAP_EXHAUSTED`
- `MATERIALIZATION_CAP_EXHAUSTED`
- `PROTOCOL_FAILURE`

All outcomes close the bounded probe. `FAILED_NEW_FRONTIER` preserves the new
frontier but does not authorize transaction 3.

## Statistical and exact-evaluation boundary

The operational construction remains observation-only:

```text
exact_iid_implementation_claimed = false
formal_exact_iid_plan_certificate = false
statistical_claim_scope =
  CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_NOT_PROVEN_BY_
  DETERMINISTIC_REPLAY_IMPLEMENTATION
```

Deterministic SplitMix64 replay demonstrates reproducibility, not formal IID.
Hidden exact support and exact probabilities are forbidden operationally.

If and only if the robust transaction-2 audit certifies, its operational
`run_id` is frozen before the existing exact-lift authority is invoked in the
standalone evaluation lane. The exact-lift artifact must bind that `run_id`
as its prerequisite operational freeze. Exact risk and regret may diagnose
the frozen policy but cannot repair the conditional operational certificate.

## Acceptance and attack tests

The implementation must show:

1. the base and both transactions remain at global checkpoint 8,192;
2. transaction-2 selection differs from transaction 1 by binding and
   physical evidence;
3. candidate evidence is bound to the transaction-1 mixed model/audit;
4. transaction-2 fresh validation observations are disjoint from all parent
   observations;
5. the final closure has exactly two distinct epoch-2 bindings and complete
   legal-action coverage;
6. all caps and incremental observation counters reconcile;
7. serial/parallel schedules have identical content identities;
8. stale transaction history, frontier, threshold, cap, or first-consumer
   identity fails closed;
9. injecting checkpoint 16,384 or authorizing transaction 3 fails closed;
10. exact evaluation is absent unless the robust audit certified first.

Items 2, 4, 5 and the materialized portion of item 6 are conditional
obligations for a result that actually reaches authorization and
materialization. The registered negative result does not claim those dormant
branches were exercised; it must instead prove zero transaction-2 observer
draws, exact calls, global-16,384 access and transaction-3 access.

## Claim boundary

A positive result would show only that two locally and causally selected
support expansions can certify this registered K6 H=2 occurrence before a
global 16,384 checkpoint. It would not prove:

- general hidden-coordinate invention;
- arbitrary-horizon partial-dynamics learning;
- IID correctness of the deterministic replay implementation;
- multi-domain transfer;
- total-work or sample advantage over direct planning;
- an economics Gate; or
- the overall research objective.

The official execution, scalar, break-even, workload-economics, and counter
completeness locks remain unchanged.

## Registered probe result

The first deterministic exact-arithmetic replay of the bounded profile found
49 eligible, newly
recomputed different-row counterfactuals on the transaction-1 mixed model.
This count is the filtered transaction-2 candidate set (selected-policy
`OTHER`-positive, epoch 1, novel, and not transaction 1), not the cardinality
of the unfiltered failed frontier. None made the failed audit certify when
its `OTHER` interval alone was fixed to zero:

```text
outcome = NO_SOUND_DIFFERENT_ROW_COVER
eligible_counterfactual_row_count = 49
causal_counterfactual_row_count = 0
transaction_2_incremental_observer_draws = 0
global_16384_checkpoint_accesses = 0
third_transaction_allowed = false
exact_failure_probability = null
exact_normalized_regret = null
```

The risk/regret fields are typed null because no transaction-2 policy
certified and therefore evaluation-only exact lift is unreachable; they are
not numerical zeroes. This negative result rules out the registered
one-more-individually-causal-row mechanism. It does not rule out a
preregistered joint multi-row causal cover, a different coordinate model, or
a later sample-tax operator.
