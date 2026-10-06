# V175：冻结棋盘与政策的新后缀复测

承接V174科学FAIL。该轮完整树在原TRAIN标签上的四history效用均为正，但新VALID中折叠为ONE显著更好。本轮只检验这一收益能否在独立后缀复现，不拟合、剪枝、换表示或改变已冻结Gate；不晋升策略，不启动U006，当前H2仍V135。

固定政策为每history已审计的V174 PART_UTILITY_UNPRUNED完整树（TREE）及ONE_LATE（ONE）。TRAIN固定原DISCOVERY384棋盘、每history12SOURCE×8根；FRESH固定原V174 VALID256棋盘、每history8SOURCE×8根。SOURCE根来自原整局，教师及后续H2控制不变。TRAIN混合V171的0..7/8分位根128条与V172的1..8/9中段分位根256条；FRESH为1..8/9中段根。保留这一实际取根差异与具体source_step，不把两组当严格相同状态分布。

TREE/ONE依冻结模型、完整合法行动支持和具体首步reward选择；不伪造旧根缺失的teacher_action。当前合法行动均需至少4fit根并在同一配对连通分量；1e-12按DOWN/LEFT/RIGHT/UP并列。任一根不支持则整批HOLD，不删根。全部640根及两政策选择在新采样前冻结；SOURCE数量和根分母保持。

每根16全新配对suffix。两政策选同一动作时新/旧差都精确0，无需新分支，仍以零差保留该根及SOURCE统计权重；不同动作时只采这两个首行动，各用相同suffix seed，之后原history H2续到终态。留存完整reward/failure/success，不采其它行动。旧4suffix仅是冻结reference：TRAIN从已审计模型training_outcomes，FRESH从V174 VALID compact outcomes；不读取或重放旧raw tapes，不将旧/新标签混池。

根ordinal在cohort×history的全部root_id排序中赋0..95(TRAIN)/0..63(FRESH)，先赋再跳过同动作根。BASE=17500000000；TRAIN_REPL为BASE+10M、FRESH_REPL为BASE+20M，再加life×1M+ordinal×1K+suffix0..15；行动/方法不进seed，旧后缀不复用。max_steps8192、p_four=.1、四worker，不新采SOURCE整局。理论上限20,480分支/167,772,160转移；实际roster在采样前精确冻结，不按观察到的收益调整suffix、根或预算。

统计均值为16suffix→root→该SOURCE全部8根等权→每history SOURCE等权→四既有history等权。分别报告TRAIN/FRESH的NEW TREE−ONE、OLD reference及同SOURCE NEW−OLD配对差，完整三分量与utility=reward−failure+success。

分别保留两种不确定性，95%区间均为mean±1.96×SE：SOURCE簇区间用每history来源游戏均值的样本方差/nSOURCE，刻画跨游戏异质性；固定棋盘后缀区间用每changed根16个配对差的样本方差/16，按root在SOURCE、SOURCE在history及history四等权的平方权重传播，sameaction根的方差为0。utility先对每配对三向量求R−F+S再估方差，完整分量的协方差不能忽略。OLD观测reference在本轮条件固定，后缀方差记0仅指该观测数，不能称旧真实均值无误；NEW−OLD后缀方差取NEW方差，SOURCE配对差的簇方差单独计算。跨cohort FRESH−TRAIN对应方差为两组之和；新root/suffix seed不重叠，两组SOURCE也不相同。不将root/suffix/action当独立SOURCE。

冻结诊断问题：TRAIN_NEW是否保留正效用；TRAIN_NEW−OLD是否显著下降；FRESH_NEW效用的方向；FRESH_NEW−TRAIN_NEW是否显著下降。固定棋盘复测以新后缀区间回答该有限棋盘集的采样问题，同时用SOURCE区间限定跨游戏稳定性；两个区间并列报告，不能据结果挑选一种。OLD/cross secondary保留，不新增事后Gate或互斥机制标签。区间含0是未判定，不是等效；标签敏感与状态分布效应可同时存在，这不能唯一识别因果。只有工程complete/HOLD状态，没有策略PASS。

required分支缺失/重复/cutoff/null、绑定或完整向量错误均计费并HOLD，不补样；同动作根无分支是正确零差，不是missing。计入冻结模型读取/根reference装配/选择/统计、全部新物理转移/RNG与教师setup/load/选择工作；新增模型fit与神经update为0。继承V174及所有已付旧成本。独立审计从已审计compact及模型重建根/选择/roster/统计，重放本轮两物理阶段，不重做已settled旧审计。

源码、协议、tests与wrappers原字节在新采样前留存，结束只比较一次，不新增hash。中途仅reports/v175_runtime_tmp/和reports/controlled_predictive_fixed_board_replication_v175/，无服务器下载。负结果或未判定均保留；最终报告据冻结区间解释主瓶颈与下一条路线。
