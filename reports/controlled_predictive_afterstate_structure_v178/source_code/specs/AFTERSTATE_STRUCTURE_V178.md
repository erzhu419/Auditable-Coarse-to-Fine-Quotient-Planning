# V178：动作后的结构表示，固定精确 H3 标签

V177 在无 Monte Carlo 标签噪声、目标有 oracle headroom、双方零回退时仍出现 SOURCE 正收益/TARGET 负收益。本轮只替换候选表示，检验可迁移的动作区分。保持 V177 的47个来源H3根、24个目标H3根、12设计组/两折、唯一后续教师和完整精确 R/F/S 标签。原 ordinal15 的 H2排除保留，H4不混入；既有 H2、U005 FAIL、U006未启动不变。

表示仅用 canonical 当前棋盘进行四个确定性合法 swipe，不采 spawn、不读取未来标签。ACTIONS 固定 DOWN/LEFT/RIGHT/UP。每动作66个布尔特征，合计264：合法动作；afterstate是否已达到goal rank11；16格 vacancy；row0..3然后column0..3分别移除零保持顺序，每压缩线三个邻接位置各记录“两个正rank相等”和“两个rank均为10，可形成goal”的两位。缺失邻接槽为0；非法动作全部66位为0。相邻比较允许重叠，仅表示几何邻接。每动作顺序为legal、goal_reached、vacancy0..15、各line/pair先equal后goal_pair。所有SOURCE/TARGET特征缓存一次；实际swipe、扫描、邻接、缓存读取与路线工作分别计费。

每候选按feature index0..263顺序，只比较布尔值<=0，等价于false/true划分。不保留原始rank门槛、不依据新结果删加特征。具体首reward仍作为参数，叶估计继续使用去首reward后的配对续局向量，每根动作对总权重1。V174两折来源等权实际效用目标、同源整组分折、MIN_CHILD_ROOTS8、MIN_CHILD_SOURCES2、MIN_ACTION_ROOTS4、MAX_LEAVES16、EPS1e-12、贪心节点和并列次序保持；结构决定后全来源重新拟合各节点。单合法动作部署强制选择，其他不足支持根用共同最大首reward回退；不使用目标oracle。

只新增STRUCTURE树拟合，V177的RAW树/ONE与其全部选择原样复用。目标特征来自已观测棋盘；新STRUCTURE动作选择在读取V177完整目标标签文件前冻结。标签是已暴露留存诊断，读取顺序不使其成为新鲜确认。旧kernel、旧fit和旧tapes不重算；继承来源/验证成本引用V177账本。

每模型依V177原摘要报告同一固定后续教师下的oracle−ONE headroom、TREE−ONE及剩余regret。主诊断为TARGET STRUCTURE−ONE和STRUCTURE−RAW的完整R/F/S/utility变化；SOURCE设计组等权、TARGET根等权，保留root/group均值、改善/恶化/等值根、新增/修复正regret及fallback。无随机CI或新的Gate；每个差额允许为负，不能追加数据或调特征直至变正。

协议、实现、测试、wrappers在正式fit前原字节留存，独立审计重新生成全部264位、boolean候选/节点拟合、缓存成本与新选择/统计；原基线及标签逐一对照继承文件。结束输入字节比对由审计执行一次，源码字节比对由stage执行一次，无hash。identity、输入/向量/计数不一致保留付费记录为执行HOLD；科学负结果保持。中途产物仅reports/v178_runtime_tmp/与reports/controlled_predictive_afterstate_structure_v178/，无服务器下载、物理样本、SOURCE整局或原生权重更新。

结果只检验一个动作结构特征家族及同一叶估计器，无法把效果拆归给单个特征或证明一般战略学习；精确H3窗口、固定后续教师、非独立设计组与旧目标暴露的限制延续V177。若改进，仅说明这一诊断的表示收益；后续仍须独立任务与长程检验。
