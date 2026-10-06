# V221 冻结：跨 episode 目标证据积累

2026-10-02，新目标观测前冻结。V220的5/7 NOT_SUPPORTED保留；本阶段保留SET强获取基准，不继续微调单步预测。

沿用原72个FULL/LOCAL初始SOURCE rows、原223000来源前缀和逐算子实测计数。PERSIST/FROZEN/ORACLE各计历史FULL来源41472（每life3456），LOCAL独立历史来源12640；不重采、不追加来源、不导入旧目标。12完整生命周期、每life24目标、原公开case顺序与隐藏稳定K=3机制族及无标签三源覆盖不变。四臂新目标共享seed226000+(life×27+index)×3+operator_index，bootstrap225900/5000，12完整life配对重抽。

PERSIST与FROZEN均使用V219 SET的TV身份获取、单/无候选证书获取、query_ready停止、384目标预算、每批16、原回退/三查询及风险阈值。LOCAL/ORACLE保持V219。所有目标初始member为空；每life只初始化一次PERSIST知识，不跨life泄漏。来源顺序保留，库仍只有原三源。

持久状态分开存储三个anchor的累计counts、独立bounds盒及提交数。初始counts/bounds均来自原FULL实测来源。PERSIST真实候选与安全规划使用当前成员自身原KL置信盒与各持久bounds的逐坐标交集；posterior点模型、query_proxy及TV获取使用该anchor累计counts+当前member，加一次Dirichlet(.5)先验。累计counts不能生成新的KL置信盒。

只在目标全部决策及终态查询已冻结后，且终态LCB≥2、mode=library、候选唯一、未进入member fallback时，提交该目标：把其原始member盒与唯一anchor持久bounds逐坐标相交；成员实测counts逐项加入该anchor累计counts一次。下一目标才可使用。多候选query_ready、失败及fallback不提交，不用真实identity或核决定归属。每目标留存完整library_before、commit(source_index,samples)及library_after；其余臂这三项为None。终态plan/envelope不被事后更新重写，提交不产生新样本/重置/环境draw。

置信度仍beta=ln(2×5544/.05)，每life覆盖原3×72个来源前缀及24×24个成员前缀、7个结果类别。持久相交复用已有原置信事件，不引入池化区间事件。在这些原盒同时覆盖真实核的事件上，真实anchor始终兼容当前成员；唯一候选归属必正确，提交后交集仍覆盖真实核，可按目标顺序归纳。此论证以完整稳定族及原三源覆盖为条件，不能转用于漂移或未覆盖的新机制。累计点模型用于获取预测，不是自适应池化后的安全置信结论。

真实评分只在12life全部决策冻结后发生。六项全部通过才PERSISTENT_EVIDENCE_SUPPORTED：
- COST：LOCAL−PERSIST生命周期总样本均值≥64、95%CI下界>0。
- QUALITY：后12目标获证≥108/144且不少于LOCAL、真实效用≥2、PERSIST−LOCAL效用差CI下界≥−.05。
- RISK：所有PERSIST新目标历史真实风险及计划风险上界≤.05，提交错归属为0（只在全部决策冻结后用真值评分）。
- APPLICABILITY：后12正确集合复用≥108/144、完整三查询平均后悔≤.05。
- TARGET_EFFECT：FROZEN−PERSIST总样本CI下界>0、PERSIST−FROZEN后12后悔差CI上界≤.01。
- REFERENCE_QUALITY：后12PERSIST获证不少于FROZEN、PERSIST−FROZEN效用差CI下界≥−.05。

同时报告逐life提交数、已归属的真实成员样本、实际归属正确性、后半成本及FROZEN−PERSIST获证/效用差。主对比检验持久化安全盒及点模型这整套学习机制，不分别归因；所有历史来源和新样本均计费，不把提交视为新环境样本。

定向测试检测错用池化KL、归属前泄漏/重复计数、集合或fallback误提交、旧FROZEN规则漂移。失败则只修实现后采样。正式新目标一次，独立审计不导入producer，重建原SOURCE、新目标前缀、滚动库及每次提交、实际选择/计划/查询/停止/回退、全历史风险/费用和六Gate；验证原库未污染及当前成员不提前反哺。源码/日志与小诊断均留在项目目录。本阶段若不能改善FROZEN，保留负结果并定位置信盒或预测点模型的限制，不改Gate或换流追逐成功。
