# V323：冻结 WIN-only 在新执行流上有收益，B 保留未解决

唯一主终点 WIN_ONLY−FIRST_LOCAL 为 **+0.276123，95% CI [+0.015834, +0.539142]**，支持整局执行收益；11/16 生命周期正、5 个负，四父组均值三个正、一个负。独立核验 PASS。候选保留实际 FIRST 奖励，直接恢复已保存 QUERY WIN 参数，全程没有重新拟合或挑选参数。

| 最终 utility 对比 | 均值 | 95% CI | 结论 |
|---|---:|---:|---|
| WIN_ONLY−FIRST，唯一 A/B 等权主终点 | +0.276123 | [+0.015834, +0.539142] | 支持收益 |
| A：WIN_ONLY−FIRST，nominal secondary | +0.596922 | [+0.223727, +1.007534] | 保留条件通过 |
| B：WIN_ONLY−FIRST，nominal secondary | −0.044676 | [−0.399903, +0.280746] | 保留未解决 |
| WIN_ONLY−SOURCE，nominal secondary | +1.451618 | [+1.241962, +1.684952] | 支持收益 |
| FIRST−SOURCE，nominal secondary | +1.175495 | [+0.823615, +1.533551] | 支持收益 |

`primary_execution_gain_supported=true`，但 **`retained_execution_gain_supported=false`**。开发阶段的 +0.524492 收益在本轮减为 +0.276123；新执行流支持有限收益，完整能力保留目标尚未达成。

SOURCE/FIRST/WIN_ONLY 三臂均使用全新配对流，各生命周期/任务/臂固定 64 局；**6144 局**全部自然终局，零 CUTOFF、零旧游戏复用。新增评估 raw **5,030,852**；零新训练 raw、零拟合、零新参数文件。62 个不同有限案例通过。核验读取实际 FIRST 和候选版本，检查完整奖励参数保持一致、全部自然游戏 summaries/物理端点/种子/计数、配对效应及成本；实验与核验均 exit 0、stderr 0 字节。

完整实验进程树 CPU **175.926025 秒**、单调墙钟 **48.906546 秒**；组件小计 174.471922 秒，最终序列化/退出另 1.454103 秒。成功 SOURCE/V317/V319/V321/V322 引用一次后经济 CPU **4,442.420631 秒**。V320 诊断 425.578459 秒单列；本轮核验 CPU **9.277560 秒**、墙钟 **1.925113 秒**另计。

## 范围与下一主线

结果条件于既有 16 个学习历史和四个固定来源，仅执行流独立；没有建立独立学习复现、一般战略学习或采样效率。secondary 区间为 nominal。接口只保存游戏 summaries，核验未重放自然游戏逐动作决策或 bootstrap。历史动力学及失败尝试成本未知；U005 FAIL 保留，U006 未运行。

全新目标学习队列的同预算 QUERY-WIN/FACTUAL-WIN 对照已在 [V324](WIN_LEARNING_V324_RESULTS.md) 完成：主终点 +0.108914，CI [−0.116499, +0.325697]，增量学习收益及 A/B 保留未确认。V323 原有 B 保留结论保留，本轮配额、候选和阈值未改变。

证据：[协议](../specs/WIN_CONFIRMATION_V323.md)、[配置](win_confirmation_v323/configuration.json)、[结果](publication/v327_snapshot/win_confirmation_v323/summary.json.gz)、[核验](win_confirmation_v323/audit.json)、[完整成本](win_confirmation_v323/audit_costs.json)、[有限测试记录](win_confirmation_v323/test_logs/finite_tests_receipt.json)。
