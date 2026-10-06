# V190 — Shared merge/blocker relations

The fixed **98-column** rank/order/packing representation removes all **20**
known within-root alias losses on development TARGET96; mean information-loss
floor drops **0.022345 → 0**. All five old certificate vertices split at their
actual edge endpoints. SOURCE143/36 selects **lambda=0.1**, held-out utility
**1.219298**, design rank **83**.

On **96 unopened H3 boards**, the new learner is **not adopted**:

| Model | Utility | Positive-regret roots |
|---|---:|---:|
| RELATION | 1.085638 | 37 |
| LINEAR | 1.098796 | 27 |
| OLD_SHARED | 1.101454 | 24 |
| RIDGE | 1.081602 | 40 |
| ORACLE | 1.145628 | 0 |

RELATION-minus-LINEAR is **−0.013157**, negative in **all four replicas**;
6 roots improve, 15 worsen, with 13 new errors and 3 resolved. Minus-OLD_SHARED
is **−0.015815**, also negative throughout. The **+0.004036** against RIDGE
has two positive and two negative replicas. Source validation also trails
the retained six-column LINEAR result, 1.233063.

**Next:** test linear ranking capacity on retained SOURCE and TARGET vectors.
If SOURCE rankings are unrepresentable, change the consequence model's
function class; otherwise locate which fitting/regularization decisions lose
representable rankings. No new labels are needed for that diagnosis.

**Verification:** 20 initial tests and one metadata regression pass. Main/audit
run once, **35.16/6.35 s**, stderr 0; **13 predictors, 96 kernels/plans**, zero
physical samples/native updates. Original **220/222** audit and **85/85 source,
10/10 input** comparisons are retained. Two audit failures were solely the
auditor's TARGET/split metadata instead of main's V184 FRESH metadata.
A frozen **0.69 s** supplement rechecks only those bindings: corrected
**222/222**, no refitting or kernel integration. The pre-run tuple/list test
failure is also retained.

**Limitations:** Development separation does not establish linear capacity or
learnability. Evaluation is finite H3 under a fixed continuation teacher.
General strategic learning remains unresolved. Keep H2; U005 FAIL, U006 unstarted.

[Protocol](../specs/MERGE_RELATIONS_V190.md) · [Summary](controlled_predictive_merge_relations_v190/summary.json) · [Development](controlled_predictive_merge_relations_v190/development.json) · [Original audit](controlled_predictive_merge_relations_v190/analysis.json) · [Metadata amendment](controlled_predictive_merge_relations_v190/metadata_binding_amendment/result.json) · [Original ledger](v190_runtime_tmp/stage_checks.json)
