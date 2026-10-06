# V197 — frozen continuation-model replication

One independent 4×24-start cohort reuses every V196 model and library. All decisions precede exact H3 labels; SOURCE results and costs are inherited. No training, configuration selection or SOURCE evaluation occurs.

| Comparator | PROGRAM delta, V196 | PROGRAM delta, V197 | V197 positive replicas /4 |
|---|---:|---:|---:|
| TERMINAL | +0.169057 | +0.121169 | 4 |
| PROGRAM_NEIGHBOR | -0.019882 | -0.035439 | 0 |
| TREE32 | +0.177590 | +0.100512 | 4 |
| CONDITIONAL | +0.009501 | +0.050523 | 2 |
| LINEAR | +0.036687 | +0.024430 | 2 |
| NONLINEAR | +0.070715 | +0.006625 | 1 |
| OLD_SHARED | +0.053673 | +0.024547 | 2 |

The continuation-information benefit repeats against TERMINAL and TREE32 in all eight replicas across both cohorts. Stable superiority over the stronger old baselines remains unestablished. PROGRAM again trails the same-input neighbor: utilities 1.013763 versus 1.049202, with 43 versus 36 regret roots. Its neighbor-relative Δ(R,F,S)=(-0.014400,+0.021039,0); this cohort's deficit is reward/risk, with no nonzero success differences in either method's positive-regret roots.

The largest neighbor-relative loss, v197_target_r03_21, chooses LEFT with true failure probability 1; RIGHT has failure probability 0 and utility higher by 1.031836. PROGRAM maps both directions to leaf15 and estimates raw/projected difference zero. Input validity and twelve word-score distinctions already differ. That leaf mixes 88 positive, 84 negative and 587 zero SOURCE failure differences, including 73 reverse pairs with nonzero differences. [Retained diagnosis](v197_runtime_tmp/retained_case_diagnostic.json) locates a partition loss without new fits or labels.

Ten focused tests pass first attempt. Audit 225/225, source 95/95 and inputs 14/14 pass; main/audit once 54.68/17.02s, stderr 0. New work: 96 exact kernels/plans/labels and 4672 virtual continuation swipes. New fits, SOURCE operations, library preparations, physical samples and parameter solves are zero; inherited costs remain referenced. This replication is closed.

## Limits and next step

Zero eligible success errors does not establish a learned general success mechanism. Short no-spawn words are not sufficient risk certificates; one replay does not explain every error. General strategy and sampling-efficiency claims remain open. Keep H2, U005 FAIL and U006 unstarted.

Next retain the representation and complete R/F/S outputs, and induce SOURCE partitions by the actual R-F+S action utility after bidirectional prediction and projection. SOURCE holdouts select configurations; a fresh cohort tests the resulting learner. Specify any short split lookahead and charge its computation before that experiment.
