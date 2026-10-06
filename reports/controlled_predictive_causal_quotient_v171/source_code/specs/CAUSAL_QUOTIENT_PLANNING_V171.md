# V171：战略商状态与可组合后果模型（冻结协议）

继承V170工程完整、科学推进FAIL；保持H2与U005 FAIL，U006不启动。旧程序、协议与结果只读。本轮改变学习对象：显式预测抽象后继分布，并由同一完整后果向量递推决策，不重开终局标量头或动作频次树路线。

活动状态为最高rank{≤8,9,10}×空格{0,1,≥2}×可正合并{否,是}，至多18类；另有WON/LOST。正合并由每行/列去零后的相邻相等tile判断；最高rank≥11优先为WON，满格且无合并为LOST。这是固定有界表示先验，不宣称已发现战略变量或满足Markov/lumpability。每步CURRENT D4最小框架按既有首变换tie，四primitive动作在当前框架中标号与transport；真实合法性四次确定性swipe显式计费，不提供未执行动作的真实终局标签。

只复用V170 SOURCE的16个已审计H2游戏（每历史4个），不读取其TRAIN/FINAL/EVAL终局标签来训练。每来源游戏八个预决策起点step=floor(slot×n/8)，slot0–7，共128roots；不足八步、来源身份/终态不完整则停止。本轮只在这些root的全部合法canonical首动作采集配对新分支，首动作强制一步，然后对应历史自己的冻结risk1 H2直至终局。完整choices/spawn/RNG/counters留存，其他query教师加载与零决策亦计费。

TRAIN每root/合法action四条新后缀；至多2048完整分支。四个独立历史模型分别只拟合该历史的SOURCE和TRAIN。每步观测拟合P(next_abstract_state|state,canonical_action)、边的归一化即时reward均值和终态failure/success事件；全部执行动作均参与，不筛正收益。边按next_state/status聚合，而非按具体棋盘或具体奖励索引。累计真实样本count≥8的模型行才支持动作；这不是置信证书，重复分支的相关性不扩大独立历史数。

V_H2_j(state)记录明确教师j后续下的剩余reward/failure/success三分量均值。SOURCE各步可作H2尾值；TRAIN强制首动作step0不能作H2尾值，只有step≥1进入tail拟合。终态仍作为转换事件参与kernel。未观察或缺必要leaf值保持unsupported，不人工补成功/失败标签。四模型的tail条件性保留，不能把不同教师的分量拼成一个后果。

编译同一模型的depth1和depth3 Bellman表，V0=该模型的H2 tail。一步Q=边的即时三分量+ACTIVE后继V；终态V=0，failure/success事件只计一次。更深V按risk1效用选择一个受支持action后保留其整向量；所有action不支持则提前使用同teacher的学习tail边界。缺ACTIVE边界时动作不支持。tie canonical动作字典序。所有四模型及depth表在任何VALID/EVAL采样前冻结，不按预测误差选择表示、深度或检查点。

VALID每root/合法action两条预定新后缀，至多1024完整分支，不参与拟合。只诊断实际执行动作的一步后继Brier、即时分量MSE与H2尾值三分量MSE及支持/缺失比例；游戏内均值后按游戏、历史等权，不把每一步当独立游戏。记录相同未拟合VALID棋盘上depth1/3实际transport方向的差异，检验组成机会。depth3采用不同后续控制，不能用首动作后固定H2的终局标签声称验证depth3预测。诊断不触发调参、额外采样或科学结果筛选。

EVAL直接从ordinary两随机tile初态执行四历史×32新配对seed×五arm=640完整游戏：H2、SAME_D1、SAME_D3、XFER_D1、XFER_D3。SAME使用自己的单模型；XFER分别递推其他三teacher条件模型，然后选择最高完整效用的model/action组合，tie来源life后action字典序，不平均或拼接tail。每步重新观测并查询冻结表；选中primitive须真实合法，无候选时当步退回自己H2。下一步继续模型决策。模型中的teacher边界是规划边界，实际策略为明确的receding-horizon重新规划，不能声称闭环价值等于估计的固定continuation价值。

主对比SAME_D3−SAME_D1，推进还要求SAME_D3−H2效用CI95下界>0，两条件均通过才提名后续确认，不能自动晋升。次对比XFER_D3−XFER_D1、XFER_D3−H2、XFER_D3−SAME_D3，以及全分量、逐历史、支持/直接执行/H2比例。每历史32个整局配对差后四历史等权，正态条件CI95；条件于这四既有teacher、训练数据、固定表示和模型，不推断新历史总体。XFER库有三倍来源历史，不能把其与SAME差异唯一归因为迁移或样本效率。

BASE=17100000000。TRAIN seed=BASE+10,000,000+life×1,000,000+replica×100,000+slot×1,000+suffix0–3；VALID用+20,000,000及suffix0–1；EVAL=BASE+50,000,000+life×1,000,000+episode0–31。首动作、arm和模型不进入seed；阶段流分离，配对共享uniform采样流，不等同棋盘轨迹。

固定上限为TRAIN/VALID合计3072分支+EVAL640=3712个新物理游戏，最多30,408,704新转移；实际branch数由采样前冻结的来源合法动作roster决定。8192步继承环境质量守恒终态上界。任何required TRAIN/VALID缺失、重复、cutoff/null或身份/向量不一致都保留已付成本、停止全部后续；无replacement。EVAL不完整阻止受影响统计，不能记成科学负结果。SOURCE旧成本与全部teacher、生成/特征、编译/规划、回退、真实采样和测试成本保留；零新增神经权重更新，经验kernel/tail拟合属于学习，不能说训练免费。

独立重建root/合法动作roster、全来源/新分支RNG和H2选择、所有kernel/tail/编译表、VALID诊断及完整EVAL决策与CI。采样前留存新源码、协议与引用源码原始字节，采样后比较一次，不新增hash。无新服务器下载，所有中途文件放项目worktree reports/v171_runtime_tmp/与该轮结果目录。

