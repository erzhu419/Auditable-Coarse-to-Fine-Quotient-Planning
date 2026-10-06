# V190：共享合并／阻塞关系的完整后果学习

V189证明 first_reward+g(六计数) 不能表示全部正确排序。本轮用固定关系编码补充牌块等级、排列、阻塞及跨行列压紧关系；仅SOURCE训练，另用未打开TARGET检验。已暴露V188 TARGET96只用于开发区分诊断，不选模型/强度、不能当验证收益。

每action从既有layout_features的16个cell token重建面向DOWN的afterstate；不新swipe。原六aggregate不变。只正rank牌块构成nodes，全部同rank无序pair构成关系，不分绝对位置或exact rank组合词典。两个固定rank基为rank/11与2^(rank−11)，参数在位置和等级间共享。

node 9矩按顺序为1、四方向到边界之间的zero数/3、四方向直接邻居是zero的指示；方向L,R,U,D，越界邻居指示0。node投影Σψ·moment/4。四个pure packing坐标由同行/列之前/之后zero数计算，packing仅移动原node ID，不merge/spawn。

equal pair 33矩：同row/col指示2；原同row/col中间非零blocker数/2共2；其rank和/22共2；abs(Δrow)/3、abs(Δcol)/3、Δrow·Δcol/9共3；四packing方向移动坐标差绝对值/3共4；四方向压紧后在正交轴成同线且无非零blocker指示4；该正交线blocker rank和/22共4；四方向该blocker序列first/last rank/11共8（按top→bottom或left→right，未对齐/无blocker置0）；四方向沿movement axis从move端扫描正牌块、相等邻对只消费一次的原pair指示4。pair投影Σψ·moment/√120。此配对是无spawn机制签名；实际后续行动先有随机spawn，因此不称为完整后续转移。

末8列是每zero cell四方向邻居为rank1/2的发生数/4，方向优先、rank1再2。总6+2×(9+33)+8=98列，顺序原6→rank基1 node/pair→rank基2 node/pair→vacancy8。无截距、学习词表、未知token回退或数据尺度。

开发诊断在固定全部旧96根的实际98向量上重新分组，逐坐标绝对差≤EPS1e−12视同，按首reward/ACTIONS/EPS选代表，计算旧20信息损失根的新rootwise上界；不使用contract原棋盘有信息来替代模型输入有信息。旧五边证书按每个vertex在该证书边中实际action的98向量比较，记录其同值假设是否仍成立。不能因其他非证书出现位置分离而声称该证据被打破；也不把该证据失效当作新函数容量或可学习性已成立。不新解容量LP，不据诊断更改本轮表示。

固定SOURCE143/36组，全部合法action pairs，tail R扣一次首reward、F/S不变，每根每对权重1/对数，SSE/N+λ||W||²、N含forced roots。复用V183 SVD/filter和V188完整模型元数据，仅新RELATION一臂。36来源组排序奇偶两折各18组，λ固定0、0.0001、0.001、0.01、0.1、1，按实际完整留出R−F+S的等组均值选强度，EPS平局先网格；3 SVD、13预测器。SOURCE98编码一次，其余fold/full/heldout读缓存。首reward推理加一次；支持4、连通性、ACTIONS DOWN LEFT RIGHT UP与EPS、回退沿旧规则。

模型与强度冻结后生成TARGET96（四副本×24），seed=1900200+24*replica+index，name=v190_target_r{replica:02d}_{index:02d}，horizon3。沿V69：16次randint1..10，24边先水平后垂直，index边端rank1+index%10，其余格sample(index%3)置零。冻结RELATION、V188 LINEAR/INTERACT、V185 RIDGE/LAYOUT/SHARED、原OLD_SHARED/ONE及FALLBACK全部选择后才取标签。

标签复用V184 V69 FULL、goal1/risk1教师与精确完整R/F/S，每board具体状态上限200000，新增96核/规划，留紧凑policy和native/canonical标签/成本，不留大kernel。主要比较RELATION−LINEAR/RIDGE/OLD_SHARED，其余controls、ORACLE、每根/副本R/F/S、遗憾、错误增减与集中度均保存。不设新科学Gate，不按目标结果重新训练。

读取真实输入前冻结源码/协议/tests/wrappers，十输入按序V189stage/run/diagnostics/summary、V188roots/labels、继承expanded_models/baseline_models/learned_rule、V188models；全在protocol_frozen复制原字节。阶段protocol_frozen(0reads)→development_diagnostics(10)→source_selection→models_frozen→target_roots→target_choices_frozen→target_labels→complete，其余均10reads。main/audit各一次，threads1；十输入独立分析比较一次，源码stage比较一次，不加hash。

独立审计重建98/cache/开发统计/SOURCE folds/design/support，13系数独立solve（λ0lstsq、正λ列正规方程），沿已有1e−10系数容差先认证实际数组后独立重算真实EPS选择。旧模型和物理后端不重fit/积分；新标签仅复用已审计native/canonical binding与成本校对。所有新学习、编码、无spawn本地配对、选择、精确标签及旧成本链保留；失败保留实付学习或核尝试并HOLD。

中途仅reports/v190_runtime_tmp（含pytest临时目录），结果仅reports/controlled_predictive_merge_relations_v190。零新物理随机样本、SOURCE游戏及native更新。限制：有限H3、固定后续教师、根动作评估；开发区分不是迁移收益，关系矩仍是压缩表示。保持H2、U005 FAIL、U006未启动。
