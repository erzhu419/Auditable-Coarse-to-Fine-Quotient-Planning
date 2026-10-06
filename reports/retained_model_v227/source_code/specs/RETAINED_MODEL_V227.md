# V227：执行回退与模型知识分离

状态：留存轨迹上的接口修正与验证，不是新科学实验。V226 的 3/6 Gate、预算和负结果保持原样。

## 修正

执行是否达到效用证书，与兼容模型是否仍可用于查询，是两个判断。终态仍按 V226 规则产生 execution_plan、回退、认证和停止状态；advance 只消费 execution_plan。若回退前的 library 模型仍有兼容候选，则 knowledge_plan 保留该模型，查询消费 knowledge_plan。无兼容模型时仍使用 member 模型。保留点预测不提高 query_ready，也不增加认证或转移成功数。

## 固定输入与验证范围

- 使用已独立验证的 V226：12 life × 24 target × 4 arm，共 1152 条完整历史及原来源计数。
- 不生成来源或目标样本，不改变旧增量、预算、停止、动作历史、执行计划、提交或滚动模型状态。
- producer 按原顺序重放全部计划和获取决定，逐项与原记录比较；终态仅分离两个接口。
- 独立分析由旧增量重建终态并重算分离、查询和滚动更新，不调用 V227 producer/core，不重复已完成的环境随机流审计。
- 真身份／真核只用于全部决策冻结后的覆盖和 regret 评价，不进入模型选择。
- 适用范围仍是原有限、完整、稳定的三类型族；不能据此接纳未知新机制。

## 四项接口验证

1. EXECUTION_AND_COST_UNCHANGED：原采样与执行历史、提交／滚动状态、来源和目标费用一致；本阶段环境采样为零。
2. MODEL_SCOPE：保留的 library 含真实候选，区间覆盖真实核；无兼容来源时使用 member。
3. CERTIFICATES_UNCHANGED：原认证、转移、停止和回退状态一致；knowledge query_ready 不被提升。
4. QUERY_RETENTION：查询与 knowledge_plan 一致，LOW_UNION late 平均 regret 比原回退下降且不高于 0.05。

四项全通过只签发 MODEL_RETENTION_INTERFACE_VALIDATED。描述性配对 bootstrap 固定 seed 233900、5000 次，以 life 为单位比较 late 的旧减新 regret；它不重判 V226 科学 Gate。

## 下一阶段

保留接口修正后，进入 GPT_MultiEpisode.md 第二阶段的情境限定 A→B→A′ 机制修订设计。先证明新的覆盖范围和置信预算，再冻结 fresh test；不继续微调 V226 来源预算。见 SCOPED_REPAIR_V228_DRAFT.md。
