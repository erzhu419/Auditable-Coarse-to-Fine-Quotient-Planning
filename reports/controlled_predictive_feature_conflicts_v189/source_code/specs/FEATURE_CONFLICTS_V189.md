# V189：固定六特征错误的信息容量诊断

V188 的 INTERACT 未超过同流程 LINEAR，后者在 TARGET96 仍有44个正遗憾根。本轮固定全部96根，不只挑错选；沿用已留存 SOURCE143、六维 action_features、可观测首奖励、完整 R/F/S、冻结教师、ACTIONS DOWN LEFT RIGHT UP 与 EPS=1e−12。目标已暴露，这是诊断，不是独立验证或新策略。

逐根按完全相同六维 tuple 合并行动。同类代表由首奖励最大及固定 ACTIONS/EPS 规则决定；保留全部原行动、原oracle最优集合、代表最优集合、LINEAR 实际选择和完整 R/F/S。允许每个根独立任意 g(phi) 时能达到的最优代表给出逐根上界；分解原oracle−LINEAR遗憾为原oracle−alias最优和alias最优−LINEAR。前者衡量该根六特征损失，后者不自动等于可学习误差。

对 TARGET 的代表问题复用已审计 V180 build_problem、V181 lift_problem/solve_capacity：共享评分 s_a=r_a+g(phi_a)，每个不同 tuple 的潜值任意无界；保留全部 optimal 析取，delta≤1、精确有理 dual 流平衡、DFS 分支覆盖及实际EPS选择。只新解 TARGET 一个scope。旧 V181 SOURCE 六特征冲突已成立，不重解 SOURCE 或 JOINT。负上界证明任何共享 g 都不能同时达到该批根的全部代表最优；零上界仅排除正间隔，不自动排除并列策略；只有严格全scope见证才能证明该批根的代表排序可达。诊断潜值不能部署或当作来源学习收益。

解释每个证书支持项的根、best/bad行动、六tuple、原首奖励及其精确差、完整 R/F/S、真实效用差与权重。精确顶点净流消去 g；负证据只推出支持根中至少一根无法满足，不能把每个支持根都判为不可修复，也不等于最优平均效用的精确上界。

SOURCE 仅用于覆盖：合法有向动作对 a!=b 的 (phi_a,phi_b)，以及追加 Fraction(r_a)−Fraction(r_b) 的奖励阈值；目标保留逐根 tuple/pair/threshold 覆盖和 LINEAR 错选的全部最优代表对照。结构出现过不等于可学习，未见结构标记外推需求，不作新Gate。

真实读取前冻结协议、代码、测试和wrappers。五输入为 V188 stage_checks/run/roots/labels/summary，读取时phase protocol_frozen，先复制原字节再运算；不读大模型或kernel。阶段固定 protocol_frozen(0 reads)→retained_inputs(5)→diagnostics_frozen(5)→target_capacity(5)→complete(5)。main/audit各一次，线程1；五输入在独立分析比对一次，源码由stage比对一次，无hash。

独立审计重新计算新增alias/覆盖/汇总，复用 V180/V181 的独立问题重建和精确证书/分支校验，不新解LP、不重估后果、不重fit模型。保留新问题构建、覆盖、LP/symbolic、证书读取及旧成本链；solver错误保留实付记录并HOLD。纯测试限于新增语义和执行隔离。

全部中途文件仅 reports/v189_runtime_tmp（包括pytest临时目录），结果仅 reports/controlled_predictive_feature_conflicts_v189。零新预测器、来源游戏、样本、标签、核或native更新。限制：固定教师、有限H3根；容量不证明一般战略学习或采样效率。保持H2、U005 FAIL、U006未启动。
