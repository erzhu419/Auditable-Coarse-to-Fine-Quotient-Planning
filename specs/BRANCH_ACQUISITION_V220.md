# V220 冻结：候选条件下的观测分支积分

2026-10-02，任何新目标采样前冻结。V218/V219失败保留。

沿用V219的72条原初始SOURCE rows及逐算子计数，不重采来源、不导入旧目标、不给库追加成员。BRANCH/MEAN/SET/ORACLE各计FULL历史来源41472，LOCAL计独立历史来源12640。12完整生命周期，每life24新目标，公开case、潜在稳定K=3族及顺序沿用V213；这不是完整类型贝叶斯模型或一般战略学习的终局检验。

五臂BRANCH/MEAN/SET/LOCAL/ORACLE。真实候选联合置信盒、共同策略、风险证书、完整三查询proxy、停止、回退全部沿用V219。BRANCH与MEAN均先对每个未观测算子pilot16；达到384或query_ready停止。唯一新干预是非pilot获取预测。每batch16，共享新目标seed225000+(life×27+index)×3+operator_index；源前缀223000不变。bootstrap224900/5000次，12life配对。beta仍ln(2×5544/.05)：假想分支不是新的环境置信事件。

对当前候选i、算子op，用α=source_i[op]+member[op]+.5的Dirichlet-multinomial预测16次结果，当前候选等权；无候选用member+.5。枚举SHORT17、DETOUR153、RECOVERY17个整数结果，先逐结果混合候选条件概率，再对每个结果重算一次完整计划，共187支/获取决策。概率用Fraction精确计算并保留全部正概率；禁止先平均核或计数、只重算当前候选、截断低概率或改成Monte Carlo。每假想计划重新检查全部三个来源，允许候选恢复。

预测损失L=max(0,2−LCB)+max(0,proxy−.05)。proxy=None时仅预测用公开case的有限上界B替代：B为12个SHORT(2)×DETOUR(3)×RECOVERY(2)联合单纯形顶点上，三个完整查询各自纯策略效用range的均值最大值。实际proxy/证书/就绪不变。用math.fsum汇总float(P)×float(L)；DM概率、真实规划及证书仍精确有理数。按(预期损失、实际该算子观测数、固定算子顺序)选择，无舍入/新epsilon阈值。逐算子记录期望损失、ready/None概率、精确质量1和分支数，审计重建叶子。

仅假想规划缓存不变来源置信盒和直接(k,n)区间端点，每支仍重新计算交集、posterior、策略与proxy；真实planner不变。预测工作均forecast_计数，实际controlled sample/reset/draw及planning_calls只计真实决策。报告环境样本与计算时间，不将计算节省等同采样节省。

七项全部通过才支持BRANCH_ACQUISITION_SUPPORTED：
- COST：LOCAL−BRANCH生命周期总样本均值≥64、95%CI下界>0。
- QUALITY：后12目标获证≥108/144且不少于LOCAL、真实效用≥2、BRANCH−LOCAL效用差CI下界≥−.05。
- RISK：BRANCH全部新目标历史真实风险及计划风险上界≤.05。
- APPLICABILITY：后12正确集合复用≥108/144、完整三查询平均后悔≤.05。
- TARGET_EFFECT：SET−BRANCH总样本CI下界>0、BRANCH−SET后12后悔差CI上界≤.01。
- REFERENCE_QUALITY：后12BRANCH获证不少于SET、BRANCH−SET效用差CI下界≥−.05。
- MEAN_EFFECT：MEAN−BRANCH总样本CI下界>0、BRANCH−MEAN后12后悔差CI上界≤.01、后12获证不少于MEAN、效用差CI下界≥−.05。

重点因果对比BRANCH−MEAN隔离观测分支预测；SET是必须保留的强获取参照，LOCAL是公平生命周期成本参照。全部决策冻结后才真核评分。定向测试验证DM质量/矩、187分支缓存与原精确planner同值、真实证据无污染及None处理；失败则修实现再采样。正式目标跑一次，独立审计不导入producer，重建来源/新目标前缀、全部获取积分、计划/查询/停止/回退、历史与实际成本及七Gate。
