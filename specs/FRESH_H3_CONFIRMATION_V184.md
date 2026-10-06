# V184：冻结模型的新棋盘 H3 确认

V183 的平均改善几乎来自一个旧目标根。本轮只检验迁移是否成立，不修改表示、系数、λ、词表、支持、回退或教师。RIDGE 唯一模型为 V183 全 SOURCE 拟合的 λ=0.1；LAYOUT、SHARED、ONE 为 V182 留存版本。首奖励仅加一次，完整效用 R−F+S、目标 rank11、spawn 4 概率1/10、reward/2048、ACTIONS/EPS 沿用。

队列预定四副本×24根，无替换、追加或按结果筛选。replica=0..3、index=0..23，seed=1840200+24*replica+index，名称 v184_h3_r{replica:02d}_{index:02d}。每根 Random(seed) 生成16个 randint(1,10)；24条边依次为12条水平、12条垂直相邻边，取 index%24，将两端改为 rank=1+index%10；再从其余14格 sample(index%3) 置零。horizon=3，完全沿用 V69 的结构生成方式，只更换种子。设计组为 FRESH_REPLICA:{replica:02d}。生成操作发生在协议源码快照及模型冻结之后。

先观察全部96棋盘并冻结四模型及可观测首reward回退的全部动作；其后才能构建新标签。一次计算 rank/layout afterstate 特征并缓存六 aggregate；使用既有评分代码，无训练、候选搜索或来源扩充。五项输入在 protocol_frozen 阶段读取：V183 stage/run/models，V182 models，V69 learned_rule。只留存 V182 models 的 LAYOUT/SHARED/ONE 完整子模型，避免复制无关 RAW/STRUCTURE；独立审计从原文件抽取相同子模型比较，无哈希。

每棋盘复用既有 V69 FULL 构建器，具体观察上限200000；使用同一精确分数转移及原 plan(goal_bonus=1,failure_penalty=1,reward_weight=1)，保留原 float fsum、strict > 和 action 顺序。V177 精确分数评估全部首动作，其后遵循该原生教师。留存每根完整 R/F/S 分数、原生到规范动作映射、全部 active(h,board,action) 教师决策及各项成本；不落盘庞大完整核。失败保留已付成本和完成根，不更换种子。核生成/规划/标签是本轮新增工作；随机环境样本、完整来源游戏、拟合和原生权重更新为0。

主要比较96根等权 RIDGE−ONE 和 RIDGE−SHARED，另报 RIDGE−LAYOUT、完整分量、oracle regret、每副本24根均值、改善/退化根及最大正收益占全部正收益比例。全部正负结果公开；无目标选择、事后阈值、随机CI或新增科学Gate。全队列正收益和四副本均正收益各自描述，不能互相替代。

新增标签由独立 V66 swipe/精确 spawn 后端按留存教师重算；新增统计独立重建。旧教师算法、特征和来源拟合已审计，保持复用。协议/源码/测试/wrappers 在真实输入与新棋盘生成前留存，输入比较一次、源码比较一次。纯测试仅合成小棋盘与模拟队列，不生成真实96根。main/audit 各一次，线程1；执行不一致为HOLD，负科学结果保留。中途文件仅 reports/v184_runtime_tmp，结果仅 reports/controlled_predictive_fresh_h3_confirmation_v184。

下一步取决于结果：若优势不能跨副本保持，不再围绕旧24根加超参，转向来源 episode/后果覆盖的实质扩充；若稳定，再推进超出H3的学习评估。限制：新有限H3棋盘、预设结构分布、固定后续教师，不证明一般战略、长episode或采样效率。保留H2、U005 FAIL、U006未启动。
