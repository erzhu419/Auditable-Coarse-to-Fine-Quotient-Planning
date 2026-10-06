# V177：精确 H3 后果标签与同一分区学习器

V176 未建立采样方差或成本收益，不追加 block。本轮直接区分采样标签问题与表示/归纳问题：固定短期任务，去除 Monte Carlo 标签噪声，先校准 oracle−ONE 提升空间，再判断同一学习器能否利用它。既有 H2、U005 FAIL、U006 未启动保持。

来源为 V68 RAW 留存完整具体状态 kernel，而非神经编码器预测。48 个原来源根实际上只有 47 个 H3；原 ordinal 15 的 H2 根排除并留存身份，不能重标为 H3。根按原 roster 次序绑定 RAW.roots，核对根层数。设计来源组按原 ordinal//4 固定，共12组，其中一组3根；这些不是12个 SOURCE 整局。每组全部根只进同一折，组字符串排序后交替分两折。目标为 V69 留存24个 H3 FULL kernel；H4 不混入。目标设计组仅用于记录，不作独立样本或确认簇。

所有任务 goal rank 11，spawn rank1/2 概率 .9/.1，奖励 merge score/2048，目标 R−F+S。唯一后续教师为各 kernel 已保存的 goal_1_risk_1 policy。递归求同一策略的完整 R/F/S，每个根对全部合法首动作求真实支持的概率期望；WON=[0,0,1]、LOST=[0,1,0]、CUTOFF=[0,0,0]。本轮只称精确有限 H3 后果，不能冒充整局终态，亦不能将多个查询的最大值拼成一个向量。源码保留 Fraction 概率/奖励；V68浮点 kernel 仅按原生分母<=2560及整数 merge score/2048恢复，误差须<=1e-12，恢复原子数与最大误差记录。

棋盘只按原 D4 canonical_frame 规则变换，动作同步运输。具体首步 reward 保留为参数，叶只拟合配对相对续局完整三向量。exact 数据接口不创建 suffix、seed 或随机重复。每根各合法动作对总权重1，配对标签为去首步 reward 后期望向量差。TREE 完整沿用 V174 PART_UTILITY_UNPRUNED 的准备后搜索、候选特征/支持约束、两折来源等权实际效用目标、贪心并列次序及全数据节点拟合；ONE 同源一次叶估计。MIN_CHILD_ROOTS=8、MIN_CHILD_SOURCES=2、MIN_ACTION_ROOTS=4、MAX_LEAVES=16、EPS=1e-12不变。

两模型仅用来源标签拟合。目标动作先使用目标 roster 的棋盘、合法动作及精确首步 reward 冻结，然后才打开目标 FULL kernel 和后续教师 plans 计算标签。部署沿用 V172：单合法动作直接强制选择，交叉拟合候选仍严格检查4根支持；多合法动作支持不足的回退只能用可观测首步 reward 最大的合法动作，按 DOWN/LEFT/RIGHT/UP 并列。TREE/ONE 共用此规则，不借目标 H3 oracle 回退。记录每个模型的全部预测、支持和回退。

oracle 为同一固定后续教师下合法首动作真实 R−F+S 最大者，1e-12并列按 canonical ACTIONS。保存每根全部标签、oracle动作/完整向量。训练摘要以12设计组均值等权，并另存根均值；目标24根等权。先报告 oracle−ONE headroom，再报告 TREE−ONE、oracle−TREE regret、改善/恶化/值相同根数与支持回退。只有 headroom>EPS 时计算提升空间关闭比例；它可为负，不截断。无 headroom 表示数据不能诊断未学到提升。reuse exact 固定根集不设随机 CI，不将训练两折分数称独立确认。本轮无新增物理样本、SOURCE 整局或神经更新，计算、继承费用、测试、审计与所有失败均留存。

源码、协议、测试、执行 wrappers 在正式拟合前原字节留存，结束只比对一次，无 hash。独立审计另算概率期望、D4动作与奖励绑定、准备后搜索/节点估计、支持/决策、oracle headroom与全部摘要；来源/目标缺失、重复、层数/向量/输入绑定错误为执行 HOLD，不以改组、改门槛或重采替换。中途产物只在 reports/v177_runtime_tmp/ 与 reports/controlled_predictive_exact_h3_v177/，不从服务器下载。

若有 headroom 但精确标签仍未改善，下一步优先修表示/归纳，而非继续补采；若改善，只说明学习器在该无采样噪声短程条件下能利用差异，仍需同目标采样干预和独立长程检验，不能单独认定旧失败由噪声导致。V68/V69 已暴露的短期根只是诊断，不能建立新鲜确认或多回合持续战略学习。
