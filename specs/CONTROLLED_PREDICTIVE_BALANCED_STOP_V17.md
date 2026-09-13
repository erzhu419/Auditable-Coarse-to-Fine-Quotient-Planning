# V17：均衡分配上的停止机制

本协议在 V17 真实运行前固定。V16 停止对同分配继续采样保持 480 项完整策略后果同值，并减少部署期望样本，但差距分配对均衡为 6 改善、15 退化。本轮固定原均衡分配，单独测同一停止条件及其计算费用。

## 固定输入与方法

沿用 V16 冻结名册中的原 16 根、horizon、种子 832101–832103、十查询及顺序、原暴露标签，每方法 480 项。六方法为 full_state_empirical、exact_empirical_quotient、online_mass_bound（V14 原执行器）、online_balanced_resampling（V15 原执行器）、online_balanced_gap_continue、online_balanced_gap_stop。四 ONLINE 按 (根索引+种子索引+查询索引) mod 4 轮转，共 1920 棵历史树。没有新增来源训练或 Stage A128。

每根／种子重新付费构建一份 V14 MASS_BOUND、最多 32 行的十查询 warm。BASE 直接使用；一次 V15 整数计数转换供原 BALANCED，一次原 V16 GapPlannerState 转换供两种新方法。各方法承担全部 warm 与自己的转换费用，另列十查询分摊。物理账只计实际发生的两次转换。两个完整模型参考共享付费支持及全行采样，预算不同。

V15 样本批流保持：每批 256 次，批号从 0 开始，第 0 批复现 V14，后续采用原 seed+1000000*batch_index 行种子。每条 ONLINE 路径上限 128 批，即 32768 实际样本，包含 warm、首次与重采；每个实际 ACTIVE 决策固定配额 floor((128−spent_batches)/h)。停止可少用样本，不强制实际消耗相等。

## 唯一行为差异

两个新方法每批前调用未经修改的 V16 assess_gap，包含原完整重算和候选诊断。经验 incumbent、Qminus/Qplus、物理跨度除以 sqrt(N)、挑战者及字母序平局规则全部不变。仅一个动作，或 incumbent Qminus >= challenger Qplus，给出启发式分离。

STOP 在分离时结束当前决策获取，再执行原经验最大下界动作；下一实际孩子重新判断。CONTINUE 记录同样诊断而忽略分离。未停止时，两组均严格使用 V15 BALANCED 的顺序：原 select_row 结构前沿优先；无结果才 select_resample(mode="BALANCED")。不使用 assess_gap 返回的候选来选择样本。评分全量重算，局部更新优化留待独立实验。

全部配额、批号、整数累计、经验模型更新、最终执行规则、实际观察和兄弟历史分离沿用原实现。终态、配额耗尽、总上限耗尽、无均衡候选与启发式分离分别记录。评分、结构／均衡选择、获取、更新和 query clone 全部收费。

## 配对、验证与成本

主比较 STOP vs CONTINUE 隔离停止效果；CONTINUE vs 原 BALANCED 隔离额外评分成本；另列 STOP vs 原 BALANCED、STOP vs BASE。报告每项完整策略 reward/failure/success/value、首动作及完整策略最优、所有退化、旧八项和旧五项见证，按根／family／split 汇总。相同最优总数不能替代逐项后果比较。

先固定所有当轮历史，再计算真最优标签及读取旧结果。当前 CONTINUE 必须与原 BALANCED 的 trace（仅忽略新增 gap_assessments 和 decision_kind）及 root_metrics 精确一致。V14 的 48 个 warm 前缀／480 棵 BASE 树、V15 的 480 棵 BALANCED 树继续要求精确复现；旧结果只用于核对，不输入当前规划。

同时记录部署路径期望／最大实际样本、不同观测行、独立／十查询分摊成本；另列全树物理获取、共享准备、完整模型构建、真值评价、历史核对和压缩成本，嵌套计时不重复相加。停止次数按历史节点数和真实到达概率分别汇总，检查停止时原经验价值区间是否仍未闭合。

必要测试检测误用差距分配、停止触发顺序错误、CONTINUE 改变原均衡策略、样本上限或费用归因遗漏。通过后只运行一次冻结名册，不根据结果调参数或重跑。固定导出 BALANCED_GAP_STOP 的原三组历史：spawn2/832101 十查询、crossing3/832102 risk5、crossing2/832102 四个 goal 配对查询，使用原 V13 格式在新进程逐历史重放。

## 范围

仍为已暴露开发证据；启发式分离没有统计置信或真最优保证。部署路径期望费用与全树物理费用分开解释，时间为路径加权操作计时。U005 FAIL、U006 未启动、原 V2 延期 24 候选未执行保持。原 V14–V16 代码、结果与 Gate 不修改。
