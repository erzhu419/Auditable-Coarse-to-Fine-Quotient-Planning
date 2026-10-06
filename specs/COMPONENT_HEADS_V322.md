# V322：保存参数的奖励/WIN 组件交叉

冻结日期：2026-10-06。V321 四步奖励目标未证实修复 QUERY 退化；本轮隔离奖励与 WIN 参数更新的行为作用。复用核验 PASS 的全部 16 个生命周期/四父来源、实际 A/B FIRST v0、NSTEP_QUERY v1/v2、库信念和最终配对评估。

| 单元 | 奖励参数 | WIN logit 参数 | 评估 |
|---|---|---|---|
| FIRST_LOCAL | FIRST | FIRST | 复用 V321 |
| NSTEP_QUERY | 最终 NSTEP_QUERY | 最终 NSTEP_QUERY | 复用 V321 |
| REWARD_ONLY | 最终 NSTEP_QUERY | FIRST | 新增 |
| WIN_ONLY | FIRST | 最终 NSTEP_QUERY | 新增 |

先从 SOURCE/default 恢复实际 FIRST，再按 FIRST→NSTEP_QUERY v1→v2 的绝对稀疏写入恢复完整最终双头，不能把 v2 当全表。混合头复制所选的完整组件，另一组件精确保留 FIRST。保存相对 FIRST 的单组件稀疏版本，完整张量与来源组件精确一致且只读。参数更新计数仍为 FIRST 的已继承计数，本轮没有拟合；混合版本是诊断组装，不表示一次新学习更新。最终 NSTEP_QUERY WIN 参数与 OLD_QUERY 的一致性直接复用 V321 结论。

仅新增两臂，各 16×A/B×32 场，共 **2048 个自然游戏**。使用 V321 的相同种子 `321900000000+life*1000000+task_index*100000+episode`，不可变库信念，true p_four A=.1/B=.5，H2 原 tie 顺序和 max_steps8192。每个自然动作均产生新 spawn，含 WIN 动作，初始两 tile 也计费；新 raw 硬上限 **16,781,312**。旧 FIRST/BOTH 的 2048 局完整 receipt 原样引用，不再执行。

唯一主终点 **REWARD_ONLY−NSTEP_QUERY** 的 A/B 等权 utility，检验固定更新奖励时恢复 FIRST WIN 的作用。utility=score/2048+8*WIN−4。16 个生命周期在四个固定父组内配对 bootstrap 20,000 次，seed32200001，所有对比共用抽样。CI 下界>0 支持收益、上界<0 支持损失，其余未解决。

纯奖励 REWARD_ONLY−FIRST、纯 WIN WIN_ONLY−FIRST、更新 WIN 下的奖励作用 NSTEP_QUERY−WIN_ONLY、BOTH−FIRST 和交互 BOTH−REWARD_ONLY−WIN_ONLY+FIRST，以及 A/B 各任务为 nominal secondary。恢复性增长须主终点支持收益、REWARD_ONLY−FIRST 支持收益且 A/B 各自该对比 CI 下界>=0。任何新或引用游戏 CUTOFF 全队列 HOLD，保留全部端点、停止终局效益推断，不替换种子。实验设计和参数不据结果改变。

独立核验实际 FIRST/最终版本链、混合完整张量和单组件增量、未变的旧评估、所有新游戏 summaries/物理终局/种子/score/计数、配对统计与成本。沿用已检验的 evaluate_split；不重新执行游戏、训练或 bootstrap，也不声称拥有该接口未保存的逐动作自然游戏 tapes/决策探针。

所有输出在 reports/component_heads_v322。计入读取/恢复、复制/保存、评估、编译、协调及最终序列化/退出的完整进程树 CPU；成功 SOURCE/V317/V319/V321 成本引用一次，V320 诊断与核验另计。零新训练 raw、零新参数拟合、零来源/初始适配重跑。历史动力学及失败尝试成本未知。

这是固定队列、固定流的策略组件机制诊断；不能充作独立确认、WIN 校准/表示错误的完整因果解释、普通在线采样效率或一般战略学习成功。U005 FAIL 保留，U006 未运行。
