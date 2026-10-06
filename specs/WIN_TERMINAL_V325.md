# V325：固定 V324 快照的 WIN 终局校准与更新误差

冻结日期：2026-10-06。V324 新学习历史未确认额外收益，约 99% 一步 WIN 标签仍来自 FIRST 的 bootstrap。本轮固定 V324 全部 16 生命周期、四来源、A/B、两轮及两个学习臂，补充真实终局信息。零拟合、零新参数版本、零来源或首次适配重跑。U005 FAIL 保留，U006 不运行。

## 固定样本与终局策略

每个任务/轮次/臂从原 16,384 根组中等距取 **64 组**，位置为 `np.linspace(0,16383,64,dtype=int64)`，保留四个已采成员，合计 **32,768 条续跑**。不得依预测或既有收益筛选。两臂共用位置及新后缀 seed，不把原首个 spawn 再计为新采样。

实际恢复 SOURCE→V324 FIRST v0；复现成员的原首个 cell/rank 和保存 DIRECT 分支，然后由不可变 FIRST H2 在真实世界续跑至自然 WIN/LOST。A=.1、B=.5，模型概率为原 FIRST FIT 库信念；max_steps8192 包含 DIRECT 动作。每个新执行动作后 spawn 均计费，包括 WIN 动作。原首个 spawn 后已经 LOST 的成员直接自然结束。任何 CUTOFF 全队列 HOLD，保存轨迹和端点、终局标签为 null，不执行 bootstrap，不替换种子或扩配额。

后缀 seed=`325500000000+life*10000000+task_index*1000000+round*100000+original_group*4+member`。所有输出位于 reports/win_terminal_v325，配置先于新续跑写入。

## 同一终局标签下的两个问题

成员教师标签是原 DIRECT 所选后继 afterstate 上的 FIRST WIN 预测；对照实际终局 Y，报告其 signed bias 与 Brier。根预测是产生首个 spawn 前的完整 root afterstate 上的概率；两类条件不同，不能以教师和根的原始 Brier 差直接判断谁更优。

每臂在自身根上读取实际 FIRST、轮前 before、轮后 after 和最终 FINAL 参数：R1 before=v0/after=v1；R2 before=v1/after=v2；FINAL 均为自身 v2。私有版本按实际链恢复，奖励完整保留 FIRST。每单元只计算 FIRST/v1/v2 三个不同快照，别名不再重复计算。概率沿用原生双头预测器，实际奖励/WIN 表读取都计入成本。

唯一主终点：**查询根上 FINAL_QUERY_WIN−FIRST 的 Brier 变化**，负值更好。对 A/B、两轮、根组、成员和生命周期等权，四固定父组内配对 bootstrap 20,000 次、seed32500001，各对比共用抽样。CI 上界<0 支持预测改善；下界>0 支持预测退化；其余未解决。两分布及任务/轮次的教师 bias、根概率与 bias、before→after、FIRST→FINAL 变化为 nominal secondary，不替换主终点。

## 核验、成本与范围

独立 reader 检查实际 V324 版本和源组、所有新动作/score/spawn/RNG/端点、预定 FIRST H2 首末探针、完整根概率及参数只读、所有成员与配对误差统计及成本。引用 V324 PASS，不重跑旧完整核验、训练、整局评估或 bootstrap。保留全部续跑轨迹；H2 策略只按预定探针核对，不重新执行所有规划决策。

新后缀 raw、读取/恢复、预测、续跑、轨迹保存、编译、协调和最终序列化/退出均计费。成功 SOURCE/V324 成本继承一次，独立审计单列；历史动力学和失败尝试 CPU 未知。

这是曾进入训练的固定根上的新后缀诊断，真实标签对应 prescribed DIRECT→FIRST H2，不对应更新后策略的整局价值。它可区分目标校准与同一标签上的更新预测误差，但单独不能证明 V324 未确认收益的因果机制、学习增益或一般战略优势。不得依据本轮结果修改配额、参数、主终点、停止规则或区间。
