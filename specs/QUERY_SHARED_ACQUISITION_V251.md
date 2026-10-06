# V251冻结：按未获证类型分配共享证据，单独检验停止

V250 complete且独立valid。八个均匀方案返场均48/72；192个未获证返场查询的真实终态regret全部0。两个方案晚B27/36但全费用48384，高于V249的47792。本轮改变证据获取对象，停止均匀配额搜索；不改原Gate、证书或U006状态，也不将手写获取规则称作一般战略学习。

三组UNIFORM_SHARED、QUERY_FIXED、QUERY_SHARED；life0/1/2每组72个A24→B24→A_RETURN24目标，总648决定。全部使用ONE_WAY、原V231普通获取/停止/WAIT，member cap384、batch16、总预算14144/17072/17168、来源4608/life不变。各组共享获取上限4224=A3072+B1152，从开始完整预留。

UNIFORM_SHARED在index3之前，对A每原生类型S/D各512，固定耗3072。另两组同样仅在index3之前获取原生A的S/D，使用下面的查询驱动规则；不增加后续A补采checkpoint。本轮所有组在index30的begin_b之后、目标之前对B每类型已声明改变的行固定补384，合计1152，隔离A分配与停止的影响。A证据进入切换快照，仅向未变B行继承；返场仍无B反向合并。

A辅助查询清单固定为3个类型×4个公共cost：(low,17/20)、(low,19/20)、(high,17/20)、(high,19/20)。只用当前已付原生池point_counts→原Jeffreys posterior→原pure vectors/queries→原online_joint_query_v242.certificates，对每cost三查询的全部替代AND。不调用执行规划、不创建member或执行事件，不使用未来目标身份序列、旧失败类型、真核、预测评分。该公共清单也覆盖未来A_RETURN的cost；B结果仍需完整生命周期实际检验。

两QUERY组初始计算全部12项辅助查询。每批16后只重算被更新类型的4项；其余类型计数未变。任一cost未全ready的类型为当前未解决类型：先选其A共享付费总量最少者，tie类型编号；再选其S/D共享付费最少行，tie S在D之前。QUERY_SHARED在所有类型/所有cost全ready时立即停止，或到A3072上限结束。QUERY_FIXED使用相同规则，但all_ready时继续对全部6个(type,S/D)行按共享付费最少、tie(type,operator)均衡续采，直到用满3072；每批仍重判，若再次出现未解决类型则恢复集中规则。双方至首次all_ready的真实补采历史应完全相同。辅助ready只用于当时的获取决策，后续普通目标仍原make_plan重判，不假定永久ready。

每阶段留存cap、实付paid、未付预留pending和已释放released，满足paid+pending+released=4224。A结束时释放未用A额度，B1152保持pending直到30实付。普通目标available=总预算−4608−普通历史−paid−pending；不能把已释放额度扣除，也不能重复扣实付。A期来源实付3456、未来B来源预留1152独立记账；后续来源实付4608。最终完整费用=4608+普通总费+实际共享费，不超过逐life预算。

新source/target/probe基数295000/296000/297000。来源seed=source_base+(life*6+slot)*3+op_index；目标seed=target_base+(life*78+index)*3+op_index；共享seed=probe_base+(life*6+context_slot*3+identity)*3+op_index，A/B slot0/1。各组同潜在流、仅读取并支付各自实际前缀；A来源384/op/type，B128/op/type，物理来源每life生成一次但每组承担全费，B计数只在30进入规划状态。

全部648目标与所有辅助查询决定冻结后才真核评分。辅助查询单独留存真实regret，已certified且regret>1/20记false_aux_query_certificate；不能把辅助查询造为执行记录。48查询事件/阈值960、执行720/720/8640、query.05+execution.05保持原样；辅助重复读取/可选停止不reset、不新增family事件。上界.10仅为每life/arm完整过程，不能宣称是整个三组cohort的联合覆盖或条件覆盖。

冻结11项资格：QUERY_SHARED晚B≥27/36、返场≥54/72；分别对QUERY_FIXED、UNIFORM_SHARED要求晚B、返场及全周期joint不下降(6)；完整观测费用≤QUERY_FIXED、严格<UNIFORM_SHARED(2)；所有组目标及辅助查询的错误证书、错误不可达/目标上界、风险违例均0(1)。分配作用由QUERY_FIXED−UNIFORM比较，停止/额度释放作用由QUERY_SHARED−QUERY_FIXED比较。失败不追加配额、候选、种子或修改Gate。

9个life×arm独立冷缓存任务，最多9进程。采样前留存源码/协议；完整来源、目标逐批/终态计划、辅助预览与决策、每批共享流/池更新、停止与释放账本和全部proof profiles保留。模型process CPU包括辅助查询与共享选择、原规划/获取/池更新/初始化；普通acquisition是planning子集，不重复加总。实际观测、写入和总耗时单列。独立审计复算辅助策略/证明引用、选择/停止/释放、全部目标及真核评分，不调用新producer或优化器。

测试针对已获证类型永久锁定、均衡续采不重新判断、辅助伪造member/执行事件、释放额度仍被扣/B预留被花掉、共享流重读/非配对、辅助或目标提前真核评分以及模型CPU漏计。范围是已知类型/变化接口下的三固定布局、新采样流；S/D行限制与原证书的可达性仍是待检验假设。
