# V185：扩充独立来源后果覆盖

V184 的四个新目标副本均不支持正则化相对 SHARED/LAYOUT 的收益。本轮固定 V182 rank/layout 表示、V183 六个 λ、两折来源组平均实际行动效用选择，以及完整 R/F/S、R−F+S、首 reward、支持/回退和教师；仅扩充来源数据后用另一个未见目标队列比较。新词表仍只由每折/全训练 SOURCE 生成，token 定义和尺度不变。覆盖不足是待检验解释。

原 SOURCE47 根及12组取自冻结 V183 RIDGE.training_outcomes，旧源标签/缓存保持。新增 SOURCE96 和独立 TARGET96，各四副本×24，均沿用 V69 近满棋盘生成方式：Random(seed) 产生16个 randint(1,10)，24条边先12水平后12垂直，取 index%24，两端为1+index%10，其余格 sample(index%3) 置零。SOURCE seed=1850100+24*replica+index，TARGET=1850200+24*replica+index；名字 v185_source_r{replica:02d}_{index:02d} / v185_target_r{replica:02d}_{index:02d}。不读取V184目标标签，也不替换或追加棋盘。

新增来源组为 DESIGN_SOURCE:{12+6*replica+index//4:02d}，每组4根；SOURCE 总143根/36个设计组。原来源组和两折奇偶位置保持；36组排序后按偶/奇构建同一两折规则，拟合18组、留出18组，选 λ 时每组等权。这些是设计分组，不是完整 episode。真实来源棋盘在协议冻结后生成；新目标棋盘在训练/参数冻结后才生成。

复用 V184 精确 FULL 构建、原 float fsum/strict> 教师 plan(goal1/risk1)、精确分数后果和200000具体状态/棋盘上限。96个新增来源标签先获取；其后训练完整36组和冻结所有模型/λ。目标七个学习器分别为扩充 RIDGE/LAYOUT/SHARED、原 OLD_RIDGE/OLD_LAYOUT/OLD_SHARED，以及原 ONE；全部目标动作冻结后才生成目标完整标签。完整标签、教师决策、每根构建与规划成本均留存，不保存庞大完整核。

RIDGE 保持每根平均 weighted 完整三分量行动对 SSE+λ||W||²、SOURCE-only 词表/支持；每折一次 SVD 产生六个滤波系数，最后全来源一次 SVD 产生选定系数。该最后分解额外产生 λ=0 的 LAYOUT；SHARED 用同一全来源 weighted X 的六 aggregate 列和完整 Y 做最小范数 lstsq。合计3次 SVD、14次系数滤波、1次六列 lstsq，共15个预测器；无改变 loss、增加参数网格或按目标选模型。

五项输入按字节冻结：V184 stage/run、其留存 V183 RIDGE models、三个旧 baseline models 和 learned_rule。旧47来源标签从模型内保留数据提取，无旧目标标签读取。主要报告新目标上三种同方法新−旧完整效用差、扩充 RIDGE−扩充 SHARED、相对 ONE 及每副本均值；另保留 R/F/S、regret、正负根、最大正收益比例和新旧词表覆盖。复用 V184 已审计统计，仅增加同方法扩充效应；无新增科学Gate、随机CI、后验筛选。

独立分析验证新增36组训练/选 λ、SOURCE词表/支持、14个系数解和六列SHARED解、冻结选择及新增配对统计。既有 V184 精确标签后端和物理分数整合已审计，本轮复用，不重复192个物理核评估；新标签核对留存native分数、规范动作映射、根教师绑定和成本。协议/源码/测试/wrappers 在真实输入读取前快照。main/audit各一次，线程1，失败保留成本和已完成根；输入和源码各比较一次，无hash。所有中途文件仅reports/v185_runtime_tmp，结果仅reports/controlled_predictive_source_coverage_v185。

下一步由覆盖效应决定：如果增加来源能稳定改善同方法并缩小 richer表示与SHARED差距，转入更长时域学习；如果仍不能，检查表示的跨动作共享与拟合目标，停止围绕目标搜强度。限制：143个来源根包含合成近满棋盘，来源构成也改变；不将收益归因于样本数单一因素，不证明完整episode、一般战略或采样效率。保留H2、U005 FAIL、U006未启动。
