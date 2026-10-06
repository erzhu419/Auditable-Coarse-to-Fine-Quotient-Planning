# V244冻结：返场goal候选坏核与全部当前证据的相容性

问题：V243有效但阶段失败。ONE_WAY返场24例全部包含未获证的goal SHORT→DETOUR_RETRY。本阶段固定这24个留存终态，区分canonical查询区域的候选反例能否同时满足其他已付观测约束。使用ONE_WAY在线基线；不读取results、laws、真概率或最优策略，不新增观测、随机种子、优化调用，不重新评分旧目标，不改变旧Gate或启动U006。

队列按life0/1/2、index升序枚举全部ONE_WAY A_RETURN终态goal选择SHORT且对DETOUR_RETRY比较未获证者，必须正好24条、每life8条。输入为V243 complete=true、完整审计valid=true的records/profiles/source_records/interfaces；旧证据保持不动。纳入当前终态之前实际揭示的数据，不追用后续目标或其他臂数据。

每例只生成一个候选。若原certificate为bad_null_mle，使用留存完整核；否则在global_likelihood_dual的有限leaf中选log_bad_likelihood_upper最大者，精确并列取首叶。用原乘子λ、行ν及系数a恢复S/D各概率k/(ν−λa)，再归一化；R采用原retry_likelihood.probability，不能采用松弛gap_endpoint。无合法恢复（free_simplex、非正分母或零行）则记录unknown，不增加起点、改用另一leaf或重新求解。恢复点不被称为原优化器的primal或最优点。

固定STRICT_GAP=0.050001。goal差值为sc−dc+4d+u(4q−rc)−4s，令s=[sc−dc+4d+u(4q−rc)−STRICT_GAP]/4，只做一次代数修复S；D/R保持恢复值。修复s超出[0,1]则不可用，不裁剪或重试。合法simplex且精确gap>1/20的核才可作为坏核。

每个合法候选依次精确检查：canonical S_D_FULL_R@960、V235全部8个query family@960（用同一终态原生A计数、原Jeffreys归一化、同一全核的相容投影）；原执行joint_constraints中的所有完整算子行事件，逐条保持原threshold与counts/source/pool/member标签（来源及池720，member8640）。执行三分类行使用完整Dirichlet区域，不能用单变量外包区间代替。阈值不相乘、不另开覆盖预算。8族查询与原执行事件的交集沿用每life/arm查询.05＋执行.05的合并上界.10，非整个cohort的.10。

状态：canonical外或无法构造候选为unknown；canonical内但其他事件排除此候选为paid_constraints_reject_candidate；严格坏核同时位于8族及全部执行事件为full_region_bad_witness。第二种只排除一个固定点，不证明整个坏零假设为空；第一种不证明认证充分。第三种证实现有完整区域仍容纳错误排序，但不证明其他统计方法或预算不可能。

独立审计不导入V244 producer/core：从来源increments和各臂paidbatch重建ONE_WAY原生池、member与事件；复算24队列、候选leaf选择/恢复/修复、全部8族及完整执行事件的精确M≤T L，不调用world或优化器。须核对无后续/跨臂观测并保持原冻结行。producer、审计、必要的因果专项测试及本方案在运行前留存源码，结果生成后只修可达的实现错误，保留首次失败日志。

本阶段完成条件是24例状态留存、独立valid=true，不要求正结果，不授予查询证书或宣告新算法通过。报告按状态和life给出数量、被排除事件类别、主瓶颈结论与一个后续动作。若完整域内仍有坏核，则进一步检验针对联合坏假设的获取轨迹；若候选被排除，只将认证接口浪费信息作为待全域证明的线索。V243的48/72、阶段FAIL和旧Gate保持不变。
