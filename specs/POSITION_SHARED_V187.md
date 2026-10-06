# V187：跨位置共享的秩与邻接关系

V186 的排序目标未优于同来源 RIDGE 和 OLD_SHARED。本轮只重构布局表示，恢复已审计的完整三分量后果拟合与来源组选择规则，检验跨位置共享是否能改善迁移。SOURCE 固定为 V185/V186 留存143根、36个设计组，完整 R/F/S 与可观测缓存不变，不增加来源标签。六个 aggregate 列保留。

每个动作仍取 V182 原方向旋转到 DOWN 的 afterstate 缓存，16个 cell、12个 horizontal、12个 vertical token：仅删除绝对格子索引，即 cell=(cell,rank)，邻接=(axis,first_rank,second_rank)。保留有序秩对、两个轴和零值，不作镜像、排序秩对或再计算物理 swipe。每发生一次 cell 加0.25，每发生一次邻接加1/sqrt(12)；相同token重复发生必须累加，不能覆盖或去重。六个aggregate尺度不变。词表与支持只来自训练来源，未知token为0；覆盖按40次发生统计。每折只使用该折训练组建词表，完整拟合只使用143来源根。

损失沿 V183：合法动作全部成对，首奖励从 R 中扣除一次后拟合 tail 三分量差；每根每对权重1/该根动作对数，weighted SSE/N+λ||W||²，N包括单动作根，无截距。参数网格固定为0、0.0001、0.001、0.01、0.1、1；排序36组按偶/奇分两折，各留出18组。选择实际留出动作的 R−F+S，组均值等权，EPS=1e−12，并列选网格较早者。三次 SVD（两折与完整来源），12个折内滤波模型和1个最终模型，共13个新预测器；不重拟旧对照，不额外拟合λ=0或SHARED。原数值后端复用，完整预测 R 加入可观测首奖励一次，动作/支持/回退及 DOWN LEFT RIGHT UP 顺序沿用 V182。

完整来源模型与参数冻结后才生成新 TARGET96：四副本×24，seed=1870200+24*replica+index，名字 v187_target_r{replica:02d}_{index:02d}，horizon=3。同 V69：16个 randint(1,10)，24条边先12水平再12垂直，index 边两端置1+index%10，其余格 sample(index%3) 置零。先缓存动作可观测特征并冻结 POOL、V185 RIDGE/LAYOUT/SHARED、原 OLD_SHARED/ONE 与 FALLBACK 的全部选择，之后再获取标签；不按标签追加或替换棋盘。

标签复用已审计 V184 V69 FULL 后端、goal=1/risk=1 的冻结教师及完整精确分数，每棋盘上限200000具体状态。新增96个核/规划，保留 native/canonical 三分量、紧凑教师策略和逐根成本，不保存大核，没有新物理随机样本、来源游戏或原生规则更新。

主要比较 POOL−同来源 RIDGE 和 POOL−OLD_SHARED；保留所有对照、ORACLE、R/F/S、遗憾、错误增减、每根正负效用、收益集中度及四副本。独立审计新pool编码/词表/重复累加、三套来源设计、13个系数解、来源选择与新选择/统计；λ>0使用正规方程，λ=0使用独立最小范数lstsq。已审计的旧模型和物理标签后端不重新积分或拟合。数值比较沿已有V185审计规则：先独立解并按已有1e−10容差认证全部13个系数数组，再用已认证的留存系数独立编码/评分SOURCE候选和TARGET动作，严格保留实际EPS并列与选择历史；不增加原始拟合或目标后调整。EPS动作规则不更改。不设新科学Gate，不以完整性PASS宣称一般战略学习成功。

真实输入读取前冻结协议/源码/测试/wrappers，main/audit各一次，线程1；源码和六个输入各比较一次，无hash。输入为 V186 stage/run/source_labels 和其继承的 expanded_models/baseline_models/learned_rule；不读取旧目标标签。留存旧成本链及全部新拟合、缓存、预测、标注与独立解成本。失败保留已支付工作与已完成根。中途只在 reports/v187_runtime_tmp，结果只在 reports/controlled_predictive_position_shared_v187。

此队列只检验已声明的共享表示，收益不能证明一般episode学习或所有位置均可忽略。若新表示不能改善强对照，转向后续动作/风险的组合结构；保持 H2、U005 FAIL、U006 未启动。
