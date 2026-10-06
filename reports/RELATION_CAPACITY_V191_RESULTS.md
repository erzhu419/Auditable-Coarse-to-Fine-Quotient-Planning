# V191 — Linear capacity of the shared relation score

**The 98-feature linear scorer cannot express all SOURCE rankings.** Exact
certificates cover every tied-optimum branch; changing the loss or penalty
within `first_reward + beta·phi98` cannot make all these rankings correct.

| Scope | Roots | Certified result | Margin |
|---|---:|---|---:|
| SOURCE | 143 | Weak rankings infeasible | Upper bound ≈ −0.000451274 |
| TARGET | 96 | Strict witness, exact and float replay pass | Verified gap ≥ 0.693209 |
| JOINT | 239 | Weak rankings infeasible | Upper bound ≈ −0.062751736 |

All actual floating feature coordinates are preserved as binary rationals;
negative bounds have exact nonnegative 99-coordinate dual balances. SOURCE
uses 39 search nodes, TARGET 8, JOINT 1. TARGET's witness reproduces all 96
optimal choices; its largest coefficient is about 2,136.

The retained SOURCE-trained RELATION model already has **72/143 regret roots**,
mean regret **0.109982** and utility **1.227151** versus oracle **1.337133**.
Its TARGET has 37/96 regret roots. The error begins on SOURCE; a structural
linear expressivity limit is now established alongside fitting errors.

**Next:** change the consequence model to shared nonlinear relation
combinations. Keep SOURCE143 and the current inputs fixed initially, select
only by held-out SOURCE groups, then freeze and evaluate unopened targets.
Do not adopt the target-labelled capacity witness or retune the same linear class.

**Verification:** 17 synthetic tests pass; **576/576 audit, 83/83 source and
8/8 input** comparisons pass. Main/audit once, **561.66/28.39 s**, stderr 0.
There are **48 LPs, 47 symbolic balances**, one verified cap certificate;
audit repeats no solves. Zero new fits, labels, kernels or physical samples.

**Limitations:** Retained finite H3 roots and a fixed continuation teacher.
The negative result does not quantify minimum mean regret or make all 72
errors unavoidable. Positive TARGET capacity is existence, not SOURCE
learnability or transfer. Nonlinear capacity remains unestablished.
General strategy remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/RELATION_CAPACITY_V191.md) · [Summary](controlled_predictive_relation_capacity_v191/summary.json) · [Exact certificates and witness](controlled_predictive_relation_capacity_v191/capacities.json) · [SOURCE diagnostics](controlled_predictive_relation_capacity_v191/learned_source_diagnostics.json) · [Audit](controlled_predictive_relation_capacity_v191/analysis.json) · [Ledger](v191_runtime_tmp/stage_checks.json)
