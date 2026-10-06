# V183：用来源组留出的行动效用选择容量控制

V182 已能零误差插值来源完整行动差，但目标效用比SHARED低0.035632。本轮固定表示，仅检验来源选择的L2正则化能否改善泛化。SOURCE47/TARGET24、12/6设计组、精确H3后果、后续教师goal_1_risk_1、首reward及R−F+S、ACTIONS与EPS、旧基线均保持。直接复用已审计layout_features缓存，不重新swipe、扩表示、核算goal标签或抽样。

预先固定lambda顺序[0,0.0001,0.001,0.01,0.1,1]。12个来源设计组按source_id排序，以偶/奇序号形成原两折。每折用另一6组训练，仅拟合组构建词表、动作根支持及观测动作对连通图；留出组不参与任何参数或词表构建。原六aggregate尺度不变，cell token权重1/4，水平/垂直token权重1/sqrt12，未见token零贡献。支持阈值4、单合法动作与最大首reward回退保持。

完整continuation行动对标签为([R−r,F,S]_a−[R−r,F,S]_b)，每根全部合法行动对权重和为1。目标为每拟合根平均weighted三分量SSE+lambda*||W||²，无截距。对raw weighted X/Y作一次SVD；lambda>0用s/(s²+N_fit*lambda)，lambda=0按eps*max(X.shape)*s_max保留奇异值并作最小范数解。每折复用同一分解产生六组系数，总计两折分解与全SOURCE选定强度分解三次、13次系数滤波。各candidate保存完整三分量残差与留出选择；fold设计以cache/vocab/support/sparse pairs保存一次，不输出dense X/Y或U/V。

用固定预测完整向量加回首reward一次，按R−F+S及原EPS选择真实可执行动作。lambda评分仅为该动作在留出SOURCE的精确真实效用，先每设计组取根均值，再12组等权平均；不用训练SSE选lambda。EPS内相同评分保留lambda表中较早项。选定后全SOURCE唯一refit，冻结模型及SOURCE/TARGET全部选择后才读TARGET完整标签。SOURCE选择得分属于同一来源上的模型选择，非独立确认。

输入按原字节冻结：V182 stage_checks/run/roots/choices，以及其inputs/inherited/source_labels共五项preparing；models/choices冻结后target_labels阶段第六项V182完整labels。不复制或重拟合旧大型模型，保留旧LAYOUT/SHARED/RAW/STRUCTURE/ONE选择及既有成本链。主要报告TARGET RIDGE−ONE、RIDGE−LAYOUT、RIDGE−SHARED和剩余oracle regret，保留完整R/F/S与逐根改变；SOURCE组等权、TARGET根等权，另一权重也保存。无新Gate、目标调参、追加lambda或随机CI。

协议/实现/测试/wrappers在真实读取前按字节留存，BLAS/OMP线程1。独立分析只重建新增来源选择与正则解：lambda0用独立lstsq，正lambda用X.T solve(X X.T+N_fit*lambda I,Y)，总计13个审计算法调用，重建SOURCE词表/支持/选择/效用，复用已审计cache与基线统计。输入字节比较一次、源码stage比较一次，无hash。记录分解、滤波、矩阵、缓存/编码、选择、读取与纯测试成本，异常保留付费记录；执行不一致为HOLD，负科学结果原样保存。文件仅reports/v183_runtime_tmp及reports/controlled_predictive_source_regularization_v183。

下一步由迁移结果决定：若容量控制改善固定目标，再开展新来源/棋盘确认；若仍无收益，优先改变局部参数共享或增加覆盖，而非追加目标驱动超参搜索。

限制：固定有限H3根和已暴露目标，不构成一般战略学习或独立新棋盘证据。lambda grid和两折是本轮固定实现选择。保留H2、U005 FAIL、U006未启动。
