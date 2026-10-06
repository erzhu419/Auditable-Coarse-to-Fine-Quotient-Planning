# V186：固定表示的最优动作排序

只改变 SOURCE 拟合目标，检验布局模型的误差是否来自优化完整向量的平方误差而非实际动作选择。SOURCE 固定为 V185 的143根、36组；词表、六个聚合列、40个布局token、权重、支持和 λ=0.1 固定为 V185 RIDGE。不追加来源，不交叉验证或搜索参数。完整 R/F/S 来源标签保留。

动作顺序 DOWN, LEFT, RIGHT, UP，EPS=1e−12。每根依此顺序选择完整标签效用 u=R−F+S 的一个最优代表 a*，只比较 Δu>EPS 的严格次优动作 b；最优并列不构造约束。K_r 为该根次优动作数，N=143，包括 K_r=0 的根。D_i=φ_a*−φ_b，t_i=Δu_i−Δr_i，w_i=1/K_r。无截距：J(β)=Σ_i w_i max(0,t_i−D_iβ)²/N+0.1||β||²。推理评分为可观测即时奖励 r_a+φ_aβ；只预测标量效用，不生成预测 R/F/S 分量。合法动作、支持阈值4、连通性和回退沿用 V182；未知token为0。

一次 scipy L-BFGS-B，零初始化，jac=True，maxiter=1000，maxls=50，ftol=1e−15，gtol=1e−10。终态 gradient_inf≤1e−7 才接受，保存全部目标/梯度调用及一次显式终态计算；不满足则 HOLD，保留已支付成本，停止目标棋盘生成，不重试。强凸性给出目标差上界 ||g||²/(4λ)。

独立审计重建来源设计，用对偶非负最小二乘而非第二次原始拟合：H=N/2 diag(1/w)+DDᵀ/(2λ)，H=LLᵀ，nnls(Lᵀ,solve(L,t),maxiter=10000)。α≥0，β_dual=Dᵀα/(2λ)，dual=tᵀα−N/4 Σα²/w−||Dᵀα||²/(4λ)。冻结 primal−dual∈[−1e−10,1e−9]、KKT违反量≤1e−7、原始 gradient_inf≤1e−7、||β−β_dual||₂≤max(sqrt(max(gap,0)/λ),(||g_primal||₂+||g_dual||₂)/(2λ))+1e−8。梯度距离项由强凸性及三角不等式得到，避免近收敛时目标相减舍入使系数界误拒绝；对β_dual额外计算一次损失/梯度并计费，无第二次优化。用对偶认证后的原始β独立重算目标评分/选择，保持 EPS 并列规则。

训练完成后才生成 TARGET96：四副本×24，seed=1860200+24*replica+index，名字 v186_target_r{replica:02d}_{index:02d}，horizon=3；沿 V69 生成16个 randint(1,10)，边先12水平再12垂直，index 边两端置1+index%10，其余格 sample(index%3) 置零。禁止替换、追加或按标签筛选。一次缓存可观测动作特征，然后冻结 RANK、V185 RIDGE/LAYOUT/SHARED、原始 OLD_SHARED/ONE 和即时奖励 FALLBACK 全部选择，之后才获取目标标签。

目标标签复用已审计 V184 的 V69 FULL 精确后端：每棋盘上限200000，goal=1/risk=1，完整多步教师和精确 R/F/S 分数。只增加96个精确核/教师规划，没有新物理随机采样、来源游戏或原生规则更新。保留紧凑教师策略、native/canonical标签及逐根成本；本轮不重复旧物理核整合审计。

主要对比 RANK−同来源 RIDGE、RANK−OLD_SHARED；同时保留 LAYOUT/SHARED/ONE、FALLBACK、ORACLE，各根/四副本的真实 R/F/S、效用、遗憾、新增/修复错误、正负收益和集中度。不设新科学 Gate，不把完整性 PASS 解释为一般战略学习成功。

读真实输入前快照协议/源码/测试/wrappers；main/audit各一次，线程1，源码和六个输入分别比较一次，无hash。冻结输入：V185 stage/run/source_labels/models、V185继承的 baseline_models/learned_rule。模型旧成本引用 V185 run/analysis 链，不重拟旧模型。新拟合1个预测器及独立对偶解全部计费。中途仅 reports/v186_runtime_tmp，结果仅 reports/controlled_predictive_action_ranking_v186。H2、U005 FAIL、U006未启动不变。
