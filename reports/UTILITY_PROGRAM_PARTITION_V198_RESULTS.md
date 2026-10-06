# V198 — actual-utility partition induction

The new UTILITY tree scores each split by the actual SOURCE action's R−F+S after bidirectional prediction and projection. SOURCE143/36, continuation inputs, outputs, grid and controls stay fixed; decisions precede fresh TARGET96 H3 labels. **The new learner is not adopted.**

SOURCE selects depth4/min4; heldout utility falls0.012420 against PROGRAM. TARGET utility0.955127 trails PROGRAM0.964842, with48 versus45 regret roots.

| Comparator | UTILITY delta | Positive replicas /4 |
|---|---:|---:|
| PROGRAM | −0.009715 | 0 |
| PROGRAM_NEIGHBOR | +0.004980 | 2 |
| TERMINAL | +0.143843 | 4 |
| TREE32 | +0.151523 | 4 |
| LINEAR | +0.050370 | 3 |
| NONLINEAR | +0.012819 | 2 |
| OLD_SHARED | +0.065236 | 3 |

Against PROGRAM,14 new errors exceed11 resolved errors; gains total0.673086, losses1.605714. Both eligible nonzero-success errors have the wrong estimated direction. 

[Retained SOURCE structure](v198_runtime_tmp/source_structure_diagnostic.json) shows10 splits/11 leaves. Training utility1.311703314801036 matches the actual decoder's equal-group utility to2.22e−16. Increasing depth to6 adds splits but lowers CV to1.234069: this is not evidence of a strict greedy plateau. Nineteen of51 SOURCE errors merge both directions, all at depth-limit leaves. [Two retained TARGET losses](v198_runtime_tmp/retained_case_diagnostic.json) show overestimated continuation offsets overriding immediate reward and a reversed success difference despite observable goal/dependency distinctions. 

Nineteen focused tests pass first attempt. Independent audit232/232, frozen source98/98 and inputs16/16 pass; main/audit once77.09/45.29s, stderr0. New work:17 training plus17 audit trees,96 exact labels and4696 TARGET virtual swipes. SOURCE traces/libraries are reused; inherited costs remain referenced.

## Limits and next step

Direct utility optimization alone has not improved transfer. General strategic learning and sampling efficiency remain unresolved; retain H2, U005 FAIL and U006 unstarted. Next learn one region for each unordered action pair, with opposite leaf vectors for its two directions during induction. Keep complete R/F/S and SOURCE holdouts. Its transfer benefit remains a new hypothesis; more depth or sampling is not justified by this result.
