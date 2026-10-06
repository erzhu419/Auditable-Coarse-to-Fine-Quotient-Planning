# V224：直接检验完整原 SET 强基线

2026-10-02，新目标采样前冻结。V223 同置信口径的累计收益成立，但其四臂联合预算削弱原来源端点，不能据此宣称超越 V221。当前移除强制 DETOUR 补采，保留原来源事件及原始端点。

三臂 ORIGINAL、FIXED、UNION。ORIGINAL 完整执行 V219 SET（即 V221 FROZEN），原 source/member beta=ln(2×5544/.05)、原候选兼容、点模型、获取、停止、query_ready 及回退均不变。FIXED 与 UNION 使用相同旧 source 盒及新成员预算、simplex 投影和原 source+当前 member 点模型；仅 UNION 在每个目标全部终态决策及查询冻结后，纳入该目标全部实测计数，重建归属外包络供下一目标使用。失败、多候选和回退目标全部保留，不用真身份提交，不把当前 member 提前池化。每个前缀独立从原 raw compatibility 重建，累计只改变安全盒。

原三来源计数不重采，各臂计 41472 历史样本（3456/life），不导入任何旧目标。12 原完整生命周期，每 life 原顺序 24 目标；所有臂共享新 seed230000+(life×27+index)×3+operator_index 的算子前缀，384 总预算、每批 16、来源访问为 0。bootstrap229900/5000，按12整个 life配对重抽。

ORIGINAL 保持旧 family5544/.05，覆盖至少95%/life。旧来源 family1512 消耗 δ_source=.05×1512/5544=3/220；FIXED/UNION 的成员 family4032 分配 δ_member=1/88，beta=ln(2×4032/(1/88))。两项和为 .025；FIXED 至少97.5%/life，UNION 再分配 pool family13608 的 .025，beta=ln(2×13608/.025)，至少95%/life。明确是**各臂各自覆盖**，不声称三臂联合95%或12life同时95%。不修改旧模块全局 BETA。union 覆盖属于保留真实固定归属的完整分支及其外包络，虚构归属不享有 iid 池化结论。

五项全部通过才 STRONG_REFERENCE_LEARNING_SUPPORTED，否则 NOT_SUPPORTED：
- RISK：三臂全部历史计划真实风险及上界≤.05、错误复用为0；库覆盖三核、保留全部已观察真归属、不可行模型为0。
- QUALITY：UNION 后12目标获证≥108/144且不少于 ORIGINAL 和 FIXED；真实效用≥2；对两参考的效用差95%CI下界均≥−.05。
- APPLICABILITY：UNION 后12正确集合复用≥108/144、完整三查询平均后悔≤.05。
- LEARNING_EFFECT：FIXED−UNION 每life总样本均值≥64、95%CI下界>0；UNION−FIXED 后半后悔差CI上界≤.01。
- STRONG_REFERENCE：ORIGINAL−UNION 每life总样本均值≥64、95%CI下界>0；UNION−ORIGINAL 后半后悔差CI上界≤.01。

报告两项直接学习/强参考对比，以及 FIXED−ORIGINAL 的置信分配影响；不能把胜过匹配对照替代胜过完整原 SET。全部计划与滚动库冻结后才评分真实核/身份，分别计历史来源、新目标和处理成本。未通过则保留负结果及失败 Gate，不换阈值、来源或随机流重跑。

定向测试检查 ORIGINAL 对实际 V221 留存计划/选择的完整一致性、三臂旧 source 端点原样、全量结束目标提交与当前任务不提前反哺、FIXED/UNION 点模型及初始规划一致。正式新采样一次，独立审计不导入 V224 producer，重建新批次、旧基线、获取/停止/回退、累计库及所有费用与五项 Gate。小份来源摘录、源码、日志留在项目目录。
