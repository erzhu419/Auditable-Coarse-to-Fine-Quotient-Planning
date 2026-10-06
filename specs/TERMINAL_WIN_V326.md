# V326：终局 WIN 标签的实际学习干预

冻结日期：2026-10-06。V325 固定快照诊断发现 FIRST 教师的 WIN 偏差在 A/B 方向相反；较好的预测尚未建立学习净收益。本轮从真实终局标签切入，重新获取全部 16 个目标生命周期。四个 V312 SOURCE 固定，parent=life%4；不复用旧 FIRST、目标样本、标签或学习版本。U005 FAIL 保留，U006 不运行。

## 方法与对照

A=.1、B=.5。各任务由 SOURCE 新获取 131,072 raw 加实际检测开销，V309 确认两独立库；以完整游戏 80% FIT 固定库信念、原 MC 双头方法 alpha=.0025 得到 FIRST。BOOTSTRAP_WIN、TERMINAL_WIN 各私有复制 FIRST，奖励参数此后完全只读。教师、后续自然采集策略、规划信念始终冻结于该生命周期 FIRST v0。

按 A_R1、B_R1、A_R2、B_R2，每阶段 FIRST H2 新采集 65,536 raw。从完整 FIT 非 WIN 且有同局 predecessor 的动作中等距取 2,048 锚点；实际 H2 第二层全部非 WIN 预测调用的有重复有序池，每锚点一次 uniform 选根。在非空池位置中等距取 1,024 个 QUERY 根。每根共享四个全新 ground spawn；FIRST 在 postspawn 上选择联合 DIRECT 分支。BOOTSTRAP 标签沿用 FIRST_P(next_afterstate)、立即 WIN=1、LOST=0。

从相同已支付的首 spawn 开始，执行保存的 DIRECT，再由冻结 FIRST H2 在真实世界走到自然终局；TERMINAL 标签 W=1(WON)，否则0(LOST)。DIRECT 及后续每动作的新 spawn 均计费，包括获胜动作。不把初次 spawn 重算为后缀成本，也不把 CUTOFF 当 LOST；完整后缀动作、RNG、终态和边界 H2 探针留存。标签不估计更新策略或最优策略的真实价值。

双臂每阶段对相同 1,024 根按相同顺序做 16 遍 WIN-only 更新，每遍重算当前预测，alpha=.0025，每组四成员均值、原 tuple occurrence 归一化；每臂恰 16,384 更新。此配额在新采样前冻结，约束昂贵的终局续跑，同时避免极弱的一遍干预。原始采样根组仍为1,024；重用样本不增加独立信息，不恢复 V324 的根覆盖。两轮更新自身连续 v0→v1→v2，奖励完整表保持 FIRST 不变。

## 新自然执行与裁决

SOURCE/FIRST 初始化、双学习臂每轮后，各任务每单元 64 个新配对自然 H2 游戏，max_steps8192，总 12,288 局。唯一主终点：最终 TERMINAL_WIN−自身 FIRST_LOCAL 的 A/B 等权 utility，95% CI 下界>0。A、B 各自同对比下界>=0 为分别必需的保留条件。TERMINAL−BOOTSTRAP 为 nominal secondary 标签机制对照；净 SOURCE、BOOTSTRAP 自身及首轮结果分别报告，不替代主终点。四固定父组内配对新生命周期 bootstrap20,000次，seed32600001。任何初始库/查询配额不足或训练、终局监督、评估 CUTOFF 均整队列 HOLD，保留实际数据，不 bootstrap、不换种子、不追加配额、不调参数。

种子固定：warm3261000000000+task_index×100000+life×1000000+game；initial3262000000000+task_index×100000+life×10000000；post3265000000000+life×10000000+task_index×1000000+round×100000；selector3263000000000、ground3266000000000 使用同 post 增量；continuation3267000000000+同增量+group×4+member；eval3269000000000+life×1000000+task_index×100000+episode0..63。配置在正式采样前写入。

## 成本与范围

共享自然采集、查询与初次 spawn 物理一次，经济上归属每个学习臂。终局后缀 raw 全部额外归属 TERMINAL；总计262,144个新初 spawn/终局续跑、每臂1,048,576次优化更新；实际后缀长度不固定，全部纳入成本。阶段检验同根标签替换的因果贡献，不声称同总 raw 预算效率。样本复用放大局部 Bernoulli 噪声的风险由新整局效用检验。

所有输出位于 reports/terminal_win_v326。新采集、处理、标签、续跑、重复拟合、复制/保存、评估、编译及协调均计入完整进程树 CPU；成功 V312 来源成本引用一次，旧目标实验不继承，审计单列。独立 reader 检查新 tape/RNG/FIT、共享 QUERY/成员/教师标签、全部续跑物理及终局标签关联、各遍更新计数/残差样例、实际连续版本和奖励不变、自然评估端点/配对效应/成本，不复演完整训练、自然评估或 bootstrap。四固定来源、生成式任意 reset、未知历史动力学及失败尝试 CPU 仍为限制。
