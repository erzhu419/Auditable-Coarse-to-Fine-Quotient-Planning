# V191：98维关系模型的线性排序容量

V190已消除旧20个同根信息冲突，但新TARGET96的RELATION比LINEAR低0.013157，四副本均负。本轮用留存SOURCE143、TARGET96与JOINT239分别检验线性评分的表达能力，并记录已训练模型在SOURCE的实际排序误差；不新采样、取标签、训练、部署或调参。

固定评分s(a)=r(a)+Σ beta[i]phi(a)[i]，98个beta无界、无截距，首reward一次。使用V190实际98维浮点数组，各坐标以Fraction(float)精确保留，不round、不limit_denominator、不更换基、不合并近似同值动作。SOURCE从既有layout缓存推导一次98向量；TARGET复用已认证relation_features，不新swipe。每个scope保留全部合法动作，按完整R−F+S及原EPS1e−12定义所有最优选项；全最优根无需排序约束。

每个最佳候选a与次优b约束(phi_b−phi_a)·beta+delta≤r_a−r_b；差分先做精确有理减法，再转换到数值LP。delta≤1，其余变量无界，最大化delta。保持V180完整析取：先约束唯一最优根；按root_id第一个违反的未分配并列根，以ACTIONS DOWN/LEFT/RIGHT/UP全部最优选项DFS。全根严格见证才能提前成功；否定结论必须覆盖全部分支，不能固定一个任意oracle并列动作。

数值LP只提供候选。正结论需exact rational全部最优对次优gap>EPS，并以Python sum按98列顺序求积和、最后加r，在原ACTIONS/EPS下实际float选择全部最优；此见证可用margin cap给上界1，无需为无关数值dual付symbolic solve。需要剪枝时，只在native正support上做一次精确有理balance：lambda≥0、98个feature净和全0、delta权重和1，sum(lambda·rhs)才是共同margin上界。负上界才说明该评分函数类存在排序冲突；零上界不证明实际并列策略不可能。记录exact及float弱见证，分别保留判定；数值失败/无精确证据为HOLD，保留已付成本，不伪造证书。

SOURCE已训练模型使用V190完整三分量推理，先保存observable-only决策，再读取其完整标签评价错误/遗憾；不假定将三头折成单beta后的float历史与原历史相同。TARGET使用原冻结RELATION决策/summary，不重复旧评分。容量见证使用过目标标签，仅为存在性诊断，不能作为新学习或迁移收益。

冻结源码/协议/tests/wrappers原字节后，八输入依序复制：V190stage_checks（初始valid=false保留）、metadata_binding_amendment/result（corrected_valid=true）、run（complete）、roots、labels、model、choices、summary。旧源码/输入比较须已通过。全部输入protocol_frozen留存；phase protocol_frozen(0reads)→problems_frozen(8)→capacity_SOURCE→capacity_TARGET→capacity_JOINT→complete，其余均8reads。三scope各一次capacity调用；内部LP/DFS/balance均计费，失败停止后续scope。main/audit各一次，threads1，零新kernel、教师规划、物理随机样本或native更新。

独立审计重建SOURCE关系缓存、全部问题、来源决策与摘要；重放exact/float primal，核对99坐标dual、非负权重、上界及分支覆盖，不重解LP/SVD或重复核积分。输入字节分析比较一次，源码stage比较一次，不加hash。记录SOURCE编码、问题矩阵、实际评分、LP、symbolic balance、exact/float评价、读取与继承成本链；中途仅reports/v191_runtime_tmp，结果仅reports/controlled_predictive_relation_capacity_v191。

下一步由证据决定：SOURCE负容量则更换后果模型的函数类；SOURCE正容量而已训练排序仍错则定位拟合目标/正则化；SOURCE与TARGET各自正、JOINT负则定位共享函数的跨域冲突。不以改变label或Gate消除反例。

限制：已暴露的有限H3根与固定后续教师；精确负证书约束数学线性评分，正证书同时校对具体浮点评分。正容量不等于可学习性或未见场景迁移；零margin不解决全部并列策略。保留H2、U005 FAIL、U006未启动。
