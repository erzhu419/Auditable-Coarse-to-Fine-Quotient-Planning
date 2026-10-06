# V173：独立来源确认的状态分割（冻结协议）

承接V172科学FAIL。本轮改变分割的学习/接纳机制：DISCOVERY提出固定分割，独立CONFIRM只保留或折叠，最终独立VALID检验。教师、原U005 Gate与U006未启动状态不变。无整局自主控制、迁移或采样效率主张。

DISCOVERY仅继承已留存V171 TRAIN128根/1880完整强制首行动后果与V172新增TRAIN256根/3700后果，共384根、96/历史。旧VALID/EVAL标签、选择与H2自选续局转移不入训练。接受V172原编码审计失败及补充observable equivalence通过这一实际状态；用已修复零和求解器重建新模型，原产物不改。旧全部已付成本继续引用，不重放已审计旧tapes。

提议树完全沿用V172的全三分量配对损失/同history Laplacian估计、canonical16cell rank≤0..9、全局贪心、最多16leaf、每child至少8根与2SOURCE、动作至少4根且连通、1e-12并列规则。首步精确确定性reward仍为数值参数。每internal node的collapsed父leaf及两个直接child leaf系数仅从DISCOVERY重建，全部在CONFIRM前冻结；最终leaf复用。ONE_LATE和COARSE_LATE控制用相同DISCOVERY一次冻结。

CONFIRM_SOURCE为每history8个新ordinary初态H2整局，共32局，每局预定8个中段分位根，step=(slot+1)×n//9。按与DISCOVERY具体canonical棋盘精确相等排除已见根，记录已付SOURCE成本，不补根。每预定SOURCE须至少1个未见根，否则HOLD。先保存每根完整提议路径上每internal node的固定父政策/直接child政策行动与支持、完整预测向量/工作，再取得全部合法首行动×4配对suffix终局reward/failure/success；之后同本history H2续局。至多4096CONFIRM分支；合法性/支持/回退政策完全沿用DISCOVERY，不能用CONFIRM改变。

固定节点确认：该proposal节点区域内每根、每suffix的child政策实际终局向量减parent政策；区域外根差向量为0。4suffix均值→每SOURCE全部留存根等权均值→该history全部8SOURCE簇均值、sample variance与SE。保留完整三分量及utility=reward−failure+success。K在新确认采样前冻结为四history全部proposal internal节点数（含以后不可达节点）；z=NormalDist().inv_cdf(1−.05/(2K))，每node区间mean±z×SE。K=0没有分割确认。区间下界>0、每child至少2不同CONFIRM SOURCE、且parent/child均模型支持并改变行动的根来自至少2SOURCE，才local_pass。所有根（含fallback）参与真实policy差，不按支持/行动变化删统计根。8簇正态界是冻结选择规则，不能称形式整树95%证书。

全部固定候选统计均留存，再从root按固定left/right次序topdown应用。节点local_pass且祖先均保留才retained；父拒绝则该处collapsed leaf成为最终规则、后代不启用。CONFIRM不能生成新分割、重拟合系数、追加样本、改变阈值/容量或选择停止条件。冻结PART_CONFIRMED、PART_UNPRUNED、ONE_LATE、COARSE_LATE的4×4模型和各history剪枝记录后，才开展VALID_SOURCE。

VALID_SOURCE同样32个全新H2整局/256候选分位根；仅按DISCOVERY及CONFIRM留存根的canonical具体棋盘精确相等排除已见，不補根，每SOURCE至少1根。全部4模型与H2选择在VALID标签前冻结；VALID全部合法行动×4全新配对suffix到终态，至多4096分支。主对比PART_CONFIRMED−PART_UNPRUNED，推进另需PART_CONFIRMED−H2，两个SOURCE簇条件95%区间下界都>0，且至少一个实际retained split，才PASS。结构全折叠不能称表示学习成功。次对比PART_CONFIRMED−ONE_LATE/COARSE_LATE、PART_UNPRUNED−H2。完整动作对MSE、支持/回退/选择差异作诊断，不作新增事后Gate。

VALID同V172：4suffix→root→SOURCE游戏→每history八SOURCE均值和簇级均值方差→四既有history等权，正态95%CI。只估计各固定首政策之后H2续局效用；不把root/suffix/action当独立游戏。确认数据是学习数据，确认区间不作最终性能结论；VALID绝不反馈学习。

BASE=17300000000。CONFIRM_SOURCE=BASE+10M+life×1M+replica0..7；CONFIRM=BASE+20M+life×1M+replica×100K+slot×1K+suffix0..3。VALID_SOURCE用+30M，VALID用+40M。行动/方法不进seed。max_steps=8192，p_four=.1，新采样上限64SOURCE+8192分支=8256物理游戏/67,633,152转移。所有根、合法分支roster、节点choice、模型按阶段采样前冻结。required SOURCE/branch缺失/重复/cutoff/null/向量或身份不一致均成本留存并HOLD，不补样；节点覆盖不足或效用未确认为local拒绝，不是执行HOLD。

每物理阶段记录教师setup/load/决策、swipe/转移/RNG/特征/回退与真实终态；新增proposal/node重建、确认计算与剪枝工作单计，无新神经权重更新。独立审计重建仅compact的DISCOVERY，重建提议/节点政策/确认统计/剪枝/VALID选择及簇统计，重放本轮四新物理阶段；不重新重放旧V171/V172。源码、协议、测试、wrapper原字节在新采样前留存，结束只比较一次，不新增hash。

中间文件仅在本项目worktree reports/v173_runtime_tmp/与reports/controlled_predictive_confirmed_partition_v173/。无服务器下载。失败/零保留节点如实留存，不调Gate、suffix数量或候选来挽救本轮。

