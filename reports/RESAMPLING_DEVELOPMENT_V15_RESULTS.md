# V15 结果与下一步

48 个组合全部完成，30 项测试通过；旧基线精确复现，三个历史产物重放一致。三种在线方法的完整策略最优数仍均为 453/480。

| 方法 | 相对 BASE 改善／退化 | 期望实际样本 | 独立／十查询分摊成本 ms |
|---|---:|---:|---:|
| V14 不重采 | — | 7,837.95 | 36.18／12.63 |
| 均衡重采 | 13／2 | 25,166.61 | 136.85／113.14 |
| 定向重采 | 10／8 | 25,166.61 | 132.58／108.87 |

两重采方案的 480 对期望／最大批数精确相同；定向相对均衡为 8 改善、15 退化。质量变化仅在 crossing3，旧八项误差未全部修复，相对全行基线退化数为 8／10／14。

**保留 V14。下一步检验按竞争动作价值差距触发、并能提前停止的补采，固定实际样本上限与完整费用。** 评分局部更新另测，不与停止规则同时更改。

本轮仍为已暴露开发证据，评分不提供统计置信保证。U005 FAIL、U006 未启动保持。

[冻结协议](../specs/CONTROLLED_PREDICTIVE_RESAMPLING_V15.md) · [质量明细](controlled_predictive_quality_analysis_v15.json) · [成本明细](controlled_predictive_cost_analysis_v15.json) · [完整结果](controlled_predictive_resampling_v15.json.gz) · [历史重放](controlled_predictive_history_replay_check_v15.json)
