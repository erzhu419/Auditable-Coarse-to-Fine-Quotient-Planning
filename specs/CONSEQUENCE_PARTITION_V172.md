# V172：由配对行动后果学习状态划分（冻结协议）

承接V171科学FAIL。当前H2仍是V135冻结的V134 SINGLE价值+两层规划；H2/U005 FAIL/U006未启动状态不变。本轮主攻表示学习，不修改教师、Gate或旧数据。先验证首动作选择所需信息，暂不部署自主整局或宣称Markov商成立。

只继承V171已审计TRAIN的128个root、1880条强制首动作完整后果；旧VALID/EVAL及H2自选续局转移均不作表示标签。四历史分别训练，禁止混合不同教师分量。每root保留4个配对suffix以及全部合法canonical动作的reward/failure/success；首步确定性奖励从reward标签扣除并保留为推断时的数值参数。非法动作不补零。

固定学习机制：在每个leaf中最小化联合合法动作的三分量配对差残差。每root权重1、每suffix权重1/4、每合法动作对等权归一；单合法动作不提供比较标签。Laplacian最小二乘给出各连通动作分量中的零和相对向量，不能称绝对成功/失败概率。分割语法为CURRENT D4 canonical棋盘16个cell的rank≤threshold0..9；全局贪心最大正损失下降，最多16leaves，每child至少8个root与2个SOURCE游戏。动作支持至少4个root，当前合法动作需在leaf比较图中连通，否则用该root已记录的H2首动作；单合法动作直接执行。gain≤1e-12不分割；gain/动作的1e-12并列按node/cell/threshold、canonical动作字典序固定。四个模型模式为PART_EARLY（旧32roots/历史）、PART_LATE（旧+新96roots/历史）、COARSE_LATE（旧18类语法，同晚期数据）、ONE_LATE（无分割，同晚期数据）；估计器、合法动作和支持规则完全相同，仅划分与EARLY数据年龄不同。

新TRAIN_SOURCE：每历史8个ordinary两随机tile初态完整H2游戏，共32局。每局预定8个中段分位root，step=(slot+1)×n//9，slot0..7；不按分歧、回报或胜负挑选。最多256新root；全部合法首动作×4suffix，共至多4096新TRAIN完整分支，首动作后执行自己的冻结risk1 H2到终态。拟合PART_LATE/COARSE_LATE/ONE_LATE时，只用这些强制首动作终局向量与旧TRAIN标签，不计续局步为新增独立root。所有16个模式/历史模型冻结后才开展新VALID_SOURCE。

新VALID_SOURCE：同样32局、每历史8个全新SOURCE随机流游戏及8个分位root。在任何VALID首动作标签采集前，仅按canonical具体棋盘与全部TRAIN root的精确相等关系排除已见棋盘，保留其已付SOURCE成本，原始排除记录留存，不补root或游戏。每个预定SOURCE簇至少有一个未见root，否则本轮HOLD。先保存全部模式和H2的选择，再采集未见root的全部合法动作×4新配对suffix，至多4096完整VALID分支，首动作后同teacher H2。

新SOURCE与全部分支分别记录真实转移、RNG、swipe、教师加载/决策、root特征、模型学习/选择、回退和继承成本。没有随机模型内采样、新神经参数更新或额外精确终局教师。SOURCE运行与合法首动作的确定性swipe属于已付获取/计算。旧1880分支及V171全部成本继续引用，不当本轮新采样；已有compact标签足够拟合，不重读其全部续局tapes。

主比较为PART_LATE−COARSE_LATE的VALID配对实际效用；推进还要求PART_LATE−H2的CI95下界>0，两个条件均通过才提名后续组合验证。次比较PART_LATE−ONE_LATE、PART_LATE−PART_EARLY、COARSE_LATE−H2。预测诊断保留完整动作对三分量MSE、实际选择差异及支持/回退；不按预测MSE晋升、不用TEST标签argmax作真实最优oracle。各root四suffix均值→SOURCE游戏内root均值→每history八个SOURCE簇均值与簇级均值方差→四既有history等权汇总，正态95%区间；不把root、suffix或动作当独立游戏。

BASE=17200000000。TRAIN_SOURCE seed=BASE+10M+life×1M+replica0..7；TRAIN=BASE+20M+life×1M+replica×100K+slot×1K+suffix0..3。VALID_SOURCE用+30M，VALID用+40M。动作/方法不进入seed；共享uniform后缀形成配对，不意味着动作后的具体棋盘相同。每新物理游戏max_steps=8192，p_four=.1。新采样上限64个SOURCE+8192个分支=8256游戏、67,633,152转移；实际roster在各阶段采样前冻结。

任何required SOURCE/TRAIN/VALID缺失、重复、cutoff/null、身份或向量不一致均留存已付成本并HOLD；不补跑/补样，不把不完整统计记为科学FAIL。独立审计只重放本轮新SOURCE/分支、重建继承compact标签和新配对数据、树/leaf/选择以及SOURCE簇统计，不重复重放已经解决的旧V171 tapes。源码/协议/测试与运行wrapper原始字节在采样前留存，结束后只比较一次，不新增hash。

所有中途文件位于项目worktree reports/v172_runtime_tmp/ 与 reports/controlled_predictive_consequence_partition_v172/；无服务器下载。通过仅证明新H2访问棋盘、明确H2续局下的首动作信息改善，尚不能证明后继模型可组合、长期自主控制、一般迁移或样本效率。
