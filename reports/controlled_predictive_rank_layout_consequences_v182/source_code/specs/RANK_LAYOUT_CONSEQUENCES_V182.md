# V182：保留棋块等级与局部布局的共享完整后果

V181 的逐特征顶点证书证明六个聚合特征不足以跨棋盘一致表达正确行动偏好。本轮实际学习 richer afterstate 表示，不再调六维函数形状。固定 SOURCE47/TARGET24、12/6设计组、被排除的 ordinal15 H2、精确H3完整R/F/S、goal rank11、首reward/2048、后续教师goal_1_risk_1、效用R−F+S及原生权重不变。

每个canonical当前棋盘只执行四个确定性swipe；合法afterstate以唯一纯旋转将首动作转向DOWN，无反射、spawn或oracle输入。保留原六个aggregate及其尺度。新增40个局部token：16个cell(index,rank)，12个horizontal(start,index_rank,next_rank)，12个vertical(start,index_rank,next_rank)。rank包含0，按原16格相邻关系，不压缩空位；每个token保留位置。cell权重1/4，水平与垂直各1/sqrt(12)，使每族one-hot特征的平方范数为1。只用SOURCE合法afterstate构建排序词表，列顺序为六aggregate后接词表。未见TARGET token在所拟合模型中贡献0，记录覆盖数量，不使用目标观测扩词表或拟合，不因此改变旧fallback。

按原每根全部合法动作对、每根总权重1，回归完整continuation差([R−r,F,S]_a−[R−r,F,S]_b)。唯一np.linalg.lstsq(rcond=None)最小范数解，无截距、ridge、超参选择、CV或新目标拟合。预测相对完整向量，F/S不裁剪、不视为绝对概率；首reward只加一次。ACTIONS DOWN/LEFT/RIGHT/UP、EPS1e-12、每动作至少4不同来源根及同一观测动作对连通分量、observable首reward回退规则不变。单合法动作直接选择。

只训练LAYOUT，V179 SHARED/STRUCTURE/RAW/ONE模型及选择原样继承。先按字节冻结协议、实现、测试与wrappers，复制八个输入：V181 stage_checks、V179 stage_checks/run/roots/models/choices，以及V179保留的独立source_labels，全部preparing；模型与全部选择冻结后，target_labels阶段才复制V179完整labels。旧目标已暴露，读取次序不构成新鲜确认。不重算旧kernel、旧标签、旧模型或56个goal标签。

主要诊断TARGET LAYOUT−ONE、LAYOUT−SHARED与剩余oracle regret，另保留RAW/STRUCTURE比较；SOURCE设计组等权、TARGET根等权，同时保留另一权重及逐根完整向量、动作和regret。记录SOURCE训练residual与source-only词表的逐目标动作已见/未见token数量。不设新Gate、不因本轮结果改变表示或拟合设置，无随机CI。若来源拟合改善而目标退化，优先解决共享和泛化；若改善迁移，再做独立来源分组与新棋盘确认。

记录新特征、词表、矩阵/唯一求解、选择、读取、纯测试、继承链成本；无新物理样本、SOURCE整局或原生权重更新。wrappers固定BLAS/OMP线程为1。独立分析用另一swipe与手写旋转重建表示、SOURCE词表，再独立SVD复现weighted完整向量回归、选择与统计，只审计新增学习部分。原输入字节比较一次，源码stage比较一次，无hash。执行不一致为HOLD，科学负结果保留。中途文件仅reports/v182_runtime_tmp及reports/controlled_predictive_rank_layout_consequences_v182。

限制：旧有限H3根、已暴露目标及固定教师；来源词表未见模式的零贡献与最小范数解是固定实现选择。局部表示的学习收益不能证明完整episode效率或一般战略学习。保留H2、U005 FAIL、U006未启动。
