# V223：累计学习与付费 DETOUR 供给的配对实验

2026-10-02，新目标采样前冻结。V222 的固定轨迹仅有 1 个新增获证目标，无首次获证提前；全部目标 DETOUR 观测为 0。新实验检验实际获取后的学习效应，不把补采收益当作学习收益。

四臂 FIXED_SET、UNION_SET、FIXED_DETOUR、UNION_DETOUR，组成来源固定／累计置信模型 × 原 SET／付费 DETOUR 首批。原 V221 三源计数不变，每臂计历史来源 41472（每 life 3456），不重采来源、不导入旧目标。12 个原完整 life、每 life 原顺序的 24 个目标；新目标共享 seed228000+(life×27+index)×3+operator_index，每算子独立同前缀。384 样本上限、批量 16。bootstrap seed227900、5000 次完整 12 life 配对重抽。

DETOUR 两臂在每个目标开始支付 16 条 DETOUR_PASS 观测，纳入 384 上限，再继续原 SET 的 TV 身份获取／成员认证获取、LCB≥2 及 query_proxy≤.05 停止。SET 两臂不强制首批。四臂使用相同新 raw KL beta、相同 simplex 投影及原 source+当前 member 点模型和查询代理。累计只改变安全盒；不学习累计点模型、不调整停止阈值、来源访问及回退规则。

UNION 两臂在全部终态计划与查询冻结后纳入该目标全部实测计数，包括失败、多候选、fallback。每次从原 raw source/member compatibility 重建 V222 的归属 DP 外包络，仅供下一目标使用；当前 member 不提前池化、不跨 life 泄漏。FIXED 两臂原盒不变。没有可行库时使用成员模型；记录模型不一致，不按真身份修复。terminal 非唯一且非 query_ready 则按原规则 member fallback。终态判定、三查询及滚动库全量留存。

每 life 联合覆盖四臂：raw family=3×72×7+4×24×24×7=17640，beta=ln(2×17640/.025)；两个 UNION 实际池化流的 family=2×3×7×648=27216，beta=ln(2×27216/.025)。来源事件共享计一次，池化流分别计入，无需相互独立。两项误差预算各 .025，给每 life 所有四臂联合至少 95% 覆盖；不声称 12 life 同时 95%。每次 union 保留真实分支的证明及所有目标观测纳入要求沿用 V222。所有计划冻结后才进行真值评分。

五项全部通过才 DETOUR_SUPPLY_LEARNING_SUPPORTED，否则 NOT_SUPPORTED：
- RISK：四臂每个历史计划的真实风险与上界≤.05，错误复用为 0；更新库覆盖三核、保留全部已观察目标真归属，模型不一致为 0。
- QUALITY：UNION_DETOUR 后12目标获证≥108/144，且不少于 FIXED_DETOUR 和 FIXED_SET；真实效用≥2；两项配对效用差 CI 下界均≥−.05。
- APPLICABILITY：UNION_DETOUR 后12正确集合复用≥108/144，完整三查询平均后悔≤.05。
- LEARNING_EFFECT：FIXED_DETOUR−UNION_DETOUR 每 life 总样本均值≥64，95% CI 下界>0；UNION_DETOUR−FIXED_DETOUR 后半后悔差 CI 上界≤.01。
- NET_EFFECT：FIXED_SET−UNION_DETOUR 每 life 总样本均值≥64，95% CI 下界>0；UNION_DETOUR−FIXED_SET 后半后悔差 CI 上界≤.01。

分别报告两个供给层的 learning、两个学习层的 pilot 和 learning_gain_difference=(FIXED_DETOUR−UNION_DETOUR)−(FIXED_SET−UNION_SET)，不以净收益替代学习判定；交互 CI 不支持则不称协同。实测付费首批、逐算子目标供给、获证/效用/后悔、完整历史安全、累计库和实际处理成本全部报告。

定向测试检测首批费用/预算、结束后全目标提交而非成功选择、当前任务泄漏与累计点估计混入，以及同置信口径四臂对照；同时运行 V222 原测试检测参数化后默认行为变化。正式采样一次，独立审计不导入 V223 producer，核对小份原来源、新采样前缀、获取/停止/回退、每次滚动库、实际费用与五项 Gate。所有中间文件在项目目录，负结果保留，不换流重跑追逐成功。
