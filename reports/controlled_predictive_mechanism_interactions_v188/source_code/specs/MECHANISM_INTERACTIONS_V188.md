# V188：共享机制特征的低维交互

V187 已覆盖所有目标token，但共享表示未改善主要对照。本轮检验机制的联合效应：固定 SOURCE143/36组及完整后果损失，在原六个动作方向共享特征上加入低维二阶项。x=(goal_reached,vacancies,row_positive_equal,col_positive_equal,row_goal_pair,col_goal_pair)，原六列及尺度不变。

INTERACT 增加20列 z_ij=x_i*x_j/sqrt(b_i*b_j)，按0≤i≤j<6字典序，排除(0,0)，因为二元goal的平方与原列相同。b=(1,16,12,12,12,12)为4×4棋盘固定物理上界；不用来源或目标数据计算尺度。总26列，无截距、词表、未知token或自适应基函数。一次从冻结六列缓存导出26列，不新增物理swipe。LINEAR 仅使用原六列，采用相同来源、分组、损失和选参规则，作为交互项的必要对照。

两种模型均沿 V183 的全部合法动作对三分量 tail 差拟合：先从完整 R 中扣一次首奖励，每根每对权重1/动作对数，weighted SSE/N+λ||W||²；N包括无动作对的根。推理只加入一次可观测首奖励，以 R−F+S 选择。支持阈值4、连通性、回退、DOWN LEFT RIGHT UP 顺序与 EPS=1e−12 不变。相对后果向量不作为校准事件概率。

固定 LINEAR→INTERACT 次序，各按36来源组排序奇偶分两折、各留出18组。网格沿用0、0.0001、0.001、0.01、0.1、1，以实际留出选择的三分量效用按组等权选强度；EPS内并列选较早网格。每臂两折+完整来源共3 SVD、12折内滤波+1最终滤波，共6 SVD、26预测器；不重拟旧对照、不新增参数或在目标后更改规则。数值后端复用已审计 V183 分解/滤波。

模型和两种强度全部冻结后才生成 TARGET96：四副本×24，seed=1880200+24*replica+index，名字 v188_target_r{replica:02d}_{index:02d}，horizon=3。沿 V69：16个 randint(1,10)，24条边先12水平再12垂直，index边两端置1+index%10，其余格sample(index%3)置零。缓存可观测特征并冻结 INTERACT、LINEAR、V185 RIDGE/LAYOUT/SHARED、原OLD_SHARED/ONE、FALLBACK 全部选择，随后才获取完整标签，不替换或追加棋盘。

标签复用已审计 V184 V69 FULL、goal1/risk1冻结教师和精确 R/F/S，每棋盘上限200000具体状态。新增96个核/规划，保留紧凑教师策略、native/canonical标签与成本，不保存大核，没有新来源游戏、物理随机样本或原生规则更新。

主要比较 INTERACT−LINEAR、INTERACT−RIDGE、INTERACT−OLD_SHARED；同时保留所有对照、ORACLE、完整 R/F/S、遗憾、错误增减、每根正负效用、集中度及四副本。独立审计固定产品尺度/26与6列缓存、来源分组/设计/支持、26个系数和两组选参；λ0用独立最小范数lstsq，正λ用列正规方程。沿已有1e−10系数容差先认证留存数组，再独立编码评分，保留实际EPS选择历史。旧模型与已审计物理后端不重拟或重复积分。不设新科学Gate，不把完整性PASS当作一般战略学习成功。

读取真实输入前冻结协议/源码/测试/wrappers，main/audit各一次，线程1；源码与六个输入各比较一次，无hash。输入为 V187 stage/run/source_labels 及其继承的 expanded_models/baseline_models/learned_rule；不读旧目标标签。留存全部新学习、缓存、预测、标注与独立解成本及旧成本链（包含V187 posthoc的独立成本引用）。失败保留实付工作和已完成根。

中途文件仅 reports/v188_runtime_tmp（含pytest临时目录），结果仅 reports/controlled_predictive_mechanism_interactions_v188。限制：固定教师、有限H3来源/目标及根动作评估；这一结果不单独证明多步策略执行或一般episode学习。保持H2、U005 FAIL、U006未启动。
