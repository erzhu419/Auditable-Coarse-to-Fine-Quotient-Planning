# V235冻结协议：必要行的联合查询证据

固定V234已审计的24个终态、原策略、费用与真实付费tapes；新增获取0。学习器只用类别和已知任务费用。共同事件每life/arm为48条：8种必要投影×A/B×3已知类型，δ=.05，T=960。reward的WAIT解析获证。方向、两查询和已知费用共享真参数事件。

八族固定为S、D_DEL、Dfull、Dfull+R、S+D_DEL、S+Dfull、S+Dfull+R、D_REC+R。S/R为DELIVERY二分类；D_DEL、D_REC分别合并另外两类；Dfull保留三类。WAIT/SHORT用S；WAIT/RETURN在goal用D_DEL、risk用Dfull；WAIT/RETRY用Dfull+R；SHORT/RETURN在goal用S+D_DEL、risk用S+Dfull；SHORT/RETRY用S+Dfull+R；RETURN/RETRY用D_REC+R。

每个投影行固定Dirichlet(1/2,…,1/2)，即二分类Jeffreys Beta。联合M为各投影行精确混合likelihood之积，L为这些实际投影计数的likelihood。M/L在本臂自己的获取过滤族上为非负supermartingale；两臂使用耦合seed，其他臂目标结果不进入该过滤族。共享来源在每臂仅计入一次。B事件从时间零预声明：变化行只用B，未变行计入对应A来源/切换前A目标，再接B来源/目标；忽略A_RETURN。A事件包含A来源、A目标及A_RETURN。实际顺序为A来源→A目标→B来源→B目标→A_RETURN。只在这条路径上使用联合过程，不推广到任意Cartesian前缀网格。

先执行固定反例诊断：12个V232已接受全核反例，以及3个V234终态矩形内反例。每个仅检查其原chosen/alternative/query的必要族，使用完整各行数量，精确比较M≤960L；不扫描其他族、先验、预算或新反例。不接受的旧反例只是必要诊断，不是新查询证书。主瓶颈6个SHORT↔RETURN风险终态中，5个已有接受反例，另1个保留无留存反例。

若上述5个主瓶颈反例全部被新必要行区域排除，再按同一冻结方案执行完整24例资格。否则本轮停止等价优化器实现，报告仍可行的反例与证据需求。完整资格不调整任何统计参数：以原V232合法对偶/向外80位数值界给坏假设gap≥.05的全域likelihood上界；非线性R仍固定32格。对D_DEL将非交付合并到LOST、RECOVERY计数置0；对D_REC将非恢复合并到LOST、DELIVERY计数置0；未用行计数置0。仅在相应动作差的被合并类别同值时使用此嵌入，分子始终用真实投影的2/3分类混合。该嵌入的全域最大likelihood与投影假设相同，不能把零计数类别当额外观测。

只有M向下界减全域坏likelihood向上界严格超过log960向上界、或坏假设精确为空时，比较才获证。每查询AND三替代动作，再AND三查询。保持原策略；全部证书冻结后才读取V233原策略真regret评分。不得与旧证书事后择优合并。正式诊断/资格各运行一次；未知不等于不可能。

独立审计从原tapes计数，用独立Dirichlet预测递推计算混合，并核对反例严格gap、旧/新必要区域关系；完整资格再审计投影嵌入、合法全域对偶、32格覆盖和汇总。报告修复/退化、主风险阻塞、完整样本量与模型时间，不启动付费生命周期、不重判旧科学Gate。原12个正对照全部保住且旧失败改善才考虑后续获取/执行设计。
