# V18：评分增量更新与上界复用

本协议在 V18 真实运行前固定。V17 均衡停止保持 480 项完整策略后果同值、期望样本减少 10.37%，但计入评分后成本高于原均衡 35.41%。本轮只改变评分计算实现，要求完整采样、停止、动作和诊断历史精确一致。

## 固定比较

沿用 V17 冻结的 16 根、horizon、三个种子 832101–832103、十查询、查询顺序及暴露标签，每方法 480 项。六方法为 full_state_empirical、exact_empirical_quotient、online_mass_bound（BASE）、online_balanced_resampling（BALANCED）、online_balanced_gap_stop（原 V17 STOP）、online_cached_balanced_gap_stop（CACHED）。四 ONLINE 按 (根索引+种子索引+查询索引) mod 4 轮转，共 1920 棵历史树。

每根／种子重新付费构建原 V14 MASS_BOUND、最多 32 行的十查询 warm。BASE 直接使用；独立进行 V15 整数计数转换、V16 GapPlannerState 转换、V18 CachedGapPlannerState 转换，分别供 BALANCED、STOP、CACHED。物理账共三次转换；每个方法承担完整 warm 和自己的转换费用，另列十查询分摊。缓存从空开始，初始化、失效标记、更新与复制均收费。两个全行参考共享付费支持及完整采样，预算与 ONLINE 不同。

原 V15 批流、批号和种子公式不变：每批 256 次，路径总上限 128 批，即 32768 实际样本，包含 warm、首次及重采；每个 ACTIVE 决策配额为 floor((128−spent_batches)/h)。原 STOP 与 CACHED 均调用未经修改的 V17 STOP 执行器，没有 Stage A128 或来源训练。

## 计算实现的唯一变化

新类按查询持有 V16 上下界评分、动作评分、续策、误差尺度及失效状态。第一次评分计算全部已观测状态；首次或重复获取后，仅将变化行所在状态及已观测祖先标记失效。新增已观测状态也在全部已初始化查询中失效。按原 horizon／board 顺序更新，原 fsum 表达式、样本行顺序、合法动作和平局顺序不变，不近似、不改阈值。

V15 均衡选择使用与 V16 相同的 Qplus 递推，因此复用更新后的 upper、q_upper、upper_policy 及已观测行 radius。候选传播和最少批数选择仍调用原逻辑。原 assess_gap 继续生成全部诊断，包括候选对和候选数；停止条件、结构前沿优先级及最终经验动作不变。

兄弟历史各自复制可变缓存和失效集合。查询切换保留各查询自己的缓存；新支持和本次实际状态揭示必须被纳入后续评分。没有跨查询／历史免费复用观测或来自旧报告的模型状态。

## 评价与完成条件

全部当轮执行树先冻结，再计算真最优标签并读取历史结果。要求 CACHED 与当轮原 STOP 的完整 trace 及 root_metrics 精确一致，不排除任何诊断字段；原 STOP 与留存 V17 的 480 棵树精确一致。保留 V14 的 48 个 warm 前缀／480 棵 BASE 树、V15 的 480 棵 BALANCED 树复现。成本和工作计数独立比较，不要求相同。

主配对 CACHED vs STOP 检验实现优化；另列 CACHED vs BALANCED、CACHED vs BASE、STOP vs BALANCED。保留完整策略 reward/failure/success/value、全部退化、原八项／五项见证及 root／family／split 汇总。评分状态访问、上界复用、失效更新、query clone 与兄弟缓存复制分别计数；报告评分／选择／模型更新等阶段计时、独立与十查询分摊费用及物理全历史成本，内外层计时不重复相加。

针对性测试检测增量失效遗漏、新支持／实际状态揭示遗漏、查询及兄弟历史串扰、上界复用数值差异、执行历史变化和三次转换费用遗漏。通过后仅运行一次冻结名册，不根据结果调整规则或重跑。固定导出 CACHED 的原三组历史：spawn2/832101 十查询、crossing3/832102 risk5、crossing2/832102 四个 goal 配对查询，沿用 V13 格式在新进程逐历史重放。

## 范围

本轮检验计算成本，全部输入仍为已暴露开发材料；启发式分离没有统计置信或真最优保证。时间为路径加权操作计时，部署期望费用与全树物理费用分别解释。U005 FAIL、U006 未启动、原 V2 延期 24 候选未执行保持。原 V14–V17 代码、结果与 Gate 不修改。
