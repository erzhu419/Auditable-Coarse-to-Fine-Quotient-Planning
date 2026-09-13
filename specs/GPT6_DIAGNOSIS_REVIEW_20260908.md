# GPT6 诊断核验与项目调整（2026-09-08）

## 结论

诊断的研究方向正确，可以据此调整：保留 U005 科学 FAIL，关闭当前方法的续调路径，U006 assurance 继续不运行；新的探索转向动作条件的可执行商模型，并直接测多步规划后果与计算量。但它没有定位这次失败的具体原因，新方案也不是已获验证的解决办法。

需要修正三个关键解释：旧方法已经有动作输入及多时距未来预测；旧 AUROC 衡量玩家技能识别，并非状态对行为等价；shuffled 保留玩家内的未来目标分布，本来就可能保留技能相关信号。新方向必须改变建模对象，不能仅补一个已有的 dynamics/forecast loss。

## 本次核验的事实

本次以独立源码目录 `acfqp-learned-resource-forecast-2048-pilot-u005-source` 的 clean commit `8dcd411b9c662448f283a8bc83c736e148bb3f54` 为准。原项目目录当前是另一条较早主线，不能用其 HEAD 代表 U005。新探索工作树由该 U005 commit 派生，分支为 `codex/controlled-predictive-quotient-exploration`。

在 `jtl110gpu2` 上读取小 JSON/日志，并在服务器端提取库存字段，结果为：

| 事实 | 核验结果 |
| --- | --- |
| 前置条件 | 17/17 |
| 主 Gate | FAIL，2/6 |
| Aligned probe AUROC | 0.5758219955，95% CI [0.5243077388, 0.6283363127] |
| RAW probe AUROC | 0.5535182823 |
| shuffled probe AUROC | 0.6087128862 |
| Aligned − RAW | +0.0223037132，95% CI [0.0097753562, 0.0348195152] |
| Aligned − shuffled | −0.0328908907，95% CI [−0.0526166800, −0.0124506880] |
| 独立验证 | valid=true |
| 分析目录 | 正好 9 个文件 |
| 留存库存 | 2064 entries，2065 physical files，retention_complete=true |
| stderr | 0 bytes |

终态日志的最后阶段是 `ANALYSIS_VERIFICATION_COMPLETED_RETENTION_READY`；完成留存的依据来自库存，不能只看这个阶段名称。本次没有重跑科学分析、独立验证或留存，也没有下载 checkpoint、矩阵或轨迹。

服务器端依据（共同前缀 `/home/erzhu419/mine_code/`）：

- `acfqp-learned-resource-forecast-2048-pilot-u005-analysis/pilot-result.json`
- `acfqp-learned-resource-forecast-2048-pilot-u005-analysis/independent-verification.json`
- `acfqp-learned-resource-forecast-2048-pilot-u005-analysis/aligned-resource-forecast.receipt.json`
- `acfqp-learned-resource-forecast-2048-pilot-u005-analysis/player-shuffled-resource-forecast.receipt.json`
- `acfqp-learned-resource-forecast-2048-pilot-u005-status/analysis-postprocess.jsonl`
- `acfqp-learned-resource-forecast-2048-pilot-u005-retained/retention-inventory.json`
- `acfqp-learned-resource-forecast-2048-pilot-u005-launch/postprocess.stderr.log`

本地 U006 源码 clean HEAD 为 `0fb65faa88bb14b8531fbee2e3d544937d654a02`。其 `specs/LEARNED_RESOURCE_FORECAST_U006_PROSPECTIVE_ASSURANCE_V1.md` 明确只接受前置条件及六项 Gate 全通过的 U005，失败结果连该工具的 summary/assessment 入口也不能使用。三个原实验服务器的项目根下均无匹配的 U006 输出路径。本次没有调用 U006。

## 对诊断的具体修正

### 1. AUROC 检验的不是“状态距离是否具有规划意义”

旧实验的输入是机器玩家最初八个合法动作的探针。标签由每个冻结玩家另外 64 个完整 episode 的平均合并分数决定：使用训练玩家的 25%/75% 分位数阈值划定 NOVICE/EXPERT，阈值固定后用于测试玩家。中间玩家不进入二分类 Gate。

预测对象是玩家，Gate 的数值按 probes 计算；不确定性按 16 个 held-out base training seeds 做 20,000 次配对 cluster bootstrap。同 seed 下的三个生成器、三个 checkpoint、重复探针都不构成独立训练样本。2064 是留存条目数。

因此，本次直接否定的是冻结设置下“对齐未来资源预测表示能为八步玩家技能识别提供规定强度且优于两类对照的信号”。它没有测量 quotient 的状态合并误差、规划收益或压缩率，也不能单独判定这些对象失败。

源码依据：[U002 协议](LEARNED_RESOURCE_FORECAST_2048_PILOT_U002.md) 的标签、classifier、metrics 和 Gate 小节；`learned_resource_forecast_evaluator_v1.py` 中的 `assign_skill_labels_v1` 和 cluster metric/bootstrap 实现。

### 2. 旧方法已有动作输入和未来预测，但没有受控递推闭合

旧 GRU 读入 8×21 的棋盘、动作 one-hot、合并收益 tokens，输出 64 维 embedding；训练时用线性 head 同时预测未来 1、4、16 步的资源坐标、累计合并收益和终止指示，共 54 个目标，固定 50 epochs 的 MSE。分类时丢弃 forecast head，拼接原始 184 维 prefix。

这不是静态状态相似性学习，也不是完全缺少时序信号。区别在于目标来自后续既定玩家策略，而未来替代动作不是可控制输入；没有要求 `P(z'|z,a)` 的输出继续进入下一步模型，也没有编译商状态、动作转移或独立计划误差包络。

本次新对象是从每个合法动作的转移响应中发现有限 cells，显式编译抽象随机转移，使规划器在这些转移上递推。它和旧的玩家技能 classifier 在学习对象、输出以及验收问题上都有实质差异。

### 3. shuffled 的意义应从实现说明

`player_shuffled_targets_v1` 对每个训练玩家的完整 54 维目标行作固定 Sattolo 置换，多窗口时无固定点。它保留该玩家的目标边际分布和目标坐标间关系，移除窗口与局部未来的对应，不是跨玩家混洗、技能标签打乱或坐标排列。两臂使用相同初始化和优化设置。

Aligned 相对 RAW 的改善不足以归因于正确的局部未来对齐。shuffled 更好也不能证明污染、实现错误或输入缺少技能信息。玩家层面的分布信息可能有利于技能识别，这是与实现相容的解释，尚未被本次实验隔离证明。

Aligned 自身训练 MSE 约从 0.03075 降到 0.01896，shuffled 约从 0.04122 降到 0.03731。这些是不同配对目标上的训练误差，不是 held-out forecasting 质量，不用于挽救 Gate。

### 4. reference quotient 是范围明确的开发诊断

有限实例上找到高质量压缩商，可以证明这些实例存在相应压缩机会。反之，一个启发式 reference builder 未找到压缩，并不证明所有近似商、动作抽象或查询族都不可能压缩。即使精确行为分割接近完整状态，结论也只针对该有限 horizon、固定动作和精确预测要求。

新的原型使用有限、分层的动作响应分割；精确模型仅作开发 reference 和计划审计。经验商和完整状态经验基线共享同一批采样转移。reference 单独记账，不混入同信息量学习对照。

### 5. 文献与数学表达

[DeepMDP](https://proceedings.mlr.press/v97/gelada19a.html) 的奖励及下一 latent 分布联合预测，与建议的方向相符；[Value Equivalence](https://papers.neurips.cc/paper_files/paper/2020/hash/3bb585ea00014b0e3ebe4c6dd165a358-Abstract.html) 的确以指定策略/函数族的 Bellman 更新定义模型等价。这些论文的保证不直接成为本项目的证书。

原文第 [3] 项链接是 [Farahmand 等 2017 年 VAML 提案](https://proceedings.mlr.press/v54/farahmand17a.html)，可以支持 value-aware 目标的来源，不能单靠它支撑“后续研究发现某些 surrogate 无法恢复正确模型和值函数”这句具体判断。该后续文献未被原文给出，本次不以此判断作为修改依据。

原文 `D_plan` 可作为研究目标，但必须明确查询族、lifted policy 范围、有限 horizon，并使用严格正的累计收益归一化尺度；若分母只是单步奖励界，不能把它当作总收益范围。有限开发查询的最大观测误差只报告为测量，不写成所给 supremum 的证明。

## 已采纳的调整

新的开发实现及实验说明见 [受控预测商开发协议](CONTROLLED_PREDICTIVE_QUOTIENT_DEVELOPMENT_V1.md)。保留现有 mechanics engine 和旧正式执行体系，以全新的开发输入完成一个可运行的有限切片：全动作观测、经验响应分割、可执行商、模型内多步规划、精确 lifted-policy 审计，以及跨查询复用。先回答是否出现“有压缩且规划后果正确”，再决定学习方法是否值得扩展。

旧 U005 作为失败的历史参照保留。它没有 planner，因此不能硬造一个“冻结旧表示规划组”，也不重新训练、重新编码或读取旧 test 数据来适配新任务。新比较中的完整状态经验模型才是与商模型同信息量的规划对照。

## 限制与尚未确定的事项

- 本次定位了 estimand 和机制区别，没有确认这次技能识别失败属于输入信息不足、信息被表示抹去还是 classifier 读出不匹配。
- 首个新切片是标准 4×4 2048 的公开密集棋盘、有限 horizon 开发诊断；状态覆盖由已知 mechanics 枚举，映射只覆盖已枚举状态，不代表完整自然开局 episode 或未见状态泛化。
- 样本商不是 sound certificate；独立有限模型审计承担此切片的误差测量。当前切片未接入生产 CEGAR、动态恢复或统计 envelope。
- 所有新数值是开发观察，没有新确认 Gate，也不授权 U006。正式后继仍需另行冻结科学问题、训练方法、独立数据与对照，然后获得相应运行授权。
