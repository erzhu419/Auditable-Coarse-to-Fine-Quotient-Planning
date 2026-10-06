# V324：新目标学习历史上的 WIN-only 净收益与同预算对照

冻结日期：2026-10-06。V323 新执行流支持 WIN-only−FIRST，但 B 保留未解决。本轮重新采集并学习全部 16 个目标生命周期，parent=life%4；四个已核验 V312 SOURCE 和动力学固定。没有旧 FIRST、目标数据或目标版本复用。U005 FAIL 保留，U006 不运行。

## 学习方法与公平预算

A=.1、B=.5。各任务重新获取 131,072 raw 加实际检测开销，沿用 V309 确认两独立库；未确认则整队列 HOLD。以完整游戏 80% FIT 的观测固定库信念，用原 MC 双头方法、alpha=.0025 首次拟合 FIRST。QUERY_WIN、FACTUAL_WIN 各私有复制 FIRST，奖励参数随后始终只读。

按 A_R1、B_R1、A_R2、B_R2，由不可变 FIRST v0 H2 每阶段新采集 65,536 raw，物理执行一次、经济上对两学习臂计费。沿用 V319：从完整 FIT 非 WIN 且有同局 predecessor 的动作中等距取 32,768 锚点；实际 FIRST H2 的所有第二层非 WIN 预测调用组成有重复的有序池，每锚点一次独立 uniform 选根。在非空池锚点中等距取 16,384 位置，两臂共享位置与顺序。不足则 HOLD，不补采或替换。

FACTUAL_WIN 监督自然 afterstate；QUERY_WIN 监督实际 H2 查询 afterstate。两臂拥有相同生成式 reset 访问，每根四个全新 ground spawn，使用配对 cell/rank RNG。不可变 FIRST 在实际 postspawn 上选择同一联合 DIRECT 分支；非 WIN 目标 W=FIRST_P(next_afterstate)，立即 WIN W=1，LOST W=0。仍保存同分支的奖励目标以核验教师选择，但不用于更新。

每组一次当前 WIN 预测，以四个 W 的均值计算残差，按原 V319 tuple occurrence 归一化更新 WIN logit；alpha=.0025、地址与顺序不变，奖励完全不写。两轮教师始终为 FIRST v0，学习臂连续更新自身 v0→v1→v2。该 WIN 轨迹与同根、同标签的原双头更新精确一致。

每臂恰 4,194,304 新监督 raw、1,048,576 根组；物理新初始训练 raw 4,194,304 加检测，后续自然采集 raw 4,194,304，双臂监督 raw 8,388,608。共同采集/查询物理一次，经济上分别归属两臂。保存全部新采集 tape、锚点及查询路径、根/成员 spawn/目标、FIRST 及连续 WIN-only 稀疏版本。

## 新执行流与判定

SOURCE/FIRST 初始化和两学习臂每轮后，A/B 每单元固定 64 个新配对自然 H2 游戏，max_steps8192，共 12,288 局。所有初始及动作后 spawn 均计费。训练或评估 CUTOFF 整队列 HOLD，保存已观测端点，不替换种子、不扩大配额、不得把截断当终局。

唯一主终点：最终 QUERY_WIN−自身 FIRST_LOCAL 的 A/B 等权 utility，95% CI 下界>0。能力保留另要求 A、B 各自同对比下界>=0。QUERY_WIN−FACTUAL_WIN 为 nominal secondary，用于检验查询监督位置的贡献；净 SOURCE、FACTUAL 自身增益及首轮结果分别报告，不替代主终点。四固定父组内配对生命周期 bootstrap 20,000 次，seed32400001，所有对比共用抽样；HOLD 不执行 bootstrap。

种子固定：warm324100000000+task_index×100000+life×1000000+game；initial324200000000+task_index×100000+life×10000000；post324500000000+life×10000000+task_index×1000000+round×100000；selector324300000000+同 post 增量；ground324600000000+同 post 增量；eval324900000000+life×1000000+task_index×100000+episode0..63。配置在正式新采样前写入。

## 核验、成本与范围

独立 reader 检查新采集物理/RNG/FIT 边界、FIRST MC 目标及保存版本、查询路径、全部成员目标、WIN-only 连续版本及奖励不变、动作探针、评估 summaries、配对效应及成本；不重跑完整拟合、整局评估或 bootstrap。沿用评估接口，没有自然游戏逐动作 tapes。新拟合完整参数来自实际版本，MC 更新不作全量第二次训练复演。

输出全部位于 reports/win_learning_v324。新采集、处理、监督、更新、复制/保存、编译和协调均纳入完整进程树 CPU；V312 成功来源成本引用一次，旧目标实验不进入本轮执行成本，审计单列。历史动力学与失败尝试 CPU 未知。

本轮验证新的目标学习历史，仍条件于四个既有来源及生成式访问；不建立独立来源重复、普通在线采样效率或一般战略学习。无论正负，不按结果更改种子、学习率、轮数、组数、候选、区间或阶段条件。
