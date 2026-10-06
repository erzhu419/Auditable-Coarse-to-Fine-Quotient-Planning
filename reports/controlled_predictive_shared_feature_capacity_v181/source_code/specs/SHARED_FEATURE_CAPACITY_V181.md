# V181：任意共享特征函数的跨根容量

V180 已用精确证据排除固定六phi的共享线性评分完整复现正确动作排序；其证据未消去逐feature tuple势值，因此未排除非线性。本轮检验六维信息本身能否支持跨根一致排序，仍是容量诊断，不训练或部署新模型。

直接复用已独立审计的V180 SOURCE47/TARGET24/JOINT71问题。原classes、完整R/F/S、首reward、optimal/suboptimal集合、EPS1e-12、ACTIONS DOWN/LEFT/RIGHT/UP及同phi代表规则原样保持。每scope全部不同六维tuple按字典序成为vertices，各class记录vertex_id；JOINT中来源与目标的相同tuple必须共享一个vertex。此前正确的56个absorbing-goal标签、features和kernel不重复计算/审计。

评分s_a=r_a+g(vertex_a)，每vertex一个任意实数潜值。无参数界、平滑、函数项、训练正则或跨根独立潜值。每根任取一个optimal a，对所有suboptimal b要求g_b−g_a+delta≤r_a−r_b；另delta≤1，所有变量无下界，最大化共同delta。矩阵用vertex incidence稀疏表示；此类包含任意共享非线性g(phi)，是函数类上界而非已学方法。

保持V180完整最优析取语义：先唯一optimal根；全optimal根无需约束；全根strict见证可结束，否则按root_id第一个违反的多optimal根，以全部optimal ACTIONS顺序DFS分支。每部分约束LP的精确非正上界剪整棵子树；全部替代被覆盖才能报告否定。不得固定任意oracle并列动作而制造假冲突。

每LP保存原native返回、exact rational潜值与稀疏dual。lambda≥0，每vertex的bad+lambda/best−lambda净流精确为0，全部约束lambda之和为1（含delta cap），则sum(lambda*b)为delta上界。dual support进行一次小精确有理平衡，独立审计只核对证书/覆盖，不重solve。全根exact gap>EPS且ACTIONS/EPS选optimal为strict_feasible；全部剪枝叶上界<0为weak_infeasible；存在0上界且无strict见证为no_positive_margin。后者不自动证明弱边界可达或实际并列策略绝不可能，只有全根gap≥0的实际潜值可留weak_witness。solver失败/证据不一致为执行HOLD并保留付费记录。

另记录SOURCE/TARGET不同tuple交集、target-only tuple及逐目标根未见tuple。此为来源学习的覆盖信息，不是新Gate，也不把oracle标签拟合出的潜值当来源学习或迁移收益。旧V179正均值收益及成功概率下降原样继承。

冻结协议/实现/纯测试/wrappers原字节后，复制V180 stage_checks/run/problems/summary四输入，全部preparing。记录lift、LP、稀疏矩阵、symbolic平衡、评价、读取和纯测试成本及V180继承链。独立分析重建tuple lift、incidence约束、exact潜值评价、dual与全部分支覆盖；旧标签和goal语义不重新计算。输入字节分析比对一次、源码stage比对一次，不加hash。中途产物仅reports/v181_runtime_tmp与reports/controlled_predictive_shared_feature_capacity_v181。

下一步：若任意共享g仍冲突，优先补充遗漏的rank/布局/转移信息；若共同容量允许，则实施仅SOURCE训练的非线性完整后果模型，并验证其迁移。固定旧标签下增加采样或换损失不能消除已证实的信息冲突。

限制：旧有限H3根、固定后续教师、已暴露目标；正容量不是可学习性、有效采样效率或一般战略学习的证据，负容量只约束本轮六phi+首reward的共享评分。保留原H2、U005 FAIL、U006未启动。
