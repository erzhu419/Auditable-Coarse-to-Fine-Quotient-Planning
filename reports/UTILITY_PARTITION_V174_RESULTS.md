# V174 — SOURCE-heldout utility partitions

The V173 follow-up is implemented and completed. Scientific progression is **FAIL (0/2)**: both generators retain **zero splits** and collapse to ONE_LATE. Keep H2; U005 FAIL, U006 unstarted.

| Fresh first-action contrast, risk1 | Utility difference | SOURCE-cluster conditional 95% CI |
| --- | ---: | --- |
| UTILITY_CONFIRMED − SSE_CONFIRMED (primary) | 0.00000 | [0.00000, 0.00000] |
| UTILITY_CONFIRMED − H2 (progression) | +0.01219 | [−0.09450, +0.11889] |
| UTILITY_UNPRUNED − SSE_UNPRUNED | −0.06687 | [−0.16801, +0.03426] |
| UTILITY_CONFIRMED − UTILITY_UNPRUNED | +0.10160 | [+0.00736, +0.19585] |

On the same 384 TRAIN roots / 5,580 outcomes, candidate generation now scores actual SOURCE-heldout action utility, preserving full outcome vectors and exact first reward. The search examines 1,920 predicates, finds 326 comparable candidates and selects eight splits, giving 3/4/3/2 leaves. SSE proposes 32 splits. Both share fresh confirmation and global K=40; all eight utility nodes are eligible, but none confirm positive utility. This tests the complete crossfit mechanism, including its stricter support constraints.

The complete utility trees have positive retrospective TRAIN effects against root-collapsed/ONE: [+0.06041, +0.21115, +0.14916, +0.14116], with all 384 roots supported. On 256 unseen VALID boards, all 1,536 choices freeze before labels and every learned arm has zero fallback. Removing the utility splits significantly improves fresh utility. The current bottleneck is therefore independent usefulness; changing the proposal mechanism has not solved it.

## Accounting and verification

CONFIRM_SOURCE: 32 games / 31,520 transitions; CONFIRM: 3,660 / 1,821,558. VALID_SOURCE: 32 / 31,332; VALID: 3,708 / 1,860,304. Total: **7,432 terminal physical games / 3,744,714 new transitions / 7,489,684 RNG draws**. Twelve discovery models fit once; eight confirmed models reuse coefficients. The 1,974 crossfit leaf fits are separately charged. Inherited costs remain referenced.

**24 distinct pure tests**, **537/537 independent checks** and **98/98 frozen-source comparisons** pass. Main/audit each run once, 303.81 s / 174.64 s, both exit 0 and stderr 0. Two retained training diagnoses compute 1,536 retrospective choices; exact costs are recorded. No diagnostic fitting, new sampling, interval recomputation, neural updates or server downloads.

Evidence: [protocol](../specs/UTILITY_PARTITION_V174.md), [summary](controlled_predictive_utility_partition_v174/summary.json), [audit](controlled_predictive_utility_partition_v174/analysis.json), [confirmation](controlled_predictive_utility_partition_v174/pruning_records.json), [stage ledger](v174_runtime_tmp/stage_checks.json), [training diagnosis](v174_runtime_tmp/discovery_diagnosis.json).

## Next step and limitations

Freeze the boards and complete tree/ONE policies; evaluate their changed actions with new paired suffixes on training and fresh boards. Freeze roster, budget and statistical questions first. This will test label sensitivity versus failure to generalize state distinctions; do not retune this run's objective or acceptance rule.

Intervals condition on four teachers. Confirmation bounds select models, rather than certify whole trees. Current data do not separate suffix noise, selection optimism and board-level generalization. General strategic learning and autonomous whole-game improvement remain unresolved.
