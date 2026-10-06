# V176：真实首个 spawn 支持分层的同分支预算对照

承接V175：固定训练棋盘的新后缀未复现原正收益，NEW−OLD效用−0.18334的两种冻结区间均低于0。V176先干预后果证据获取，不能将采样精度当作战略学习成功。保持V135 H2、冻结TREE/ONE及其后续教师；新增SOURCE整局、模型拟合与权重更新均为0，U005 FAIL与U006未启动保持。

复用已审计V175的640根与冻结选择，不重做旧raw或模型审计。在每cohort TRAIN/FRESH×四history中，对选择不同的根按首个joint-spawn支持数量、root_id排序，取index=len//2的根；只用棋盘与动作生成几何、不读旧收益决定选择。固定8根，各有单个SOURCE来源，不能推广为整个640根集。真实棋盘强制TREE/ONE首动作，之后各自原H2续到终态。

first-spawn采用两动作共同cell uniform与共同rank：合并i/nTREE和j/nONE的有理端点，其相邻区间映射各native空格cell；每区间分别rank1(.9)与rank2(.1)，形成S个正概率分层。分层概率为区间长度×rank概率。每根每block N=4S配对suffix。每层先2条，再把剩余2S条依次分配给p²/[n(n+1)]最大者（最低stratum打破并列），只用已知概率；这是等条件方差假设下的整数分配，不拟合新结果的方差。IID同根每block也采N对；两方法物理分支数严格相同，不声称转移数或总CPU预算精确匹配。

冻结8独立block。STRAT逐层固定其首个cell/rank、保留完整终局reward/failure/success，以sum(p_s×层内配对均值)估计TREE−ONE；IID为N配对均值。两方法的目标期望相同，政策选择不变。tail RNG与first-spawn RNG分离：BASE17600000000；tail为BASE+10M，first为BASE+20M，再加probe_ordinal×100000+block×1000+draw。动作和方法均不进seed；STRAT不消耗first RNG，IID首步2次draw；两方法后续从同tail RNG状态开始，pair内也共用。其余spawn与V175环境相同。

几何预检已固定8根，S为[12,18,12,16,12,14,12,14]，总物理分支14,080，每方法7,040；max_steps8192、p_four.1、四worker，最大转移115,343,360。actual转移、RNG、H2决策和模型setup/load全计费，不因观察到的返回调整根、样本或分配。

每block先八根完整向量等权，四history及两cohort因根数相等而等权，再在8block上计算样本方差。primary为utility完整向量点积R−F+S的block方差差STRAT−IID，按paired delete-one-block jackknife估SE，冻结normal95区间为差值±1.96SE，上界<0仅支持该8棋盘条件下采样方差降低。方差ratio、每根/每history四metrics、均值及方差×平均block转移数为描述性secondary。区间含0为未判定；8block近似不能当广义效率保证或战略PASS。不能独立相加R/F/S方差忽略协方差。

所有计划与源码/协议/tests/wrappers在物理采样前留存；结束原字节比对一次，无hash。任一required分支missing/duplicate/cutoff/null/绑定或完整vector不符，整批HOLD，不补样。独立审计另行构造支持、整数分配、选根、roster与加权/paired统计，逐条重放本轮完整轨迹并核对成本及教师不变；不重放旧tapes。

预检一次import因Python3.10的starred-subscript语法失败、已修；在任何JSON读取与采样前发生。成功几何预检6次JSON读取/590次ground swipe/295次支持构造，无物理样本/RNG；它在preflight_checks.json计费一次，preflight.json是同一操作的几何摘要，不重复相加。正式冻结及独立审计的读取/构造另计。全部中间产物限项目reports/v176_runtime_tmp/与reports/controlled_predictive_spawn_stratification_v176/，不从服务器下载。

若未建立采样收益，不继续追加block至显著；转向表示/归纳的无MonteCarlo噪声阳性控制。若采样收益成立，则下一阶段固定相同学习算法，分别用两种获取方法训练并在独立新棋盘、新后缀上评估真实效用；本轮不修改策略或晋升H2。
